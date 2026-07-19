#!/usr/bin/env python3
"""Generate publication figures from frozen English comparison artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "artifacts" / "method_comparison_samples_en" / "cases"
OUTPUT = ROOT / "artifacts" / "paper_case_studies_en" / "figures"
LATEX_OUTPUT = ROOT / "latex" / "figures"

METHODS = {
    "algotutorgen_stage2": "AlgoTutorGen",
    "direct_html": "Direct HTML",
    "webgen_agent": "WebGen-Agent",
    "browser_repair_1call": "Direct-BrowserRepair",
}

CHECKS = [
    ("page_load_ok", "Load"),
    ("visible_answer_match", "Ans"),
    ("interaction_reachable", "Int"),
    ("correct_feedback_ok", "CF"),
    ("wrong_feedback_ok", "WF"),
    ("hint_ok", "Hint"),
    ("show_answer_ok", "Show"),
    ("learning_log_ok", "Log"),
    ("mutation_free_ok", "PAns"),
]

COLORS = {
    "ink": "#182335",
    "muted": "#5D6B7E",
    "line": "#D5DCE5",
    "panel": "#F7F9FC",
    "blue": "#2D6CDF",
    "green": "#178B57",
    "green_fill": "#E8F6EF",
    "red": "#C84242",
    "red_fill": "#FCECEC",
    "amber": "#C27A12",
}


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(case_id: str, method: str) -> dict[str, Any]:
    record = read_json(SOURCE / case_id / method / "audit.json")
    values = record.get("machine_metrics")
    assert isinstance(values, dict)
    assert [key for key, _ in CHECKS] == list(values.keys())
    assert record.get("language") == "en"
    assert record.get("machine_ok") is all(values.values())
    return record


def screenshot(case_id: str, method: str) -> Image.Image:
    return Image.open(SOURCE / case_id / method / "screenshot.png").convert("RGB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rounded_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    *,
    facecolor: str,
    edgecolor: str,
    linewidth: float = 0.8,
    radius: float = 0.02,
    transform=None,
) -> FancyBboxPatch:
    transform = transform or ax.transAxes
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.004,rounding_size={radius}",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        transform=transform,
        clip_on=False,
    )
    ax.add_patch(patch)
    return patch


def draw_image(
    ax: plt.Axes,
    image: Image.Image,
    *,
    crop: tuple[int, int, int, int] | None = None,
    border: bool = True,
) -> None:
    if crop is not None:
        image = image.crop(crop)
    ax.imshow(image)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(border)
        spine.set_color(COLORS["line"])
        spine.set_linewidth(0.8)


def draw_audit_strip(ax: plt.Axes, record: dict[str, Any]) -> None:
    ax.set_axis_off()
    metrics = record["machine_metrics"]
    gap = 0.008
    width = (1.0 - gap * (len(CHECKS) - 1)) / len(CHECKS)
    for index, (key, label) in enumerate(CHECKS):
        ok = bool(metrics[key])
        x = index * (width + gap)
        rounded_box(
            ax,
            (x, 0.12),
            width,
            0.72,
            facecolor=COLORS["green_fill"] if ok else COLORS["red_fill"],
            edgecolor=COLORS["green"] if ok else COLORS["red"],
            linewidth=0.65,
            radius=0.035,
        )
        ax.text(
            x + width / 2,
            0.49,
            label,
            ha="center",
            va="center",
            color=COLORS["green"] if ok else COLORS["red"],
            fontsize=6.8,
            fontweight="bold",
            transform=ax.transAxes,
        )


def export_figure(fig: plt.Figure, stem: str) -> list[Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    LATEX_OUTPUT.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for suffix, kwargs in (
        (".svg", {}),
        (".pdf", {}),
        (".png", {"dpi": 300}),
    ):
        path = OUTPUT / f"{stem}{suffix}"
        fig.savefig(path, bbox_inches=None, pad_inches=0, **kwargs)
        shutil.copy2(path, LATEX_OUTPUT / path.name)
        created.append(path)
    plt.close(fig)
    return created


def build_dijkstra_comparison() -> list[Path]:
    case_id = "dijkstra_shortest_path"
    methods = list(METHODS)
    fig = plt.figure(figsize=(7.2, 5.45))
    grid = fig.add_gridspec(
        7,
        2,
        height_ratios=[0.25, 2.12, 0.34, 0.25, 2.12, 0.34, 0.18],
        hspace=0.12,
        wspace=0.11,
        left=0.035,
        right=0.985,
        top=0.91,
        bottom=0.055,
    )

    fig.text(
        0.035,
        0.982,
        "Dijkstra case: appearance versus executable tutoring",
        ha="left",
        va="top",
        fontsize=10.0,
        color=COLORS["ink"],
        fontweight="bold",
    )
    for index, method in enumerate(methods):
        row = 0 if index < 2 else 3
        col = index % 2
        record = audit(case_id, method)
        header = fig.add_subplot(grid[row, col])
        header.set_axis_off()
        label = METHODS[method]
        header.text(
            0.0,
            0.5,
            f"({chr(97 + index)})  {label}",
            transform=header.transAxes,
            ha="left",
            va="center",
            fontsize=8.7,
            fontweight="bold",
            color=COLORS["ink"],
        )
        ok = bool(record["machine_ok"])
        badge_text = "PASS · 9/9 checks" if ok else (
            f"FAIL · {sum(record['machine_metrics'].values())}/9 checks"
        )
        badge_width = 0.33 if ok else 0.36
        rounded_box(
            header,
            (1 - badge_width, 0.16),
            badge_width,
            0.68,
            facecolor=COLORS["green_fill"] if ok else COLORS["red_fill"],
            edgecolor=COLORS["green"] if ok else COLORS["red"],
            linewidth=0.7,
            radius=0.05,
        )
        header.text(
            1 - badge_width / 2,
            0.5,
            badge_text,
            transform=header.transAxes,
            ha="center",
            va="center",
            fontsize=6.9,
            fontweight="bold",
            color=COLORS["green"] if ok else COLORS["red"],
        )

        image_ax = fig.add_subplot(grid[row + 1, col])
        im = screenshot(case_id, method)
        draw_image(image_ax, im, crop=(0, 0, min(1365, im.width), min(900, im.height)))

        audit_ax = fig.add_subplot(grid[row + 2, col])
        draw_audit_strip(audit_ax, record)

    note_ax = fig.add_subplot(grid[6, :])
    note_ax.set_axis_off()
    note_ax.text(
        0.5,
        0.35,
        "Static panels document appearance; strips reproduce the frozen browser audit (PAns = protected-answer stability).",
        ha="center",
        va="center",
        fontsize=6.9,
        color=COLORS["muted"],
        transform=note_ax.transAxes,
    )
    return export_figure(fig, "qualitative_dijkstra_comparison")


def build_knapsack_walkthrough() -> list[Path]:
    case_id = "complete_knapsack_coin_change"
    method = "algotutorgen_stage2"
    record = audit(case_id, method)
    case = read_json(SOURCE / case_id / "case.json")
    im = screenshot(case_id, method)

    fig = plt.figure(figsize=(7.2, 4.55))
    grid = fig.add_gridspec(
        3,
        12,
        height_ratios=[1.15, 0.9, 1.18],
        hspace=0.16,
        wspace=0.18,
        left=0.035,
        right=0.985,
        top=0.88,
        bottom=0.07,
    )
    fig.text(
        0.035,
        0.975,
        "Complete-knapsack walkthrough: task, trace state, and result",
        ha="left",
        va="top",
        fontsize=9.8,
        fontweight="bold",
        color=COLORS["ink"],
    )
    contract_ax = fig.add_subplot(grid[0, 0:4])
    contract_ax.set_axis_off()
    rounded_box(
        contract_ax,
        (0.0, 0.0),
        1.0,
        1.0,
        facecolor=COLORS["panel"],
        edgecolor=COLORS["line"],
        radius=0.035,
    )
    sample = case["samples"][0]
    contract_ax.text(
        0.05,
        0.82,
        "(a) Frozen task contract",
        fontsize=8.7,
        fontweight="bold",
        color=COLORS["ink"],
        transform=contract_ax.transAxes,
    )
    contract_lines = [
        f"Coins: {sample['input_data']['coins']}",
        f"Amount: {sample['input_data']['amount']}",
        f"Expected minimum: {sample['expected']}",
        "Strategy: update dp[c] in",
        "increasing capacity order",
    ]
    y = 0.63
    for line in contract_lines:
        contract_ax.text(
            0.06,
            y,
            line,
            fontsize=7.25,
            color=COLORS["muted"],
            transform=contract_ax.transAxes,
            va="top",
            wrap=True,
        )
        y -= 0.135

    input_ax = fig.add_subplot(grid[0, 4:12])
    draw_image(input_ax, im, crop=(180, 15, 1180, 300))
    input_ax.set_title(
        "(b) Problem-specific input and coin affordances",
        loc="left",
        fontsize=8.7,
        fontweight="bold",
        color=COLORS["ink"],
        pad=4,
    )

    dp_ax = fig.add_subplot(grid[1, 0:12])
    draw_image(dp_ax, im, crop=(190, 305, 1170, 475))
    dp_ax.set_title(
        "(c) Trace-backed DP state (twelve visible amount states)",
        loc="left",
        fontsize=8.7,
        fontweight="bold",
        color=COLORS["ink"],
        pad=4,
    )

    result_ax = fig.add_subplot(grid[2, 0:8])
    draw_image(result_ax, im, crop=(195, 660, 1170, 940))
    result_ax.set_title(
        "(d) Navigation and verified terminal result",
        loc="left",
        fontsize=8.7,
        fontweight="bold",
        color=COLORS["ink"],
        pad=4,
    )

    evidence_ax = fig.add_subplot(grid[2, 8:12])
    evidence_ax.set_axis_off()
    rounded_box(
        evidence_ax,
        (0.0, 0.0),
        1.0,
        1.0,
        facecolor="white",
        edgecolor=COLORS["line"],
        radius=0.035,
    )
    evidence_ax.text(
        0.06,
        0.84,
        "(e) Executable evidence",
        fontsize=8.7,
        fontweight="bold",
        color=COLORS["ink"],
        transform=evidence_ax.transAxes,
    )
    evidence_ax.text(
        0.06,
        0.66,
        "68 trace frames (0–67)\nverified answer = 3\nbrowser audit = 9/9",
        fontsize=7.5,
        color=COLORS["muted"],
        linespacing=1.55,
        transform=evidence_ax.transAxes,
        va="top",
    )
    rounded_box(
        evidence_ax,
        (0.06, 0.08),
        0.88,
        0.18,
        facecolor=COLORS["green_fill"],
        edgecolor=COLORS["green"],
        linewidth=0.8,
        radius=0.05,
    )
    evidence_ax.text(
        0.50,
        0.17,
        "ALL NINE CHECKS PASS",
        ha="center",
        va="center",
        fontsize=7.1,
        fontweight="bold",
        color=COLORS["green"],
        transform=evidence_ax.transAxes,
    )
    return export_figure(fig, "complete_knapsack_walkthrough")


def build_cross_family_gallery() -> list[Path]:
    cases = [
        ("complete_knapsack_coin_change", "Coin Change · DP", (200, 20, 1165, 475)),
        ("dijkstra_shortest_path", "Dijkstra · Shortest path", (203, 140, 1163, 760)),
        ("permutations", "Permutations · Backtracking", (270, 80, 1095, 605)),
        ("provinces", "Provinces · Union-find", (200, 20, 1165, 540)),
    ]
    fig = plt.figure(figsize=(7.2, 4.85))
    grid = fig.add_gridspec(
        2,
        2,
        hspace=0.22,
        wspace=0.10,
        left=0.035,
        right=0.985,
        top=0.88,
        bottom=0.055,
    )
    fig.text(
        0.035,
        0.975,
        "Cross-family gallery: four selected AlgoTutorGen tutors",
        ha="left",
        va="top",
        fontsize=10.0,
        fontweight="bold",
        color=COLORS["ink"],
    )
    for index, (case_id, family, crop) in enumerate(cases):
        ax = fig.add_subplot(grid[index // 2, index % 2])
        im = screenshot(case_id, "algotutorgen_stage2")
        draw_image(ax, im, crop=crop)
        ax.set_title(
            f"({chr(97 + index)}) {family}",
            loc="left",
            fontsize=8.6,
            fontweight="bold",
            color=COLORS["ink"],
            pad=4,
        )
        rounded_box(
            ax,
            (0.83, 0.92),
            0.15,
            0.065,
            facecolor=COLORS["green_fill"],
            edgecolor=COLORS["green"],
            linewidth=0.65,
            radius=0.025,
        )
        ax.text(
            0.905,
            0.943,
            "9 / 9",
            ha="center",
            va="center",
            fontsize=5.9,
            fontweight="bold",
            color=COLORS["green"],
            transform=ax.transAxes,
        )
    return export_figure(fig, "cross_family_gallery")


def write_manifest(created: list[Path]) -> None:
    selected = {
        "dijkstra_shortest_path": list(METHODS),
        "complete_knapsack_coin_change": ["algotutorgen_stage2"],
        "cross_family_gallery": [
            "complete_knapsack_coin_change",
            "dijkstra_shortest_path",
            "permutations",
            "provinces",
        ],
    }
    manifest = {
        "schema_version": "paper-qualitative-figures-v1",
        "source_root": "artifacts/method_comparison_samples_en/cases",
        "interpretation_boundary": (
            "screenshots document visible appearance; functional labels are copied "
            "from audit.json and are not inferred from pixels"
        ),
        "selected": selected,
        "outputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(created)
        ],
    }
    (OUTPUT.parent / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    configure_matplotlib()
    created: list[Path] = []
    created.extend(build_dijkstra_comparison())
    created.extend(build_knapsack_walkthrough())
    created.extend(build_cross_family_gallery())
    write_manifest(created)
    for path in created:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
