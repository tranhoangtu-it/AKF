"""AKF v1.1 — Shared OOXML (ZIP-based) helpers for DOCX/XLSX/PPTX.

All Office Open XML formats are ZIP archives. AKF metadata is stored
entirely within docProps/custom.xml as Office Custom Document Properties.
This is the standard OOXML mechanism for custom metadata, so Word, Excel,
and PowerPoint handle it natively — no "unreadable content" warnings.

Storage layout inside the ZIP:
  docProps/custom.xml — AKF summary fields as named properties
                        + full JSON in AKF.Metadata property

Key properties visible in File > Properties > Custom:
  AKF.Enabled, AKF.Classification, AKF.Claims, AKF.AvgTrust,
  AKF.AIClaims, AKF.HumanClaims, AKF.Agent, AKF.LastActor
Full metadata round-trips via AKF.Metadata (JSON string).
"""

import json
import os
import re
import shutil
import tempfile
import zipfile
from typing import Optional

# Legacy paths for backwards-compatible reading
_LEGACY_JSON_PATH = "customXml/akf-metadata.json"
_LEGACY_XML_PATH = "customXml/akf-item.xml"
_LEGACY_AKF_JSON_PATH = "akf/metadata.json"
_LEGACY_AKF_XML_PATH = "akf/metadata.xml"

CUSTOM_PROPS_PATH = "docProps/custom.xml"

CUSTOM_PROPS_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.custom-properties+xml"
)
CUSTOM_PROPS_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
)

# Property name for the full AKF JSON payload
_AKF_METADATA_PROP = "AKF.Metadata"


def embed_in_ooxml(filepath: str, metadata: dict) -> None:
    """Embed AKF metadata into an OOXML ZIP archive via custom properties.

    Stores key AKF fields as individual Custom Document Properties
    (visible in File > Properties > Custom) and the full JSON in
    AKF.Metadata for round-trip fidelity. No non-standard ZIP entries
    are created, so Office never shows "unreadable content" warnings.

    Args:
        filepath: Path to the OOXML file (.docx, .xlsx, .pptx).
        metadata: AKF metadata dict to embed.

    Raises:
        zipfile.BadZipFile: If the file is not a valid ZIP archive.
        OSError: If the file cannot be read or written.
    """
    custom_props_xml = _build_custom_properties(metadata)

    # Create temp file in same directory for safe atomic replace
    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=os.path.splitext(filepath)[1],
        dir=os.path.dirname(os.path.abspath(filepath)),
    )
    os.close(tmp_fd)

    try:
        with zipfile.ZipFile(filepath, "r") as zin:
            existing_names = zin.namelist()
            had_custom_props = CUSTOM_PROPS_PATH in existing_names

            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    # Skip entries we'll rewrite or clean up
                    if item.filename in (
                        _LEGACY_JSON_PATH,
                        _LEGACY_XML_PATH,
                        _LEGACY_AKF_JSON_PATH,
                        _LEGACY_AKF_XML_PATH,
                        CUSTOM_PROPS_PATH,
                    ):
                        continue

                    raw = zin.read(item.filename)

                    # Patch [Content_Types].xml to include custom props
                    if (
                        item.filename == "[Content_Types].xml"
                        and not had_custom_props
                    ):
                        raw = _inject_content_type(raw)

                    # Patch _rels/.rels to include custom props relationship
                    if item.filename == "_rels/.rels" and not had_custom_props:
                        raw = _inject_rels(raw)

                    zout.writestr(item, raw)

                # Write custom document properties (only standard OOXML part)
                zout.writestr(CUSTOM_PROPS_PATH, custom_props_xml.encode("utf-8"))

        # Atomic replace
        shutil.move(tmp_path, filepath)
    except Exception:
        # Clean up temp file on any failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def extract_from_ooxml(filepath: str) -> Optional[dict]:
    """Extract AKF metadata from an OOXML ZIP archive.

    Checks (in order):
      1. AKF.Metadata property in docProps/custom.xml (current format)
      2. akf/metadata.json (v1.1 legacy)
      3. customXml/akf-metadata.json (v1.0 legacy)

    Args:
        filepath: Path to the OOXML file.

    Returns:
        Parsed metadata dict, or None if no AKF metadata found.
    """
    try:
        with zipfile.ZipFile(filepath, "r") as z:
            names = z.namelist()

            # Try custom properties first (current format)
            if CUSTOM_PROPS_PATH in names:
                meta = _extract_from_custom_props(z.read(CUSTOM_PROPS_PATH))
                if meta is not None:
                    return meta

            # Fall back to legacy paths
            for path in (_LEGACY_AKF_JSON_PATH, _LEGACY_JSON_PATH):
                if path in names:
                    data = z.read(path)
                    return json.loads(data)
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError):
        pass
    return None


def is_ooxml_enriched(filepath: str) -> bool:
    """Check if an OOXML file contains AKF metadata.

    Args:
        filepath: Path to the OOXML file.

    Returns:
        True if the file contains AKF metadata.
    """
    try:
        with zipfile.ZipFile(filepath, "r") as z:
            names = z.namelist()
            # Check custom properties for AKF.Enabled
            if CUSTOM_PROPS_PATH in names:
                content = z.read(CUSTOM_PROPS_PATH).decode("utf-8", errors="replace")
                if "AKF.Enabled" in content:
                    return True
            # Legacy paths
            return (
                _LEGACY_AKF_JSON_PATH in names or _LEGACY_JSON_PATH in names
            )
    except (zipfile.BadZipFile, OSError):
        return False


