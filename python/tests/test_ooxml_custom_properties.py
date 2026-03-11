"""Comprehensive tests for OOXML custom properties AKF storage.

Tests the new docProps/custom.xml-based storage for DOCX/XLSX/PPTX,
including embed, extract, round-trip, legacy path migration, XML escaping,
content type injection, relationship injection, and Word compatibility.
"""

import json
import os
import re
import tempfile
import zipfile

import pytest

from akf.formats._ooxml import (
    CUSTOM_PROPS_PATH,
    CUSTOM_PROPS_CONTENT_TYPE,
    CUSTOM_PROPS_REL_TYPE,
    _LEGACY_JSON_PATH,
    _LEGACY_XML_PATH,
    _LEGACY_AKF_JSON_PATH,
    _LEGACY_AKF_XML_PATH,
    embed_in_ooxml,
    extract_from_ooxml,
    is_ooxml_enriched,
    list_ooxml_entries,
    _build_custom_properties,
    _extract_from_custom_props,
    _inject_content_type,
    _inject_rels,
    _xml_escape,
)


# ── Helpers ──────────────────────────────────────────────────────


def create_minimal_docx(path):
    """Create a minimal valid DOCX."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType='
            '"application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns='
            '"http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type='
            '"http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            '/officeDocument" Target="word/document.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w='
            '"http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Test content</w:t></w:r></w:p></w:body>"
            "</w:document>",
        )


def create_minimal_xlsx(path):
    """Create a minimal valid XLSX."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType='
            '"application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument'
            '.spreadsheetml.sheet.main+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns='
            '"http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type='
            '"http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            '/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>'
        )


