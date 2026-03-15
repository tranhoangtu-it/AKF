"""End-to-end integration tests for the AKF Hugging Face Gradio Space.

Tests all 3 tabs: Stamp & Inspect, Trust Analysis, Security Detections.
Covers happy paths, edge cases, boundary values, and error handling.

Run:  cd huggingface && python -m pytest test_app.py -v
"""

import json
import sys
import os

import pytest

# Import the app functions directly (no Gradio UI needed)
sys.path.insert(0, os.path.dirname(__file__))
from logic import stamp_and_inspect, trust_analysis, run_detections, EXAMPLE_UNIT


# ═══════════════════════════════════════════════════════════════════════════
# Tab 1: Stamp & Inspect
# ═══════════════════════════════════════════════════════════════════════════

class TestStampAndInspect:
    """Tests for the Stamp & Inspect tab."""

    def test_basic_stamp(self):
        """Basic claim produces valid inspect text and JSON."""
        inspect_text, raw_json = stamp_and_inspect(
            "Revenue projected at $42.1B", 0.85, "financial-erp", "1", "gpt-4o", True
        )
        assert "Revenue projected at $42.1B" in inspect_text
        assert "AKF" in inspect_text

        data = json.loads(raw_json)
        assert data["version"] in ("1.0", "1.1")
        assert len(data["claims"]) == 1
        assert data["claims"][0]["content"] == "Revenue projected at $42.1B"
        assert data["claims"][0]["confidence"] == 0.85
        assert data["claims"][0]["authority_tier"] == 1

    def test_json_is_descriptive_format(self):
        """JSON output uses descriptive keys (not compact wire format)."""
        _, raw_json = stamp_and_inspect("Test claim", 0.7, "", "3", "", True)
        data = json.loads(raw_json)
        # Descriptive format uses "content", "confidence", not "c", "t"
        assert "content" in data["claims"][0]
        assert "confidence" in data["claims"][0]

    def test_empty_content_returns_error(self):
        """Empty claim text returns a user-friendly message."""
        inspect_text, raw_json = stamp_and_inspect("", 0.5, "", "3", "", True)
        assert "Please enter a claim" in inspect_text
        assert raw_json == "{}"

    def test_whitespace_only_content(self):
        """Whitespace-only input treated as empty."""
        inspect_text, raw_json = stamp_and_inspect("   \n\t  ", 0.5, "", "3", "", True)
        assert "Please enter a claim" in inspect_text
        assert raw_json == "{}"

    def test_confidence_zero(self):
        """Confidence 0.0 is a valid edge case."""
        inspect_text, raw_json = stamp_and_inspect("Low trust claim", 0.0, "", "5", "", True)
        data = json.loads(raw_json)
        assert data["claims"][0]["confidence"] == 0.0

    def test_confidence_one(self):
        """Confidence 1.0 is a valid edge case."""
        inspect_text, raw_json = stamp_and_inspect("Certain claim", 1.0, "", "1", "", True)
        data = json.loads(raw_json)
        assert data["claims"][0]["confidence"] == 1.0

    def test_all_authority_tiers(self):
        """All 5 authority tiers are accepted and reflected in output."""
        for tier in ["1", "2", "3", "4", "5"]:
            _, raw_json = stamp_and_inspect("Tier test", 0.7, "", tier, "", True)
            data = json.loads(raw_json)
            assert data["claims"][0]["authority_tier"] == int(tier)

    def test_source_included_when_provided(self):
        """Source field appears in JSON when user provides it."""
        _, raw_json = stamp_and_inspect("Claim", 0.7, "sec-filing", "2", "", True)
        data = json.loads(raw_json)
        assert data["claims"][0]["source"] == "sec-filing"

    def test_source_omitted_when_empty(self):
        """Empty source field uses default, not empty string."""
        _, raw_json = stamp_and_inspect("Claim", 0.7, "", "3", "", True)
        data = json.loads(raw_json)
        # Should not be empty string — either omitted or set to "unspecified"
        source = data["claims"][0].get("source", "unspecified")
        assert source != ""

    def test_model_included_when_provided(self):
        """Model field appears in JSON when user provides it."""
        _, raw_json = stamp_and_inspect("Claim", 0.7, "", "3", "claude-sonnet", True)
        data = json.loads(raw_json)
        # Model is on the unit level, not claim level
        assert data.get("model") == "claude-sonnet" or \
            any("claude-sonnet" in str(v) for v in data.values())

    def test_ai_generated_true(self):
        """AI-generated flag is set when checked."""
        _, raw_json = stamp_and_inspect("AI claim", 0.7, "", "3", "", True)
        data = json.loads(raw_json)
        assert data["claims"][0].get("ai_generated") is True

    def test_ai_generated_false(self):
        """AI-generated flag is false when unchecked."""
        _, raw_json = stamp_and_inspect("Human claim", 0.7, "", "3", "", False)
        data = json.loads(raw_json)
        assert data["claims"][0].get("ai_generated") is False

    def test_inspect_shows_tier(self):
        """Inspect output reflects authority tier."""
        inspect_text, _ = stamp_and_inspect("Expert claim", 0.95, "", "1", "", True)
        assert "Tier 1" in inspect_text

    def test_inspect_shows_confidence(self):
        """Inspect output includes the confidence score."""
        inspect_text, _ = stamp_and_inspect("Claim", 0.42, "", "3", "", True)
        assert "0.42" in inspect_text

    def test_json_is_valid_parseable(self):
        """JSON output is always valid JSON."""
        _, raw_json = stamp_and_inspect("Parse test", 0.7, "src", "3", "model", True)
        data = json.loads(raw_json)  # Should not raise
        assert isinstance(data, dict)

    def test_special_characters_in_content(self):
        """Claims with special characters are handled properly."""
        content = 'He said "hello" & goodbye <script>alert(1)</script>'
        inspect_text, raw_json = stamp_and_inspect(content, 0.7, "", "3", "", True)
        data = json.loads(raw_json)
        assert data["claims"][0]["content"] == content

    def test_unicode_content(self):
        """Unicode content is preserved."""
        content = "Revenue: \u00a5420B \u2014 Q3 \u2019 analysis"
        _, raw_json = stamp_and_inspect(content, 0.7, "", "3", "", True)
        data = json.loads(raw_json)
        assert data["claims"][0]["content"] == content

    def test_long_content(self):
        """Very long claim text is handled without errors."""
        content = "This is a long claim. " * 500
        inspect_text, raw_json = stamp_and_inspect(content, 0.7, "", "3", "", True)
        data = json.loads(raw_json)
        assert data["claims"][0]["content"] == content.strip()

    def test_returns_two_outputs(self):
        """Function returns exactly 2 values (inspect text, JSON)."""
        result = stamp_and_inspect("Test", 0.7, "", "3", "", True)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    def test_json_has_id(self):
        """Stamped unit has an auto-generated ID."""
        _, raw_json = stamp_and_inspect("ID test", 0.7, "", "3", "", True)
        data = json.loads(raw_json)
        assert "id" in data
        assert data["id"].startswith("akf-")

    def test_json_has_claim_id(self):
        """Each claim has an auto-generated ID."""
        _, raw_json = stamp_and_inspect("Claim ID test", 0.7, "", "3", "", True)
        data = json.loads(raw_json)
        assert "id" in data["claims"][0]
        assert len(data["claims"][0]["id"]) > 0

    def test_content_is_stripped(self):
        """Leading/trailing whitespace is stripped from content."""
        _, raw_json = stamp_and_inspect("  padded claim  ", 0.7, "", "3", "", True)
        data = json.loads(raw_json)
        assert data["claims"][0]["content"] == "padded claim"

    def test_source_is_stripped(self):
        """Leading/trailing whitespace is stripped from source."""
        _, raw_json = stamp_and_inspect("Test", 0.7, "  my-source  ", "3", "", True)
        data = json.loads(raw_json)
        assert data["claims"][0]["source"] == "my-source"


