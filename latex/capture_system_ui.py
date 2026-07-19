"""Capture a publication figure from a verified AlgoTutorGen HTML artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Single-file AlgoTutorGen HTML artifact")
    parser.add_argument("--output", required=True, help="PNG output path")
    parser.add_argument("--step", type=int, default=8, help="Timeline step to display")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    output.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1720, "height": 1040},
            device_scale_factor=1.25,
        )
        page.goto(source.as_uri(), wait_until="load")
        page.wait_for_selector(".app")
        page.locator(f'.tick[data-step="{args.step}"]').click()
        page.wait_for_timeout(300)

        hint = page.get_by_role("button", name="提示", exact=True)
        if hint.count():
            hint.last.click()
            page.wait_for_timeout(200)

        page.evaluate(
            """
            () => {
              document.documentElement.style.background = '#ffffff';
              document.body.style.background = '#ffffff';
              const app = document.querySelector('.app');
              if (app) app.style.minHeight = '100vh';
            }
            """
        )
        page.screenshot(path=str(output), full_page=False, animations="disabled")
        browser.close()

    print(f"captured {source} -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