def list_ooxml_entries(filepath: str) -> Optional[list]:
    """List all entries in an OOXML ZIP archive.

    Useful for debugging and testing.

    Args:
        filepath: Path to the OOXML file.

    Returns:
        List of entry names, or None if not a valid ZIP.
    """
    try:
        with zipfile.ZipFile(filepath, "r") as z:
            return z.namelist()
    except zipfile.BadZipFile:
        return None


# ── Internal helpers ──────────────────────────────────────────────


def _xml_escape(s: str) -> str:
    """Escape a string for safe inclusion in XML text content."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_custom_properties(metadata: dict) -> str:
    """Build docProps/custom.xml with AKF fields.

    Stores both human-readable summary properties and the full AKF JSON
    in AKF.Metadata for lossless round-trip extraction.
    """
    VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
    NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"

    props: list[tuple[str, str, str]] = []  # (name, vt_type, value)

    # Always add the AKF marker
    props.append(("AKF.Enabled", "bool", "true"))

    # Classification
    label = metadata.get("classification") or metadata.get("label")
    if label:
        props.append(("AKF.Classification", "lpwstr", str(label)))

    # Claims summary
    claims = metadata.get("claims", [])
    if claims:
        props.append(("AKF.Claims", "i4", str(len(claims))))
        trust_scores = [c.get("t", 0) for c in claims if isinstance(c, dict)]
        if trust_scores:
            avg = sum(trust_scores) / len(trust_scores)
            props.append(("AKF.AvgTrust", "lpwstr", f"{avg:.2f}"))
        ai_count = sum(1 for c in claims if isinstance(c, dict) and c.get("ai"))
        if ai_count:
            props.append(("AKF.AIClaims", "i4", str(ai_count)))
        human_count = len(claims) - ai_count
        if human_count:
            props.append(("AKF.HumanClaims", "i4", str(human_count)))

    # Provenance — last actor
    prov = metadata.get("provenance") or metadata.get("prov", [])
    if prov and isinstance(prov, list):
        last = prov[-1] if prov else None
        if last and isinstance(last, dict):
            actor = last.get("actor") or last.get("by", "")
            if actor:
                props.append(("AKF.LastActor", "lpwstr", str(actor)))
            ts = last.get("at", "")
            if ts:
                props.append(("AKF.LastModified", "lpwstr", str(ts)))

    # Agent
    agent = metadata.get("agent")
    if agent:
        props.append(("AKF.Agent", "lpwstr", str(agent)))

    # Full JSON payload for round-trip fidelity
    json_str = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
    props.append((_AKF_METADATA_PROP, "lpwstr", json_str))

    # Build XML
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<Properties xmlns="{NS}" xmlns:vt="{VT}">',
    ]
    for i, (name, vt_type, value) in enumerate(props, start=2):
        escaped_val = _xml_escape(value)
        escaped_name = _xml_escape(name)
        lines.append(
            f'  <property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}"'
            f' pid="{i}" name="{escaped_name}">'
        )
        lines.append(f"    <vt:{vt_type}>{escaped_val}</vt:{vt_type}>")
        lines.append("  </property>")
    lines.append("</Properties>")
    return "\n".join(lines)


def _extract_from_custom_props(raw: bytes) -> Optional[dict]:
    """Extract AKF metadata from docProps/custom.xml content.

    Looks for the AKF.Metadata property containing the full JSON payload.
    """
    text = raw.decode("utf-8", errors="replace")
    # Quick check — is AKF present?
    if "AKF.Metadata" not in text:
        return None

    # Extract the value from the AKF.Metadata property
    # Pattern: <property ...name="AKF.Metadata">...<vt:lpwstr>JSON</vt:lpwstr>...
    match = re.search(
        r'name="AKF\.Metadata"[^>]*>.*?<vt:lpwstr>(.*?)</vt:lpwstr>',
        text,
        re.DOTALL,
    )
    if not match:
        return None

    json_str = match.group(1)
    # Unescape XML entities
    json_str = (
        json_str.replace("&quot;", '"')
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
    )
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def _inject_content_type(raw: bytes) -> bytes:
    """Add custom properties content type to [Content_Types].xml."""
    text = raw.decode("utf-8")
    if CUSTOM_PROPS_CONTENT_TYPE in text:
        return raw
    override = (
        f'<Override PartName="/{CUSTOM_PROPS_PATH}"'
        f' ContentType="{CUSTOM_PROPS_CONTENT_TYPE}"/>'
    )
    text = text.replace("</Types>", f"{override}</Types>")
    return text.encode("utf-8")


def _inject_rels(raw: bytes) -> bytes:
    """Add custom properties relationship to _rels/.rels."""
    text = raw.decode("utf-8")
    if CUSTOM_PROPS_REL_TYPE in text:
        return raw
    existing = re.findall(r'Id="rId(\d+)"', text)
    next_id = max((int(n) for n in existing), default=0) + 1
    rel = (
        f'<Relationship Id="rId{next_id}"'
        f' Type="{CUSTOM_PROPS_REL_TYPE}"'
        f' Target="{CUSTOM_PROPS_PATH}"/>'
    )
    text = text.replace("</Relationships>", f"{rel}</Relationships>")
    return text.encode("utf-8")
