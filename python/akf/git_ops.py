"""AKF v1.0 — Git integration via git notes.

Stores AKF metadata as git notes under refs/notes/akf,
which doesn't conflict with regular git notes.

Usage:
    import akf
    akf.stamp_commit(content="Refactored auth", kind="code_change",
                     evidence=["all tests pass"], agent="claude-code")
    unit = akf.read_commit()
    print(akf.trust_log(n=10))
"""

import json
import subprocess
from typing import Optional

from .models import AKF
from .stamp import stamp
from .trust import effective_trust


def _run_git(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    cmd = ["git"] + list(args)
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )


def stamp_commit(
    content: str = "",
    *,
    ref: str = "HEAD",
    kind: str = "code_change",
    evidence: Optional[list] = None,
    agent: Optional[str] = None,
    model: Optional[str] = None,
    confidence: float = 0.7,
    **kwargs,
) -> AKF:
    """Stamp the current (or specified) git commit with AKF metadata.

    Writes AKF JSON to git notes under refs/notes/akf.

    Args:
        content: Description of the change.
        ref: Git ref to annotate (default HEAD).
        kind: Kind of claim (default "code_change").
        evidence: Evidence list (strings, dicts, or Evidence objects).
        agent: Agent identifier.
        model: Model identifier.
        confidence: Trust score (default 0.7).
        **kwargs: Extra fields passed to stamp().

    Returns:
        The AKF unit that was written.
    """
    if not content:
        # Use the commit message as content
        result = _run_git("log", "-1", "--format=%s", ref)
        content = result.stdout.strip() or "commit"

    unit = stamp(
        content,
        confidence=confidence,
        kind=kind,
        evidence=evidence,
        agent=agent,
        model=model,
        **kwargs,
    )

    note_json = unit.to_json(compact=True)
    _run_git("notes", "--ref=akf", "add", "-f", "-m", note_json, ref)

    return unit


def read_commit(ref: str = "HEAD") -> Optional[AKF]:
    """Read AKF metadata from a git commit's notes.

    Args:
        ref: Git ref to read from (default HEAD).

    Returns:
        AKF unit if notes exist, None otherwise.
    """
    result = _run_git("notes", "--ref=akf", "show", ref, check=False)
    if result.returncode != 0:
        return None

    note_text = result.stdout.strip()
    if not note_text:
        return None

    try:
        data = json.loads(note_text)
        return AKF(**data)
    except (json.JSONDecodeError, Exception):
        return None


def trust_log(n: int = 10, ref: str = "HEAD") -> str:
    """Show a trust-annotated git log.

    Displays recent commits with AKF trust indicators:
    + = ACCEPT, ~ = LOW, - = REJECT, ? = no AKF metadata

    Args:
        n: Number of commits to show.
        ref: Starting ref.

    Returns:
        Formatted trust log string.
    """
    result = _run_git("log", f"-{n}", "--format=%H %h %s", ref)
    if result.returncode != 0:
        return ""

    lines = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(" ", 2)
        if len(parts) < 3:
            continue
        full_hash, short_hash, subject = parts

        unit = read_commit(full_hash)
        if unit is None:
            indicator = "?"
            score_str = "     "
            kind_str = ""
        else:
            claim = unit.claims[0]
            tr = effective_trust(claim)
            if tr.decision == "ACCEPT":
                indicator = "+"
            elif tr.decision == "LOW":
                indicator = "~"
            else:
                indicator = "-"
            score_str = f"{tr.score:.2f}"
            kind_str = f" [{claim.kind}]" if claim.kind else ""

        lines.append(f"  {indicator} {short_hash} {score_str} {subject}{kind_str}")

    header = "  Trust Log (refs/notes/akf)"
    separator = "  " + "-" * 50
    legend = "  + ACCEPT  ~ LOW  - REJECT  ? no metadata"

    return "\n".join([header, separator] + lines + [separator, legend])
