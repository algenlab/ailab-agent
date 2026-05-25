"""Single-file HTML runtime shell."""

from __future__ import annotations


def document_start(title: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>"""


def document_end() -> str:
    return """</body>
</html>"""
