"""Write docs/NUMBERS.md from the case manifests and the reconstruction evidence (never retyped)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / "lib"))
from stemkit.docs import _num, numbers   # noqa: E402

CASES = ["schwarzschild", "kerr", "extreme"]
md = numbers([ROOT / "cases" / c / "case.json" for c in CASES], "Kerr 2 · witness numbers")
md += "## Browser frame vs offline render (reconstruction witness)\n\n"
md += "| Case | View (deep link) | Signal (std) | Correlation | Mean abs. difference (8-bit) | Flipped control | Pass |\n|---|---|---|---|---|---|---|\n"
for c in CASES:
    r = json.loads((ROOT / "evidence" / f"reconstruction-{c}.json").read_text())
    w = {x["id"].split(":")[0].split(",")[0]: x["observed"] for x in r["witnesses"]}
    obs = [x["observed"] for x in r["witnesses"]]
    md += f"| {c} | `#{r['view'].get('hash', '')}` | {_num(obs[0])} | {obs[1]:.7f} | {_num(obs[2])} | {_num(obs[3])} | {'✓' if r['pass'] else '✗'} |\n"
md += f"\nRenderer: {json.loads((ROOT / 'evidence' / 'reconstruction-extreme.json').read_text())['view'].get('renderer', 'unknown')}; Playwright headless Chromium.\n"
(ROOT / "docs" / "NUMBERS.md").write_text(md)
print("docs/NUMBERS.md")
