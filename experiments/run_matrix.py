"""Run all 9 combinations (3 sample vendors x 3 RFQs) through the running API and write a report.

Usage (API must be running):  python experiments/run_matrix.py [base_url] [output_name]
  defaults: http://localhost:8000  matrix
Writes experiments/<output_name>.md. Makes 9 LLM calls (~$0.01 total with gpt-6-luna).
"""

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
OUT_NAME = sys.argv[2] if len(sys.argv) > 2 else "matrix"
VENDORS = ["a", "b", "c"]
RFQS = ["RFQ-001", "RFQ-002", "RFQ-003"]


def evaluate(vendor: str, rfq_id: str) -> dict:
    text = (ROOT / "data_warehouse" / "samples" / f"vendor-{vendor}.txt").read_text(encoding="utf-8")
    body = json.dumps({"rfq_id": rfq_id, "vendor_text": text}).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/evaluations", body, {"Content-Type": "application/json"})
    start = time.time()
    try:
        result = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        result = {"error": f"HTTP {e.code}: {e.read().decode()}"}
    result["seconds"] = round(time.time() - start, 1)
    return {"vendor": vendor.upper(), "rfq": rfq_id, **result}


def main() -> None:
    pairs = [(v, r) for v in VENDORS for r in RFQS]
    with ThreadPoolExecutor(max_workers=len(pairs)) as pool:
        results = list(pool.map(lambda p: evaluate(*p), pairs))

    lines = [f"# 3 x 3 evaluation matrix ({OUT_NAME})", ""]
    ok = [r for r in results if "error" not in r]
    if ok:
        lines += [f"Model `{ok[0]['model']}`, prompt `{ok[0]['prompt_version']}`.", ""]

    # Summary grid: score (raw) and gate
    lines += ["| Vendor | RFQ-001 | RFQ-002 | RFQ-003 |", "|---|---|---|---|"]
    for v in VENDORS:
        cells = []
        for rfq in RFQS:
            r = next(x for x in results if x["vendor"] == v.upper() and x["rfq"] == rfq)
            cells.append("ERROR" if "error" in r else
                         f"**{r['score']}** (raw {r['raw_score']}, gate {'✓' if r['gate_passed'] else '✗'})")
        lines.append(f"| {v.upper()} | " + " | ".join(cells) + " |")
    lines.append("")

    # Detail per combination
    for r in results:
        lines += [f"## Vendor {r['vendor']} x {r['rfq']}  ({r['seconds']}s)", ""]
        if "error" in r:
            lines += [r["error"], ""]
            continue
        tiers = ", ".join(f"{t} {s['points']}/{s['max']}" for t, s in r["breakdown"].items())
        lines += [f"Score **{r['score']}**, raw {r['raw_score']}, gate passed: {r['gate_passed']}. {tiers}", "",
                  "| Id | Requirement | Verdict | Evidence |", "|---|---|---|---|"]
        for c in r["criteria"]:
            verdict = c["verdict"] + (" ⚠ downgraded" if c["downgraded"] else "")
            evidence = c["evidence"].replace("|", "/").replace("\n", " ")
            lines.append(f"| {c['id']} | {c['text']} | {verdict} | {evidence} |")
        lines += ["", "Reasons:"] + [f"- ({f['criterion_id']}) {f['text']}" for f in r["reasons"]]
        lines += ["", "Gaps:"] + [f"- ({f['criterion_id']}) {f['text']}" for f in r["gaps"]] + [""]

    out = ROOT / "experiments" / f"{OUT_NAME}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:9]))
    print(f"\nFull report: {out}")


if __name__ == "__main__":
    main()