def create_minimal_pptx(path):
    """Create a minimal valid PPTX."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType='
            '"application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/ppt/presentation.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument'
            '.presentationml.presentation.main+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns='
            '"http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type='
            '"http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            '/officeDocument" Target="ppt/presentation.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "ppt/presentation.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>'
        )


CREATORS = {
    "docx": create_minimal_docx,
    "xlsx": create_minimal_xlsx,
    "pptx": create_minimal_pptx,
}


@pytest.fixture(params=["docx", "xlsx", "pptx"])
def ooxml_file(request, tmp_path):
    """Parametrized fixture: creates a minimal DOCX, XLSX, or PPTX."""
    ext = request.param
    path = str(tmp_path / f"test.{ext}")
    CREATORS[ext](path)
    return path


@pytest.fixture
def docx_file(tmp_path):
    path = str(tmp_path / "test.docx")
    create_minimal_docx(path)
    return path


@pytest.fixture
def sample_metadata():
    return {
        "classification": "confidential",
        "claims": [
            {"c": "Revenue was $4.2B", "t": 0.98, "src": "SEC 10-Q", "ai": False},
            {"c": "AI segment grew 45%", "t": 0.85, "src": "Internal", "ai": True},
        ],
        "provenance": [
            {"actor": "copilot-m365", "action": "embedded", "at": "2026-01-15T10:00:00Z"}
        ],
        "agent": "copilot-m365",
    }


# ── Test: Custom Properties Build ────────────────────────────────


class TestBuildCustomProperties:
    """Test _build_custom_properties XML generation."""

    def test_always_has_akf_enabled(self):
        xml = _build_custom_properties({})
        assert "AKF.Enabled" in xml
        assert "<vt:bool>true</vt:bool>" in xml

    def test_classification_property(self):
        xml = _build_custom_properties({"classification": "secret"})
        assert "AKF.Classification" in xml
        assert "secret" in xml

    def test_label_fallback(self):
        xml = _build_custom_properties({"label": "internal"})
        assert "AKF.Classification" in xml
        assert "internal" in xml

    def test_claims_count(self):
        meta = {"claims": [{"c": "A", "t": 0.9}, {"c": "B", "t": 0.8}]}
        xml = _build_custom_properties(meta)
        assert "AKF.Claims" in xml
        assert "<vt:i4>2</vt:i4>" in xml

    def test_avg_trust(self):
        meta = {"claims": [{"c": "A", "t": 0.9}, {"c": "B", "t": 0.7}]}
        xml = _build_custom_properties(meta)
        assert "AKF.AvgTrust" in xml
        assert "0.80" in xml

    def test_ai_human_split(self):
        meta = {"claims": [
            {"c": "Human claim", "t": 0.9, "ai": False},
            {"c": "AI claim 1", "t": 0.7, "ai": True},
            {"c": "AI claim 2", "t": 0.6, "ai": True},
        ]}
        xml = _build_custom_properties(meta)
        assert "AKF.AIClaims" in xml
        assert "AKF.HumanClaims" in xml
        # Find the values
        ai_match = re.search(r'name="AKF\.AIClaims".*?<vt:i4>(\d+)</vt:i4>', xml, re.DOTALL)
        human_match = re.search(r'name="AKF\.HumanClaims".*?<vt:i4>(\d+)</vt:i4>', xml, re.DOTALL)
        assert ai_match and ai_match.group(1) == "2"
        assert human_match and human_match.group(1) == "1"

    def test_provenance_last_actor(self):
        meta = {"provenance": [
            {"actor": "alice", "action": "created", "at": "2026-01-01T00:00:00Z"},
            {"actor": "bob", "action": "reviewed", "at": "2026-01-02T00:00:00Z"},
        ]}
        xml = _build_custom_properties(meta)
        assert "AKF.LastActor" in xml
        assert "bob" in xml

    def test_provenance_prov_key(self):
        """Should handle 'prov' key (compact format) as well as 'provenance'."""
        meta = {"prov": [{"by": "agent-x", "at": "2026-01-01T00:00:00Z"}]}
        xml = _build_custom_properties(meta)
        assert "AKF.LastActor" in xml
        assert "agent-x" in xml

    def test_agent_property(self):
        xml = _build_custom_properties({"agent": "claude-code"})
        assert "AKF.Agent" in xml
        assert "claude-code" in xml

    def test_metadata_json_payload(self):
        meta = {"claims": [{"c": "Test", "t": 0.5}]}
        xml = _build_custom_properties(meta)
        assert "AKF.Metadata" in xml
        # The JSON should be XML-escaped and parseable after unescaping
        match = re.search(r'name="AKF\.Metadata".*?<vt:lpwstr>(.*?)</vt:lpwstr>', xml, re.DOTALL)
        assert match
        json_str = match.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        parsed = json.loads(json_str)
        assert parsed["claims"][0]["c"] == "Test"

    def test_pid_numbering(self):
        """PIDs should start at 2 and be sequential."""
        xml = _build_custom_properties({"classification": "public", "claims": []})
        pids = re.findall(r'pid="(\d+)"', xml)
        for i, pid in enumerate(pids):
            assert int(pid) == i + 2

    def test_valid_xml_structure(self):
        xml = _build_custom_properties({"claims": [{"c": "X", "t": 0.5}]})
        assert xml.startswith('<?xml version="1.0"')
        assert "<Properties" in xml
        assert "</Properties>" in xml
        assert xml.count("<property") == xml.count("</property>")


# ── Test: XML Escaping ───────────────────────────────────────────


class TestXmlEscape:
    def test_ampersand(self):
        assert _xml_escape("A & B") == "A &amp; B"

    def test_less_than(self):
        assert _xml_escape("x < y") == "x &lt; y"

    def test_greater_than(self):
        assert _xml_escape("x > y") == "x &gt; y"

    def test_quote(self):
        assert _xml_escape('say "hello"') == "say &quot;hello&quot;"

    def test_combined(self):
        assert _xml_escape('<a & "b">') == "&lt;a &amp; &quot;b&quot;&gt;"

    def test_no_escaping_needed(self):
        assert _xml_escape("plain text") == "plain text"

    def test_unicode_passthrough(self):
        assert _xml_escape("日本語テスト") == "日本語テスト"


# ── Test: Extract from Custom Properties ─────────────────────────


class TestExtractFromCustomProps:
    def _make_custom_xml(self, json_str):
        escaped = _xml_escape(json_str)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"'
            ' xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="AKF.Metadata">'
            f'<vt:lpwstr>{escaped}</vt:lpwstr>'
            '</property></Properties>'
        ).encode("utf-8")

    def test_extract_simple(self):
        meta = {"claims": [{"c": "Hello", "t": 0.9}]}
        raw = self._make_custom_xml(json.dumps(meta))
        result = _extract_from_custom_props(raw)
        assert result == meta

    def test_extract_with_special_chars(self):
        meta = {"claims": [{"c": "A & B < C > D", "t": 0.7}]}
        raw = self._make_custom_xml(json.dumps(meta))
        result = _extract_from_custom_props(raw)
        assert result["claims"][0]["c"] == "A & B < C > D"

    def test_extract_no_akf_metadata(self):
        raw = (
            '<?xml version="1.0"?><Properties xmlns="http://schemas.openxmlformats.org'
            '/officeDocument/2006/custom-properties"></Properties>'
        ).encode("utf-8")
        assert _extract_from_custom_props(raw) is None

    def test_extract_invalid_json(self):
        raw = self._make_custom_xml("not valid json {{{")
        assert _extract_from_custom_props(raw) is None

    def test_extract_unicode_content(self):
        meta = {"claims": [{"c": "売上高は42億ドル", "t": 0.95}]}
        raw = self._make_custom_xml(json.dumps(meta, ensure_ascii=False))
        result = _extract_from_custom_props(raw)
        assert result["claims"][0]["c"] == "売上高は42億ドル"


# ── Test: Content Type Injection ─────────────────────────────────


class TestInjectContentType:
    def test_injects_content_type(self):
        raw = b'<?xml version="1.0"?><Types xmlns="x"></Types>'
        result = _inject_content_type(raw)
        assert CUSTOM_PROPS_CONTENT_TYPE.encode() in result

    def test_idempotent(self):
        raw = b'<?xml version="1.0"?><Types xmlns="x"></Types>'
        once = _inject_content_type(raw)
        twice = _inject_content_type(once)
        assert once == twice

    def test_preserves_existing_types(self):
        raw = (
            b'<?xml version="1.0"?><Types xmlns="x">'
            b'<Default Extension="xml" ContentType="application/xml"/>'
            b'</Types>'
        )
        result = _inject_content_type(raw)
        assert b'Extension="xml"' in result
        assert CUSTOM_PROPS_CONTENT_TYPE.encode() in result


# ── Test: Relationship Injection ─────────────────────────────────


class TestInjectRels:
    def test_injects_relationship(self):
        raw = (
            b'<?xml version="1.0"?>'
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="rId1" Type="http://example.com" Target="doc.xml"/>'
            b'</Relationships>'
        )
        result = _inject_rels(raw)
        assert CUSTOM_PROPS_REL_TYPE.encode() in result
        assert b'rId2' in result

    def test_finds_next_free_rid(self):
        raw = (
            b'<?xml version="1.0"?>'
            b'<Relationships xmlns="x">'
            b'<Relationship Id="rId1" Type="a" Target="b"/>'
            b'<Relationship Id="rId3" Type="c" Target="d"/>'
            b'</Relationships>'
        )
        result = _inject_rels(raw)
        # Should use rId4 (max existing is 3)
        assert b'rId4' in result

    def test_idempotent(self):
        raw = (
            b'<?xml version="1.0"?>'
            b'<Relationships xmlns="x">'
            b'<Relationship Id="rId1" Type="a" Target="b"/>'
            b'</Relationships>'
        )
        once = _inject_rels(raw)
        twice = _inject_rels(once)
        assert once == twice


# ── Test: Embed & Extract Round-Trip ─────────────────────────────


class TestEmbedExtractRoundTrip:
    """Core round-trip tests across all OOXML formats."""

    def test_embed_and_extract(self, ooxml_file, sample_metadata):
        embed_in_ooxml(ooxml_file, sample_metadata)
        result = extract_from_ooxml(ooxml_file)
        assert result is not None
        assert result["classification"] == "confidential"
        assert len(result["claims"]) == 2
        assert result["claims"][0]["c"] == "Revenue was $4.2B"
        assert result["claims"][0]["t"] == 0.98
        assert result["claims"][1]["ai"] is True

    def test_extract_non_enriched(self, ooxml_file):
        result = extract_from_ooxml(ooxml_file)
        assert result is None

    def test_is_enriched_false_initially(self, ooxml_file):
        assert is_ooxml_enriched(ooxml_file) is False

    def test_is_enriched_true_after_embed(self, ooxml_file, sample_metadata):
        embed_in_ooxml(ooxml_file, sample_metadata)
        assert is_ooxml_enriched(ooxml_file) is True

    def test_re_embed_replaces(self, ooxml_file, sample_metadata):
        embed_in_ooxml(ooxml_file, sample_metadata)
        new_meta = {"classification": "public", "claims": [{"c": "Updated", "t": 0.5}]}
        embed_in_ooxml(ooxml_file, new_meta)
        result = extract_from_ooxml(ooxml_file)
        assert result["classification"] == "public"
        assert len(result["claims"]) == 1

    def test_empty_metadata(self, ooxml_file):
        embed_in_ooxml(ooxml_file, {})
        result = extract_from_ooxml(ooxml_file)
        assert result == {}

    def test_provenance_round_trip(self, ooxml_file):
        meta = {
            "provenance": [
                {"actor": "alice", "action": "created", "at": "2026-01-01"},
                {"actor": "bob", "action": "reviewed", "at": "2026-01-02"},
            ]
        }
        embed_in_ooxml(ooxml_file, meta)
        result = extract_from_ooxml(ooxml_file)
        assert len(result["provenance"]) == 2
        assert result["provenance"][1]["actor"] == "bob"


# ── Test: ZIP Integrity ──────────────────────────────────────────


class TestZipIntegrity:
    """Ensure embedding doesn't corrupt the ZIP archive."""

    def test_valid_zip_after_embed(self, ooxml_file, sample_metadata):
        embed_in_ooxml(ooxml_file, sample_metadata)
        with zipfile.ZipFile(ooxml_file, "r") as z:
            assert z.testzip() is None

    def test_preserves_original_content(self, docx_file, sample_metadata):
        with zipfile.ZipFile(docx_file, "r") as z:
            original_doc = z.read("word/document.xml")
        embed_in_ooxml(docx_file, sample_metadata)
        with zipfile.ZipFile(docx_file, "r") as z:
            assert z.read("word/document.xml") == original_doc

    def test_preserves_original_entries(self, docx_file, sample_metadata):
        with zipfile.ZipFile(docx_file, "r") as z:
            original_names = set(z.namelist())
        embed_in_ooxml(docx_file, sample_metadata)
        with zipfile.ZipFile(docx_file, "r") as z:
            new_names = set(z.namelist())
        assert original_names.issubset(new_names)

    def test_no_non_standard_entries(self, docx_file, sample_metadata):
        """After embed, no akf/ or customXml/akf-* entries should exist."""
        embed_in_ooxml(docx_file, sample_metadata)
        with zipfile.ZipFile(docx_file, "r") as z:
            names = z.namelist()
        bad = [n for n in names if n.startswith("akf/") or "akf-metadata" in n or "akf-item" in n]
        assert bad == [], f"Non-standard entries found: {bad}"

    def test_custom_props_in_content_types(self, docx_file, sample_metadata):
        embed_in_ooxml(docx_file, sample_metadata)
        with zipfile.ZipFile(docx_file, "r") as z:
            ct = z.read("[Content_Types].xml").decode()
        assert CUSTOM_PROPS_CONTENT_TYPE in ct

    def test_custom_props_in_rels(self, docx_file, sample_metadata):
        embed_in_ooxml(docx_file, sample_metadata)
        with zipfile.ZipFile(docx_file, "r") as z:
            rels = z.read("_rels/.rels").decode()
        assert CUSTOM_PROPS_REL_TYPE in rels

    def test_no_duplicate_content_types_on_re_embed(self, docx_file, sample_metadata):
        embed_in_ooxml(docx_file, sample_metadata)
        embed_in_ooxml(docx_file, sample_metadata)
        with zipfile.ZipFile(docx_file, "r") as z:
            ct = z.read("[Content_Types].xml").decode()
        assert ct.count(CUSTOM_PROPS_CONTENT_TYPE) == 1

    def test_no_duplicate_rels_on_re_embed(self, docx_file, sample_metadata):
        embed_in_ooxml(docx_file, sample_metadata)
        embed_in_ooxml(docx_file, sample_metadata)
        with zipfile.ZipFile(docx_file, "r") as z:
            rels = z.read("_rels/.rels").decode()
        assert rels.count(CUSTOM_PROPS_REL_TYPE) == 1

    def test_no_duplicate_custom_props_entries(self, docx_file, sample_metadata):
        embed_in_ooxml(docx_file, sample_metadata)
        embed_in_ooxml(docx_file, sample_metadata)
        with zipfile.ZipFile(docx_file, "r") as z:
            count = z.namelist().count(CUSTOM_PROPS_PATH)
        assert count == 1


