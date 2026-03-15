"""Business logic for the AKF Gradio Space — no Gradio dependency."""

import json
import akf


# ── Tab 1: Stamp & Inspect ──────────────────────────────────────────────────

def stamp_and_inspect(content, confidence, source, tier, model, ai_generated):
    if not content.strip():
        return "Please enter a claim.", "{}"

    kwargs = dict(
        content=content.strip(),
        confidence=confidence,
        ai_generated=ai_generated,
    )
    if source.strip():
        kwargs["source"] = source.strip()
    if model.strip():
        kwargs["model"] = model.strip()

    unit = akf.stamp(**kwargs)
    # Override authority tier on the claim
    unit.claims[0].authority_tier = int(tier)

    inspect_text = unit.inspect()
    raw_json = json.dumps(unit.to_dict(compact=False), indent=2)
    return inspect_text, raw_json


# ── Tab 2: Trust Analysis ───────────────────────────────────────────────────

def trust_analysis(content, confidence, source, tier, model, ai_generated):
    if not content.strip():
        return "Please enter a claim."

    kwargs = dict(
        content=content.strip(),
        confidence=confidence,
        ai_generated=ai_generated,
    )
    if source.strip():
        kwargs["source"] = source.strip()
    if model.strip():
        kwargs["model"] = model.strip()

    unit = akf.stamp(**kwargs)
    unit.claims[0].authority_tier = int(tier)

    return akf.explain_trust(unit.claims[0])


# ── Tab 3: Security Detections ──────────────────────────────────────────────

EXAMPLE_UNIT = json.dumps(
    {
        "version": "1.1",
        "claims": [
            {
                "content": "Revenue will reach $50B next quarter",
                "confidence": 0.95,
                "authority_tier": 1,
                "ai_generated": True,
                "source": "unspecified",
            },
            {
                "content": "Market conditions are favorable",
                "confidence": 0.3,
                "authority_tier": 5,
                "ai_generated": True,
                "source": "unspecified",
            },
        ],
        "classification": "public",
    },
    indent=2,
)


def run_detections(json_text):
    if not json_text.strip():
        return "Please paste an AKF JSON unit."

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    try:
        unit = akf.loads(json.dumps(data))
    except Exception as e:
        return f"Could not parse AKF unit: {e}"

    report = akf.run_all_detections(unit)

    lines = []
    lines.append(f"Detection Report  —  {report.triggered_count} triggered "
                 f"({report.critical_count} critical, {report.high_count} high)")
    lines.append("=" * 60)

    for r in report.results:
        icon = "\u26a0\ufe0f" if r.triggered else "\u2705"
        lines.append(f"\n{icon}  {r.detection_class}  [{r.severity}]")
        if r.triggered:
            for f in r.findings:
                lines.append(f"   - {f}")
            lines.append(f"   Recommendation: {r.recommendation}")

    if report.clean:
        lines.append("\nAll clear — no detections triggered.")

    return "\n".join(lines)
