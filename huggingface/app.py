"""AKF Gradio Space — try Agent Knowledge Format without installing anything."""

import json
import gradio as gr
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


# ── Build the UI ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "**Agent Knowledge Format** — EXIF for AI. "
    "Stamp claims with trust metadata, analyze trust scores, "
    "and run security detections. "
    "[GitHub](https://github.com/HMAKT99/AKF) · "
    "[PyPI](https://pypi.org/project/akf/) · "
    "[npm](https://www.npmjs.com/package/akf-format)"
)

with gr.Blocks(title="AKF — Agent Knowledge Format", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# AKF — Agent Knowledge Format")
    gr.Markdown(DESCRIPTION)

    # ── Tab 1 ────────────────────────────────────────────────────────────
    with gr.Tab("Stamp & Inspect"):
        with gr.Row():
            with gr.Column():
                t1_content = gr.Textbox(
                    label="Claim",
                    placeholder="e.g. Revenue projected at $42.1B",
                    lines=3,
                )
                t1_confidence = gr.Slider(0, 1, value=0.85, step=0.01, label="Confidence")
                t1_source = gr.Textbox(label="Source", placeholder="e.g. financial-erp")
                t1_tier = gr.Dropdown(
                    choices=["1", "2", "3", "4", "5"],
                    value="3",
                    label="Authority Tier (1 = expert, 5 = speculative)",
                )
                t1_model = gr.Textbox(label="Model", placeholder="e.g. gpt-4o")
                t1_ai = gr.Checkbox(label="AI-generated", value=True)
                t1_btn = gr.Button("Stamp", variant="primary")
            with gr.Column():
                t1_inspect = gr.Textbox(label="Inspect Output", lines=12, interactive=False)
                t1_json = gr.Code(label="Raw JSON", language="json")

        t1_btn.click(
            stamp_and_inspect,
            inputs=[t1_content, t1_confidence, t1_source, t1_tier, t1_model, t1_ai],
            outputs=[t1_inspect, t1_json],
        )

    # ── Tab 2 ────────────────────────────────────────────────────────────
    with gr.Tab("Trust Analysis"):
        with gr.Row():
            with gr.Column():
                t2_content = gr.Textbox(
                    label="Claim",
                    placeholder="e.g. Revenue projected at $42.1B",
                    lines=3,
                )
                t2_confidence = gr.Slider(0, 1, value=0.85, step=0.01, label="Confidence")
                t2_source = gr.Textbox(label="Source", placeholder="e.g. financial-erp")
                t2_tier = gr.Dropdown(
                    choices=["1", "2", "3", "4", "5"],
                    value="3",
                    label="Authority Tier (1 = expert, 5 = speculative)",
                )
                t2_model = gr.Textbox(label="Model", placeholder="e.g. gpt-4o")
                t2_ai = gr.Checkbox(label="AI-generated", value=True)
                t2_btn = gr.Button("Analyze Trust", variant="primary")
            with gr.Column():
                t2_output = gr.Textbox(label="Trust Breakdown", lines=16, interactive=False)

        t2_btn.click(
            trust_analysis,
            inputs=[t2_content, t2_confidence, t2_source, t2_tier, t2_model, t2_ai],
            outputs=[t2_output],
        )

    # ── Tab 3 ────────────────────────────────────────────────────────────
    with gr.Tab("Security Detections"):
        with gr.Row():
            with gr.Column():
                t3_json_input = gr.Code(
                    label="AKF Unit (JSON)",
                    language="json",
                    value=EXAMPLE_UNIT,
                    lines=18,
                )
                t3_btn = gr.Button("Run Detections", variant="primary")
            with gr.Column():
                t3_output = gr.Textbox(label="Detection Report", lines=24, interactive=False)

        t3_btn.click(run_detections, inputs=[t3_json_input], outputs=[t3_output])

if __name__ == "__main__":
    demo.launch()