# ═══════════════════════════════════════════════════════════════════════════
# Tab 2: Trust Analysis
# ═══════════════════════════════════════════════════════════════════════════

class TestTrustAnalysis:
    """Tests for the Trust Analysis tab."""

    def test_basic_trust_output(self):
        """Trust analysis returns a formatted breakdown."""
        result = trust_analysis("Revenue $4.2B", 0.98, "SEC", "1", "", False)
        assert "Trust Analysis" in result
        assert "Revenue $4.2B" in result

    def test_empty_content_returns_error(self):
        """Empty claim text returns a user-friendly message."""
        result = trust_analysis("", 0.5, "", "3", "", True)
        assert "Please enter a claim" in result

    def test_whitespace_only(self):
        """Whitespace-only returns error."""
        result = trust_analysis("   ", 0.5, "", "3", "", True)
        assert "Please enter a claim" in result

    def test_shows_confidence(self):
        """Output includes the base confidence value."""
        result = trust_analysis("Test", 0.85, "", "3", "", True)
        assert "0.85" in result

    def test_shows_authority_weight(self):
        """Output includes authority tier weight."""
        result = trust_analysis("Test", 0.85, "", "1", "", True)
        assert "1.00" in result  # Tier 1 weight = 1.00

    def test_shows_decision(self):
        """Output includes a trust decision (ACCEPT, LOW, or REJECT)."""
        result = trust_analysis("Test", 0.85, "", "1", "", False)
        assert any(d in result for d in ["ACCEPT", "LOW", "REJECT"])

    def test_shows_effective_trust(self):
        """Output shows the computed effective trust score."""
        result = trust_analysis("Test", 0.85, "", "3", "", True)
        assert "Effective trust" in result

    def test_tier1_human_high_confidence_accepts(self):
        """Expert human claim with high confidence should ACCEPT."""
        result = trust_analysis("Expert finding", 0.95, "lab-result", "1", "", False)
        assert "ACCEPT" in result

    def test_tier5_low_confidence_rejects_or_low(self):
        """Speculative claim with low confidence should be LOW or REJECT."""
        result = trust_analysis("Wild guess", 0.3, "", "5", "", True)
        assert any(d in result for d in ["LOW", "REJECT"])

    def test_ai_origin_weight(self):
        """AI-generated claims show origin weight ~0.70."""
        result = trust_analysis("AI claim", 0.85, "", "3", "", True)
        assert "0.70" in result or "ai" in result.lower()

    def test_all_tiers_produce_output(self):
        """All 5 authority tiers produce valid trust analysis."""
        for tier in ["1", "2", "3", "4", "5"]:
            result = trust_analysis("Tier test", 0.7, "", tier, "", True)
            assert "Trust Analysis" in result
            assert "Effective trust" in result

    def test_confidence_zero(self):
        """Zero confidence produces a valid analysis."""
        result = trust_analysis("Zero conf", 0.0, "", "3", "", True)
        assert "Trust Analysis" in result
        assert "0.00" in result or "0.0" in result

    def test_confidence_one(self):
        """Full confidence produces a valid analysis."""
        result = trust_analysis("Full conf", 1.0, "", "1", "", False)
        assert "Trust Analysis" in result
        assert "1.0" in result

    def test_shows_evidence_status(self):
        """Output mentions evidence grounding status."""
        result = trust_analysis("Claim", 0.7, "", "3", "", True)
        assert "Evidence" in result or "evidence" in result

    def test_returns_string(self):
        """Trust analysis returns a single string."""
        result = trust_analysis("Test", 0.7, "", "3", "", True)
        assert isinstance(result, str)

    def test_multiline_output(self):
        """Output is multiline with breakdown rows."""
        result = trust_analysis("Test", 0.7, "", "3", "", True)
        lines = result.strip().split("\n")
        assert len(lines) >= 5  # Header + several breakdown rows


