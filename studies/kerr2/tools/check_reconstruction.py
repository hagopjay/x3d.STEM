"""Eyes witness for the Loom: every case has a passing browser-vs-offline reconstruction that still
describes the current case manifest, with its signal floor and flipped negative control.
Exit 0 pass, 1 fail. Run: python3 -E -s tools/check_reconstruction.py"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows, ok = [], True
for case in sorted(p.parent.name for p in (ROOT / "cases").glob("*/case.json")):
    f = ROOT / "evidence" / f"reconstruction-{case}.json"
    if not f.is_file():
        rows.append({"case": case, "problem": "missing"}); ok = False; continue
    r = json.loads(f.read_text())
    fresh = r["case_manifest_sha256"] == hashlib.sha256((ROOT / "cases" / case / "case.json").read_bytes()).hexdigest()
    ids = " ".join(w["id"] for w in r["witnesses"])
    complete = "signal" in ids and "negative control" in ids and r["view"].get("view") == 0
    # the capture must describe the page that ships: every page source hash recorded at capture time must still match
    srcs = r["view"].get("page_sources") or {}
    fresh = fresh and bool(srcs) and all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == d for p, d in srcs.items())
    good = r["pass"] and fresh and complete and all(w["pass"] for w in r["witnesses"])
    # evidence/ is outside the Loom candidate (excluded by name): pin the judged bytes in the witness output
    rows.append({"case": case, "pass": r["pass"], "fresh": fresh, "controls": complete,
                 "evidence_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                 "offline_png_sha256": hashlib.sha256((ROOT / "evidence" / f"reconstruction-{case}-offline.png").read_bytes()).hexdigest()})
    ok &= good
print(json.dumps(rows))
sys.exit(0 if ok else 1)
