"""Bind a browser run's raw result (JSON on stdin, from the page's cloudView()) to the files it ran
against, and write evidence/browser-<date>.json for tools/check_browser.py and the Loom."""
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
h = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
r = json.loads(sys.stdin.read())
s = r["playback"]["samples"]
ev = {"schema": "electron-cloud.browser/1", "date": datetime.date.today().isoformat(), "browser": "Playwright MCP headless Chromium",
      "renderer": r["renderer"], "user_agent": r["ua"],
      "page_sources": {p: h(p) for p in ["index.html", "src/app.js", "src/nets.js", "src/app.css", "scenes/cloud.x3d"]},
      "case_manifests": {c: h(f"cases/{c}/case.json") for c in r["cases"]},
      "mesh_cross_check": {"what": "the page rebuilds every frame's mesh from the verified field (src/nets.js) and compares vertex and triangle counts (exact) and enclosed volume (relative, at most 1e-6) with the builder's reference at level 0.2",
                           "cases": r["cases"], "pass": all(c["status"] == "pass" and c["match"] == c["total"] for c in r["cases"].values())},
      "playback": {"what": "Play from frame 0; sample the page's frame and the Switch whichChoice and the charge bead every 0.6 s; pause and check it holds",
                   "samples_frame_whichChoice": s, "paused_then": r["playback"]["paused_then"],
                   "pass": all(x[0] == x[1] for x in s) and all(s[i + 1][0] > s[i][0] for i in range(len(s) - 1))
                           and len({x[2] for x in s}) == len(s) and r["playback"]["paused_then"][0] == r["playback"]["paused_then"][1]},
      "console_errors": r["errors"],
      "scope": "One browser on one machine. Counts and volumes, not pixels: no frame is compared with an offline render, and no frame rate is claimed."}
ev["pass"] = ev["mesh_cross_check"]["pass"] and ev["playback"]["pass"] and not r["errors"]
out = ROOT / "evidence" / f"browser-{ev['date']}.json"
out.write_text(json.dumps(ev, indent=2) + "\n")
print(out.name, "pass" if ev["pass"] else "FAIL")
sys.exit(0 if ev["pass"] else 1)