# ═══════════════════════════════════════════════════════════════════════════
# Tab 3: Security Detections
# ═══════════════════════════════════════════════════════════════════════════

class TestSecurityDetections:
    """Tests for the Security Detections tab."""

    def test_example_unit_runs(self):
        """The pre-loaded example unit produces a detection report."""
        result = run_detections(EXAMPLE_UNIT)
        assert "Detection Report" in result
        assert "triggered" in result

    def test_example_unit_has_detections(self):
        """Example unit (unreviewed AI claims) should trigger detections."""
        result = run_detections(EXAMPLE_UNIT)
        # Should NOT be "All clear"
        assert "All clear" not in result

    def test_example_unit_specific_detections(self):
        """Example unit should trigger key detection classes."""
        result = run_detections(EXAMPLE_UNIT)
        # Low confidence claim (0.3) + AI without review + ungrounded
        assert "trust_below_threshold" in result
        assert "ai_content_without_review" in result

    def test_empty_input(self):
        """Empty input returns a user-friendly message."""
        result = run_detections("")
        assert "Please paste" in result

    def test_whitespace_only_input(self):
        """Whitespace-only returns error."""
        result = run_detections("   \n\t  ")
        assert "Please paste" in result

    def test_invalid_json(self):
        """Malformed JSON returns a clear error."""
        result = run_detections("{not valid json}")
        assert "Invalid JSON" in result

    def test_invalid_akf_structure(self):
        """Valid JSON but invalid AKF structure returns an error."""
        result = run_detections('{"foo": "bar"}')
        assert "Could not parse AKF unit" in result

    def test_clean_unit(self):
        """Well-formed unit with human review passes all detections."""
        clean = json.dumps({
            "version": "1.1",
            "claims": [{
                "content": "Revenue $4.2B",
                "confidence": 0.98,
                "authority_tier": 1,
                "verified": True,
                "source": "SEC 10-Q",
                "ai_generated": False,
                "evidence": [{"type": "human_review", "detail": "CFO reviewed"}],
            }],
            "classification": "internal",
            "prov": [{"hop": 1, "by": "analyst@corp.com", "at": "2026-01-01T00:00:00Z", "action": "create"}],
        })
        result = run_detections(clean)
        assert "Detection Report" in result
        # A well-formed human-authored claim should be largely clean
        assert "0 critical" in result

    def test_hallucination_risk_detection(self):
        """High-confidence AI claim with no evidence triggers hallucination risk."""
        risky = json.dumps({
            "version": "1.1",
            "claims": [{
                "content": "The product will 10x revenue",
                "confidence": 0.99,
                "authority_tier": 1,
                "ai_generated": True,
                "source": "unspecified",
            }],
        })
        result = run_detections(risky)
        assert "hallucination_risk" in result

    def test_excessive_ai_concentration(self):
        """100% AI claims triggers excessive AI concentration."""
        ai_heavy = json.dumps({
            "version": "1.1",
            "claims": [
                {"content": f"AI claim {i}", "confidence": 0.8, "ai_generated": True}
                for i in range(5)
            ],
        })
        result = run_detections(ai_heavy)
        assert "excessive_ai_concentration" in result

    def test_provenance_gap_detection(self):
        """Missing provenance chain triggers provenance gap."""
        no_prov = json.dumps({
            "version": "1.1",
            "claims": [{
                "content": "Claim without provenance",
                "confidence": 0.7,
                "ai_generated": True,
            }],
        })
        result = run_detections(no_prov)
        assert "provenance_gap" in result

    def test_report_shows_severity(self):
        """Detection results include severity levels."""
        result = run_detections(EXAMPLE_UNIT)
        assert any(s in result for s in ["critical", "high", "medium", "low", "info"])

    def test_report_shows_recommendations(self):
        """Triggered detections include recommendations."""
        result = run_detections(EXAMPLE_UNIT)
        assert "Recommendation" in result

    def test_report_shows_findings(self):
        """Triggered detections include specific findings."""
        result = run_detections(EXAMPLE_UNIT)
        # Findings are bulleted with " - "
        assert " - " in result

    def test_report_header_counts(self):
        """Report header includes triggered, critical, and high counts."""
        result = run_detections(EXAMPLE_UNIT)
        first_line = result.split("\n")[0]
        assert "triggered" in first_line
        assert "critical" in first_line
        assert "high" in first_line

    def test_single_claim_unit(self):
        """Single-claim unit works correctly."""
        single = json.dumps({
            "version": "1.1",
            "claims": [{
                "content": "Single claim",
                "confidence": 0.5,
                "ai_generated": True,
            }],
        })
        result = run_detections(single)
        assert "Detection Report" in result

    def test_multi_claim_unit(self):
        """Multi-claim unit processes all claims."""
        multi = json.dumps({
            "version": "1.1",
            "claims": [
                {"content": f"Claim {i}", "confidence": 0.5 + i * 0.1, "ai_generated": True}
                for i in range(5)
            ],
        })
        result = run_detections(multi)
        assert "Detection Report" in result

    def test_unicode_in_json(self):
        """Unicode characters in JSON input are handled."""
        unicode_unit = json.dumps({
            "version": "1.1",
            "claims": [{
                "content": "Revenue: \u00a5420B \u2014 exceeds forecast",
                "confidence": 0.8,
            }],
        })
        result = run_detections(unicode_unit)
        assert "Detection Report" in result

    def test_returns_string(self):
        """Function returns a single string."""
        result = run_detections(EXAMPLE_UNIT)
        assert isinstance(result, str)

    def test_low_trust_threshold_claim(self):
        """Very low confidence claim triggers trust_below_threshold."""
        low = json.dumps({
            "version": "1.1",
            "claims": [{
                "content": "Uncertain speculation",
                "confidence": 0.1,
                "authority_tier": 5,
                "ai_generated": True,
            }],
        })
        result = run_detections(low)
        assert "trust_below_threshold" in result

    def test_ungrounded_ai_claims(self):
        """AI claims without evidence trigger ungrounded detection."""
        ungrounded = json.dumps({
            "version": "1.1",
            "claims": [{
                "content": "Bold assertion",
                "confidence": 0.9,
                "ai_generated": True,
                "source": "unspecified",
            }],
        })
        result = run_detections(ungrounded)
        assert "ungrounded_ai_claims" in result


