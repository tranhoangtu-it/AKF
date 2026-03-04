"""Tests for the stamp() one-line API."""

import json

import akf
from akf import AKF, Evidence, stamp
from akf.stamp import parse_evidence_string


class TestParseEvidenceString:
    """Tests for evidence string auto-detection."""

    def test_test_pass_pattern(self):
        ev = parse_evidence_string("42/42 tests passed")
        assert ev.type == "test_pass"
        assert ev.detail == "42/42 tests passed"
        assert ev.timestamp is not None

    def test_all_tests_pass(self):
        ev = parse_evidence_string("all tests pass")
        assert ev.type == "test_pass"

    def test_pytest_pass(self):
        ev = parse_evidence_string("pytest: 100 passed, 0 failed")
        assert ev.type == "test_pass"

    def test_type_check(self):
        ev = parse_evidence_string("mypy: 0 errors")
        assert ev.type == "type_check"

    def test_type_check_clean(self):
        ev = parse_evidence_string("type check clean")
        assert ev.type == "type_check"

    def test_lint_clean(self):
        ev = parse_evidence_string("lint clean")
        assert ev.type == "lint_clean"

    def test_ruff_lint(self):
        ev = parse_evidence_string("ruff: 0 issues")
        assert ev.type == "lint_clean"

    def test_ci_pass(self):
        ev = parse_evidence_string("CI passed")
        assert ev.type == "ci_pass"

    def test_build_success(self):
        ev = parse_evidence_string("build successful")
        assert ev.type == "ci_pass"

    def test_human_review(self):
        ev = parse_evidence_string("approved by @alice")
        assert ev.type == "human_review"

    def test_code_review(self):
        ev = parse_evidence_string("code review complete")
        assert ev.type == "human_review"

    def test_unknown_falls_back(self):
        ev = parse_evidence_string("some random text")
        assert ev.type == "other"
        assert ev.detail == "some random text"


class TestStamp:
    """Tests for stamp() basics."""

    def test_stamp_basic(self):
        unit = stamp("Fixed auth bypass")
        assert isinstance(unit, AKF)
        assert len(unit.claims) == 1
        assert unit.claims[0].content == "Fixed auth bypass"
        assert unit.claims[0].confidence == 0.7
        assert unit.claims[0].ai_generated is True
        assert unit.claims[0].kind == "claim"

    def test_stamp_defaults(self):
        unit = stamp("test")
        assert unit.classification == "internal"
        assert unit.inherit_classification is True
        assert unit.allow_external is False
        assert unit.claims[0].authority_tier == 5  # AI default

    def test_stamp_with_kind(self):
        unit = stamp("Refactored module", kind="code_change")
        assert unit.claims[0].kind == "code_change"

    def test_stamp_with_confidence(self):
        unit = stamp("test", confidence=0.95)
        assert unit.claims[0].confidence == 0.95

    def test_stamp_with_evidence(self):
        unit = stamp("Fixed bug", evidence=["42/42 tests passed", "mypy: 0 errors"])
        assert len(unit.claims[0].evidence) == 2
        assert unit.claims[0].evidence[0].type == "test_pass"
        assert unit.claims[0].evidence[1].type == "type_check"

    def test_stamp_with_evidence_objects(self):
        ev = Evidence(type="test_pass", detail="ok")
        unit = stamp("test", evidence=[ev])
        assert unit.claims[0].evidence[0].type == "test_pass"

    def test_stamp_with_evidence_dicts(self):
        unit = stamp("test", evidence=[{"type": "ci_pass", "detail": "green"}])
        assert unit.claims[0].evidence[0].type == "ci_pass"

    def test_stamp_agent_context(self):
        unit = stamp("test", agent="claude-code", model="claude-sonnet-4-20250514",
                     tools=["bash", "edit"], session="sess-abc")
        assert unit.agent == "claude-code"
        assert unit.model == "claude-sonnet-4-20250514"
        assert unit.tools == ["bash", "edit"]
        assert unit.session == "sess-abc"

    def test_stamp_serialization(self):
        unit = stamp("test", kind="code_change",
                     evidence=["tests pass"], agent="test-agent")
        json_str = unit.to_json(compact=False)
        data = json.loads(json_str)
        assert data["agent"] == "test-agent"
        assert data["claims"][0]["kind"] == "code_change"
        assert len(data["claims"][0]["evidence"]) == 1

    def test_stamp_kwargs_passthrough(self):
        unit = stamp("test", source="manual", authority_tier=2, verified=True)
        c = unit.claims[0]
        assert c.source == "manual"
        assert c.authority_tier == 2
        assert c.verified is True

    def test_stamp_not_ai(self):
        unit = stamp("human observation", ai_generated=False)
        assert unit.claims[0].ai_generated is False
        assert unit.claims[0].authority_tier == 3  # non-AI default

    def test_stamp_produces_valid_akf(self):
        unit = stamp("test")
        result = akf.validate(unit)
        assert result.valid is True
