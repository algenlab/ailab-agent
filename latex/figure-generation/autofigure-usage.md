# AutoFigure-Edit Local Usage Notes

## Repository

- URL: `https://github.com/ResearAI/AutoFigure-Edit`
- Local path: `/ssd1/liaokunpeng/paper/AutoFigure-Edit`
- Inspected revision: `a14889f82b9ed1376b848d8e8eaaf6bca6077033`
- Main entry point: `autofigure2.py`

## Documented Workflows

Text or method section to a complete editable figure pipeline:

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 autofigure2.py \
  --method_file paper.txt \
  --output_dir outputs/demo \
  --provider custom \
  --base_url https://provider.example/v1 \
  --api_key YOUR_KEY \
  --image_provider openai \
  --image_base_url https://provider.example/v1 \
  --image_api_key YOUR_KEY \
  --image_model gpt-image-2
```

Existing stage-1 raster to SAM/SVG reconstruction:

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 autofigure2.py \
  --input_figure_path ./figure.png \
  --output_dir outputs/import-demo \
  --provider custom \
  --base_url https://provider.example/v1 \
  --api_key YOUR_KEY \
  --svg_model gpt-5.5 \
  --optimize_iterations 0
```

The complete import workflow requires a working SAM3 backend and the RMBG dependencies. AutoFigure-Edit supports local SAM3, fal.ai, and Roboflow routes.

## Route Used for This Paper

This task needs three publication raster figures and the current machine has the stage-1 dependencies (`Pillow`, `openai`, and `requests`) but no installed `sam3` package, `HF_TOKEN`, `FAL_KEY`, or `ROBOFLOW_API_KEY`. The task therefore invokes AutoFigure-Edit's native `generate_figure_from_method(...)` function directly:

- provider: `openai` when the configured endpoint exposes `/images/generations` and `/images/edits`;
- model: `gpt-image-2`;
- project base URL and API key: loaded internally from `../ailab-agent/api_settings.json` without printing the credential;
- size: `1536x1024`, followed by AutoFigure-Edit's aspect-ratio-preserving 4K upscale;
- Figures 1 and 2: existing PNGs are reference images;
- Figure 3: the selected redesigned figure is the shared style reference.

Calling the stage-1 function is deliberate: it uses the repository's own OpenAI Images implementation for generation and reference-image editing while avoiding an unrelated failure in the optional SAM/SVG half of the pipeline.

## Expected Artifacts

- stage 1: `figure.png` or the requested output filename;
- full optional pipeline: `samed.png`, `boxlib.json`, `template.svg`, `optimized_template.svg`, `final.svg`, and extracted icon assets.

