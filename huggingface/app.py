"""AKF Gradio Space — try Agent Knowledge Format without installing anything."""

from logic import stamp_and_inspect, trust_analysis, run_detections, EXAMPLE_UNIT


# ── Build the UI ─────────────────────────────────────────────────────────────

def build_app():
    import gradio as gr

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

        # ── Tab 1 ────────────────────────────────────────────────────────
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

        # ── Tab 2 ────────────────────────────────────────────────────────
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

        # ── Tab 3 ────────────────────────────────────────────────────────
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

    return demo


demo = build_app()

if __name__ == "__main__":
    demo.launch()
