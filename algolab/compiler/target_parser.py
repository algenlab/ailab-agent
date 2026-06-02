"""Parse semantic target strings."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedTarget:
    raw: str
    kind: str
    name: str
    indices: tuple[int, ...] = ()
    source: str = ""
    target: str = ""


INDEX_RE = re.compile(r"^([A-Za-z_][\w]*)\[(\d+)\](?:\[(\d+)\])?$")
SLICE_RE = re.compile(r"^([A-Za-z_][\w]*)\[(\d+):(\d+)\]$")
MAP_BRACKET_RE = re.compile(r"^([A-Za-z_][\w]*)\[([^\[\]:]+)\]$")


def parse_target(raw: str) -> ParsedTarget:
    raw = str(raw).strip()
    m = INDEX_RE.match(raw)
    if m:
        indices = tuple(int(x) for x in m.groups()[1:] if x is not None)
        return ParsedTarget(raw=raw, kind="indexed", name=m.group(1), indices=indices)
    m = SLICE_RE.match(raw)
    if m:
        return ParsedTarget(raw=raw, kind="slice", name=m.group(1), indices=(int(m.group(2)), int(m.group(3))))
    m = MAP_BRACKET_RE.match(raw)
    if m and not m.group(2).isdigit():
        return ParsedTarget(raw=raw, kind="map", name=f"{m.group(1)}:{m.group(2)}")

    if raw.startswith("node:"):
        return ParsedTarget(raw=raw, kind="node", name=raw.split(":", 1)[1])
    if raw.startswith("edge:"):
        edge = raw.split(":", 1)[1]
        if "->" in edge:
            src, dst = edge.split("->", 1)
            return ParsedTarget(raw=raw, kind="edge", name=edge, source=src, target=dst)
        if "-" in edge:
            src, dst = edge.split("-", 1)
            if src and dst:
                return ParsedTarget(raw=raw, kind="edge", name=edge, source=src, target=dst)
        return ParsedTarget(raw=raw, kind="edge", name=edge)
    if raw.startswith("pointer:"):
        return ParsedTarget(raw=raw, kind="pointer", name=raw.split(":", 1)[1])
    if raw.startswith("frame:"):
        return ParsedTarget(raw=raw, kind="frame", name=raw.split(":", 1)[1])
    if raw.startswith("point:"):
        return ParsedTarget(raw=raw, kind="point", name=raw.split(":", 1)[1])
    if raw.startswith("char:"):
        return ParsedTarget(raw=raw, kind="char", name=raw.split(":", 1)[1])
    if raw in {"stack", "queue", "deque", "heap", "tree", "trie", "frames", "points", "string"}:
        return ParsedTarget(raw=raw, kind="container", name=raw)
    return ParsedTarget(raw=raw, kind="symbol", name=raw)
