#!/usr/bin/env python3
"""Frontend wiring verifier.

Checks:
1) Internal navigation targets from Link href / router.push exist in app routes.
2) Button action heuristic: button has onClick or submit semantics.

Exit codes:
  0 = no missing routes (warnings may still be present)
  1 = missing routes detected
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "frontend" / "app"

LINK_HREF_RE = re.compile(r"<Link[^>]*\shref\s*=\s*[\"'](/[^\"'#?]+)")
ROUTER_PUSH_RE = re.compile(r"router\.push\(\s*[\"'](/[^\"']+)[\"']\s*\)")
BUTTON_RE = re.compile(r"<button\b([^>]*)>", re.IGNORECASE)


@dataclass(frozen=True)
class RouteRef:
    source_file: str
    target: str
    kind: str


@dataclass(frozen=True)
class ButtonWarning:
    source_file: str
    snippet: str


def normalize_route(route: str) -> str:
    route = route.split("?", 1)[0].split("#", 1)[0]
    if route == "":
        route = "/"
    if not route.startswith("/"):
        route = f"/{route}"
    if route != "/":
        route = route.rstrip("/")
    return route


def collect_page_routes() -> list[str]:
    routes: list[str] = []
    for page in APP_DIR.rglob("page.tsx"):
        rel = page.relative_to(APP_DIR)
        raw = "/" + str(rel).replace("/page.tsx", "").replace("page.tsx", "")
        routes.append(normalize_route(raw if raw else "/"))
    return sorted(set(routes))


def route_pattern_to_regex(route: str) -> re.Pattern[str]:
    pattern = re.escape(route)
    # dynamic segments: [id] or [...slug]
    pattern = pattern.replace(re.escape("[..."), "[...")
    pattern = re.sub(r"\\\[\.\.\.([^\]]+)\\\]", r"(?P<\1>.+)", pattern)
    pattern = re.sub(r"\\\[([^\]]+)\\\]", r"(?P<\1>[^/]+)", pattern)
    return re.compile(rf"^{pattern}$")


def route_exists(target: str, all_routes: list[str]) -> bool:
    target = normalize_route(target)
    if target in all_routes:
        return True
    for route in all_routes:
        if "[" in route and "]" in route and route_pattern_to_regex(route).match(target):
            return True
    return False


def collect_navigation_refs() -> list[RouteRef]:
    refs: list[RouteRef] = []
    for file_path in APP_DIR.rglob("*.tsx"):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        rel = str(file_path.relative_to(ROOT))

        for m in LINK_HREF_RE.finditer(text):
            refs.append(RouteRef(source_file=rel, target=normalize_route(m.group(1)), kind="Link.href"))

        for m in ROUTER_PUSH_RE.finditer(text):
            refs.append(RouteRef(source_file=rel, target=normalize_route(m.group(1)), kind="router.push"))

    return refs


def collect_button_warnings() -> list[ButtonWarning]:
    warnings: list[ButtonWarning] = []
    for file_path in APP_DIR.rglob("*.tsx"):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        rel = str(file_path.relative_to(ROOT))

        for m in BUTTON_RE.finditer(text):
            attrs = m.group(1)
            has_onclick = "onClick=" in attrs
            has_submit = re.search(r"\btype\s*=\s*[\"']submit[\"']", attrs) is not None
            has_disabled = re.search(r"\bdisabled\b", attrs) is not None
            if not has_onclick and not has_submit and not has_disabled:
                snippet = "<button" + attrs + ">"
                warnings.append(ButtonWarning(source_file=rel, snippet=snippet[:180]))
    return warnings


def main() -> int:
    routes = collect_page_routes()
    refs = collect_navigation_refs()

    missing: list[dict[str, str]] = []
    for ref in refs:
        if not route_exists(ref.target, routes):
            missing.append(
                {
                    "source_file": ref.source_file,
                    "target": ref.target,
                    "kind": ref.kind,
                }
            )

    button_warnings = collect_button_warnings()

    output = {
        "total_routes": len(routes),
        "total_navigation_refs": len(refs),
        "missing_navigation_targets": len(missing),
        "missing_navigation_items": missing[:300],
        "button_warnings": len(button_warnings),
        "button_warning_items": [
            {"source_file": item.source_file, "snippet": item.snippet}
            for item in button_warnings[:300]
        ],
    }

    print(json.dumps(output, indent=2))

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