# ═══════════════════════════════════════════════════════════════════════════
# Cross-tab integration tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossTabIntegration:
    """Tests that verify consistency across tabs."""

    def test_stamp_json_roundtrips_to_detections(self):
        """JSON from Tab 1 can be pasted into Tab 3 for detection."""
        _, raw_json = stamp_and_inspect("AI generated claim", 0.7, "", "3", "", True)
        # Feed Tab 1 output into Tab 3
        result = run_detections(raw_json)
        assert "Detection Report" in result

    def test_stamp_and_trust_same_claim(self):
        """Tab 1 and Tab 2 produce consistent results for the same inputs."""
        content, conf, source, tier, model, ai = "Test claim", 0.85, "src", "2", "", True

        inspect_text, raw_json = stamp_and_inspect(content, conf, source, tier, model, ai)
        trust_result = trust_analysis(content, conf, source, tier, model, ai)

        # Both should reference the claim content
        data = json.loads(raw_json)
        assert data["claims"][0]["content"] == content
        assert content in trust_result

    def test_full_pipeline(self):
        """Stamp → Trust → Detect full pipeline works end to end."""
        content = "Quarterly earnings beat expectations by 15%"

        # Tab 1: Stamp
        inspect_text, raw_json = stamp_and_inspect(content, 0.92, "earnings-call", "1", "gpt-4o", True)
        data = json.loads(raw_json)
        assert data["claims"][0]["content"] == content
        assert data["claims"][0]["confidence"] == 0.92

        # Tab 2: Trust
        trust_result = trust_analysis(content, 0.92, "earnings-call", "1", "gpt-4o", True)
        assert "Effective trust" in trust_result

        # Tab 3: Detection (using Tab 1's JSON output)
        detection_result = run_detections(raw_json)
        assert "Detection Report" in detection_result

    def test_high_trust_claim_fewer_detections(self):
        """A well-crafted claim should trigger fewer detections than a sloppy one."""
        # Good claim
        _, good_json = stamp_and_inspect("Verified fact", 0.95, "lab-test", "1", "", False)
        good_report = run_detections(good_json)

        # Bad claim
        _, bad_json = stamp_and_inspect("Wild guess", 0.2, "", "5", "", True)
        bad_report = run_detections(bad_json)

        # Count triggered detections by counting warning icons
        good_triggered = good_report.count("\u26a0\ufe0f")
        bad_triggered = bad_report.count("\u26a0\ufe0f")
        assert bad_triggered >= good_triggered


# ═══════════════════════════════════════════════════════════════════════════
# Constants / module-level tests
# ═══════════════════════════════════════════════════════════════════════════

class TestModuleConstants:
    """Tests for module-level constants and structure."""

    def test_example_unit_is_valid_json(self):
        """EXAMPLE_UNIT constant is valid JSON."""
        data = json.loads(EXAMPLE_UNIT)
        assert isinstance(data, dict)

    def test_example_unit_has_claims(self):
        """EXAMPLE_UNIT has multiple claims for a good demo."""
        data = json.loads(EXAMPLE_UNIT)
        assert len(data["claims"]) >= 2

    def test_example_unit_has_version(self):
        """EXAMPLE_UNIT specifies a version."""
        data = json.loads(EXAMPLE_UNIT)
        assert "version" in data

    def test_example_unit_variety(self):
        """EXAMPLE_UNIT has claims with different confidence levels for demo value."""
        data = json.loads(EXAMPLE_UNIT)
        confidences = [c["confidence"] for c in data["claims"]]
        assert max(confidences) - min(confidences) >= 0.3  # Good spread