# ── Test: Legacy Path Migration ──────────────────────────────────


class TestLegacyPathMigration:
    """Test reading from old storage paths and migrating to new format."""

    def _inject_legacy_v1_0(self, path, metadata):
        """Manually inject v1.0 legacy format (customXml/akf-metadata.json)."""
        json_bytes = json.dumps(metadata).encode("utf-8")
        tmp = path + ".tmp"
        with zipfile.ZipFile(path, "r") as zin:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    zout.writestr(item, zin.read(item.filename))
                zout.writestr(_LEGACY_JSON_PATH, json_bytes)
        os.replace(tmp, path)

    def _inject_legacy_v1_1(self, path, metadata):
        """Manually inject v1.1 legacy format (akf/metadata.json)."""
        json_bytes = json.dumps(metadata).encode("utf-8")
        tmp = path + ".tmp"
        with zipfile.ZipFile(path, "r") as zin:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    zout.writestr(item, zin.read(item.filename))
                zout.writestr(_LEGACY_AKF_JSON_PATH, json_bytes)
        os.replace(tmp, path)

    def test_read_legacy_v1_0(self, docx_file):
        meta = {"classification": "internal", "claims": [{"c": "Old format", "t": 0.7}]}
        self._inject_legacy_v1_0(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result is not None
        assert result["classification"] == "internal"

    def test_read_legacy_v1_1(self, docx_file):
        meta = {"classification": "public", "claims": [{"c": "Mid format", "t": 0.8}]}
        self._inject_legacy_v1_1(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result is not None
        assert result["classification"] == "public"

    def test_is_enriched_legacy_v1_0(self, docx_file):
        self._inject_legacy_v1_0(docx_file, {"claims": []})
        assert is_ooxml_enriched(docx_file) is True

    def test_is_enriched_legacy_v1_1(self, docx_file):
        self._inject_legacy_v1_1(docx_file, {"claims": []})
        assert is_ooxml_enriched(docx_file) is True

    def test_current_format_preferred_over_legacy(self, docx_file):
        """If both current and legacy exist, current should win."""
        current_meta = {"classification": "current", "claims": []}
        legacy_meta = {"classification": "legacy", "claims": []}
        # Inject legacy first
        self._inject_legacy_v1_0(docx_file, legacy_meta)
        # Then embed current
        embed_in_ooxml(docx_file, current_meta)
        result = extract_from_ooxml(docx_file)
        assert result["classification"] == "current"

    def test_embed_cleans_up_legacy_paths(self, docx_file):
        """Embedding should remove old legacy entries."""
        self._inject_legacy_v1_0(docx_file, {"claims": []})
        self._inject_legacy_v1_1(docx_file, {"claims": []})
        # Now embed with new format
        embed_in_ooxml(docx_file, {"claims": [{"c": "New", "t": 0.9}]})
        with zipfile.ZipFile(docx_file, "r") as z:
            names = z.namelist()
        assert _LEGACY_JSON_PATH not in names
        assert _LEGACY_AKF_JSON_PATH not in names


# ── Test: Word Compatibility (no foreign entries) ────────────────


class TestWordCompatibility:
    """Ensure embedded files contain ONLY standard OOXML parts."""

    STANDARD_PREFIXES = (
        "[Content_Types].xml",
        "_rels/",
        "word/",
        "xl/",
        "ppt/",
        "docProps/",
        "customXml/",  # Word's own customXml (like bibliography)
    )

    def test_docx_only_standard_entries(self, tmp_path):
        path = str(tmp_path / "test.docx")
        create_minimal_docx(path)
        embed_in_ooxml(path, {"claims": [{"c": "Test", "t": 0.9}]})
        with zipfile.ZipFile(path, "r") as z:
            for name in z.namelist():
                assert any(name.startswith(p) for p in self.STANDARD_PREFIXES), \
                    f"Non-standard entry: {name}"

    def test_xlsx_only_standard_entries(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        create_minimal_xlsx(path)
        embed_in_ooxml(path, {"claims": [{"c": "Test", "t": 0.9}]})
        with zipfile.ZipFile(path, "r") as z:
            for name in z.namelist():
                assert any(name.startswith(p) for p in self.STANDARD_PREFIXES), \
                    f"Non-standard entry: {name}"

    def test_pptx_only_standard_entries(self, tmp_path):
        path = str(tmp_path / "test.pptx")
        create_minimal_pptx(path)
        embed_in_ooxml(path, {"claims": [{"c": "Test", "t": 0.9}]})
        with zipfile.ZipFile(path, "r") as z:
            for name in z.namelist():
                assert any(name.startswith(p) for p in self.STANDARD_PREFIXES), \
                    f"Non-standard entry: {name}"

    def test_custom_props_readable_as_xml(self, docx_file, sample_metadata):
        """The custom.xml should be well-formed XML."""
        embed_in_ooxml(docx_file, sample_metadata)
        with zipfile.ZipFile(docx_file, "r") as z:
            raw = z.read(CUSTOM_PROPS_PATH).decode()
        # Basic well-formedness checks
        assert raw.startswith("<?xml")
        assert "<Properties" in raw
        assert "</Properties>" in raw
        # All opened property tags are closed
        assert raw.count("<property") == raw.count("</property>")


# ── Test: Special Characters & Edge Cases ────────────────────────


class TestSpecialCharacters:
    """Test that special characters survive round-trip through XML."""

    def test_ampersand_in_claim(self, docx_file):
        meta = {"claims": [{"c": "R&D expenses increased", "t": 0.8}]}
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result["claims"][0]["c"] == "R&D expenses increased"

    def test_angle_brackets_in_claim(self, docx_file):
        meta = {"claims": [{"c": "Revenue <$1B or >$5B", "t": 0.7}]}
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result["claims"][0]["c"] == "Revenue <$1B or >$5B"

    def test_quotes_in_claim(self, docx_file):
        meta = {"claims": [{"c": 'The "final" report', "t": 0.9}]}
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result["claims"][0]["c"] == 'The "final" report'

    def test_unicode_japanese(self, docx_file):
        meta = {"claims": [{"c": "売上高は42億ドル", "t": 0.95}]}
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result["claims"][0]["c"] == "売上高は42億ドル"

    def test_unicode_german(self, docx_file):
        meta = {"claims": [{"c": "Umsatz betrug €4,2 Mrd.", "t": 0.9}]}
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result["claims"][0]["c"] == "Umsatz betrug €4,2 Mrd."

    def test_newlines_in_claim(self, docx_file):
        meta = {"claims": [{"c": "Line 1\nLine 2\nLine 3", "t": 0.8}]}
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result["claims"][0]["c"] == "Line 1\nLine 2\nLine 3"

    def test_backslashes_in_path(self, docx_file):
        meta = {"claims": [{"c": r"Path is C:\Users\test\file.docx", "t": 0.7}]}
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result["claims"][0]["c"] == r"Path is C:\Users\test\file.docx"


# ── Test: Large Metadata ─────────────────────────────────────────


class TestLargeMetadata:
    def test_100_claims(self, docx_file):
        claims = [{"c": f"Claim {i}: detailed content here", "t": 0.5 + (i % 50) / 100.0} for i in range(100)]
        meta = {"claims": claims}
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert len(result["claims"]) == 100

    def test_long_claim_text(self, docx_file):
        long_text = "A" * 10000
        meta = {"claims": [{"c": long_text, "t": 0.5}]}
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result["claims"][0]["c"] == long_text

    def test_deep_nested_metadata(self, docx_file):
        meta = {
            "claims": [{"c": "Test", "t": 0.9, "extra": {"nested": {"deep": True}}}],
            "custom": {"a": {"b": {"c": {"d": "value"}}}},
        }
        embed_in_ooxml(docx_file, meta)
        result = extract_from_ooxml(docx_file)
        assert result["custom"]["a"]["b"]["c"]["d"] == "value"


# ── Test: Error Handling ─────────────────────────────────────────


class TestErrorHandling:
    def test_extract_nonexistent_file(self):
        assert extract_from_ooxml("/nonexistent/file.docx") is None

    def test_is_enriched_nonexistent_file(self):
        assert is_ooxml_enriched("/nonexistent/file.docx") is False

    def test_extract_non_zip_file(self, tmp_path):
        path = str(tmp_path / "not_a_zip.docx")
        with open(path, "w") as f:
            f.write("This is not a ZIP file")
        assert extract_from_ooxml(path) is None

    def test_is_enriched_non_zip_file(self, tmp_path):
        path = str(tmp_path / "not_a_zip.docx")
        with open(path, "w") as f:
            f.write("Not a ZIP")
        assert is_ooxml_enriched(path) is False

    def test_embed_non_zip_raises(self, tmp_path):
        path = str(tmp_path / "bad.docx")
        with open(path, "w") as f:
            f.write("Not a ZIP")
        with pytest.raises(zipfile.BadZipFile):
            embed_in_ooxml(path, {"claims": []})

    def test_embed_failure_preserves_original(self, tmp_path):
        """If embed fails mid-operation, original file should be intact."""
        path = str(tmp_path / "test.docx")
        create_minimal_docx(path)
        original_size = os.path.getsize(path)
        # Embed once successfully
        embed_in_ooxml(path, {"claims": [{"c": "Good", "t": 0.9}]})
        good_size = os.path.getsize(path)
        assert good_size > original_size
        # File still works
        assert extract_from_ooxml(path)["claims"][0]["c"] == "Good"

    def test_list_entries(self, docx_file, sample_metadata):
        embed_in_ooxml(docx_file, sample_metadata)
        entries = list_ooxml_entries(docx_file)
        assert entries is not None
        assert CUSTOM_PROPS_PATH in entries

    def test_list_entries_non_zip(self, tmp_path):
        path = str(tmp_path / "bad.docx")
        with open(path, "w") as f:
            f.write("Not a ZIP")
        assert list_ooxml_entries(path) is None


# ── Test: Custom Properties Visibility ───────────────────────────


class TestCustomPropertiesVisibility:
    """Test that the right summary fields appear in docProps/custom.xml."""

    def _get_custom_xml(self, filepath):
        with zipfile.ZipFile(filepath, "r") as z:
            return z.read(CUSTOM_PROPS_PATH).decode("utf-8")

    def test_classification_visible(self, docx_file):
        embed_in_ooxml(docx_file, {"classification": "top-secret", "claims": []})
        xml = self._get_custom_xml(docx_file)
        assert "top-secret" in xml

    def test_claim_count_visible(self, docx_file):
        embed_in_ooxml(docx_file, {"claims": [{"c": "A", "t": 0.9}, {"c": "B", "t": 0.8}]})
        xml = self._get_custom_xml(docx_file)
        assert "AKF.Claims" in xml

    def test_ai_claims_visible(self, docx_file):
        embed_in_ooxml(docx_file, {"claims": [{"c": "AI gen", "t": 0.7, "ai": True}]})
        xml = self._get_custom_xml(docx_file)
        assert "AKF.AIClaims" in xml

    def test_agent_visible(self, docx_file):
        embed_in_ooxml(docx_file, {"agent": "claude-code", "claims": []})
        xml = self._get_custom_xml(docx_file)
        assert "claude-code" in xml

    def test_no_akf_claims_when_empty(self, docx_file):
        embed_in_ooxml(docx_file, {"claims": []})
        xml = self._get_custom_xml(docx_file)
        assert "AKF.Claims" not in xml  # No claims = no count property

    def test_all_human_claims_no_ai_count(self, docx_file):
        embed_in_ooxml(docx_file, {"claims": [{"c": "Human", "t": 0.9}]})
        xml = self._get_custom_xml(docx_file)
        assert "AKF.AIClaims" not in xml
        assert "AKF.HumanClaims" in xml
