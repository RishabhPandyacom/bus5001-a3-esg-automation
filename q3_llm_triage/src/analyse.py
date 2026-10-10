"""Compare LLM prompts v0/v1 with the rule-based and zero-shot baselines.

Reads results/llm_runs.jsonl and results/baseline_runs.jsonl and writes
results/analysis.md plus results/analysis.json.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["issue_category", "urgency", "followup_required", "recommended_team"]
URG_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

msgs = {m["id"]: m for m in json.load(open(ROOT / "data" / "messages.json"))}
llm = [json.loads(l) for l in open(ROOT / "results" / "llm_runs.jsonl")]
base = [json.loads(l) for l in open(ROOT / "results" / "baseline_runs.jsonl")]

systems = defaultdict(dict)  # system -> id -> predicted dict
for r in llm:
    systems["llm_" + r["prompt_version"]][r["id"]] = r["parsed"] or {}
for r in base:
    systems[r["method"]][r["id"]] = r

main_ids = list(msgs)
out = {}
lines = []

# 1. Schema validity and format discipline (LLM only)
lines.append("## 1. Output format discipline (LLM runs, 10 main messages)\n")
lines.append("| Prompt | Valid enum values | Markdown fenced | Text outside JSON | Missing human_review_required |")
lines.append("|---|---|---|---|---|")
for v in ("v0", "v1"):
    rows = [r for r in llm if r["prompt_version"] == v and r["set"] == "main"]
    valid = sum(1 for r in rows if not r["schema_issues"])
    fenced = sum(1 for r in rows if r["markdown_fenced"])
    outside = sum(1 for r in rows if r["text_outside_json"])
    missing = sum(1 for r in rows if any("missing" in s for s in r["schema_issues"]))
    n = len(rows)
    lines.append(f"| {v} | {valid}/{n} | {fenced}/{n} | {outside}/{n} | {missing}/{n} |")
    out[f"format_{v}"] = dict(valid=valid, fenced=fenced, outside=outside, missing=missing, n=n)

# 2. Accuracy against analyst reference labels
lines.append("\n## 2. Accuracy against analyst reference labels (10 main messages)\n")
lines.append("| System | issue_category | urgency | followup_required | recommended_team | urgency within one level |")
lines.append("|---|---|---|---|---|---|")
acc = {}
for s, preds in systems.items():
    cells = []
    acc[s] = {}
    for f in FIELDS:
        ok = n = 0
        for i in main_ids:
            p = preds.get(i, {}).get(f)
            if p is None:
                continue
            n += 1
            ok += p == msgs[i]["ref"][f]
        cells.append(f"{ok}/{len(main_ids)}")
        acc[s][f] = ok
    near = sum(
        1 for i in main_ids
        if preds.get(i, {}).get("urgency") in URG_ORDER
        and abs(URG_ORDER[preds[i]["urgency"]] - URG_ORDER[msgs[i]["ref"]["urgency"]]) <= 1
    )
    cells.append(f"{near}/{len(main_ids)}")
    acc[s]["urgency_within_one"] = near
    lines.append(f"| {s} | " + " | ".join(cells) + " |")
out["accuracy"] = acc

# 3. Per-message disagreements
lines.append("\n## 3. Per-message predictions (category / urgency)\n")
lines.append("| id | reference | llm_v1 | rule_based | zeroshot_bart_mnli |")
lines.append("|---|---|---|---|---|")
for i in main_ids:
    ref = msgs[i]["ref"]
    row = [i, f'{ref["issue_category"]} / {ref["urgency"]}']
    for s in ("llm_v1", "rule_based", "zeroshot_bart_mnli"):
        p = systems[s].get(i, {})
        row.append(f'{p.get("issue_category")} / {p.get("urgency")}')
    lines.append("| " + " | ".join(row) + " |")

# 4. Bias probe: urgency by reporter variant
probe = {p["id"]: p for p in json.load(open(ROOT / "data" / "bias_probe.json"))}
lines.append("\n## 4. Bias probe: urgency and category by reporter variant\n")
lines.append("| Probe | Variant | llm_v1 urgency | llm_v1 category | rule_based urgency | zeroshot urgency |")
lines.append("|---|---|---|---|---|---|")
bias = {}
for pid, p in probe.items():
    l = systems["llm_v1"].get(pid, {})
    rb = systems["rule_based"].get(pid, {})
    zs = systems["zeroshot_bart_mnli"].get(pid, {})
    lines.append(f'| {pid} | {p["variant"]} | {l.get("urgency")} | {l.get("issue_category")} | {rb.get("urgency")} | {zs.get("urgency")} |')
    bias[pid] = dict(variant=p["variant"], llm=l.get("urgency"), rule=rb.get("urgency"), zs=zs.get("urgency"))
out["bias"] = bias

for grp in ("b1", "b2"):
    for s, key in (("LLM v1", "llm"), ("rule-based", "rule"), ("zero-shot", "zs")):
        vals = {bias[k]["variant"]: bias[k][key] for k in bias if k.startswith(grp)}
        spread = len(set(vals.values()))
        out.setdefault("bias_spread", {})[f"{grp}_{key}"] = spread
lines.append("\nNumber of distinct urgency values across the four reporter variants of the same fact pattern (1 means fully consistent):\n")
lines.append("| Probe | LLM v1 | Rule-based | Zero-shot |")
lines.append("|---|---|---|---|")
for grp in ("b1", "b2"):
    lines.append(f'| {grp} | {out["bias_spread"][grp+"_llm"]} | {out["bias_spread"][grp+"_rule"]} | {out["bias_spread"][grp+"_zs"]} |')

# 5. Latency
lines.append("\n## 5. Latency (seconds per message, CPU only)\n")
for v in ("v0", "v1"):
    t = [r["seconds"] for r in llm if r["prompt_version"] == v]
    lines.append(f"- LLM {v}: mean {sum(t)/len(t):.1f} s")
    out[f"latency_{v}"] = round(sum(t) / len(t), 1)
zt = [r["seconds"] for r in base if r["method"] == "zeroshot_bart_mnli"]
lines.append(f"- Zero-shot bart-large-mnli: mean {sum(zt)/len(zt):.1f} s (two classification passes)")
lines.append("- Rule-based: under 1 ms")
out["latency_zs"] = round(sum(zt) / len(zt), 1)

(ROOT / "results" / "analysis.md").write_text("\n".join(lines) + "\n")
(ROOT / "results" / "analysis.json").write_text(json.dumps(out, indent=2))
print("\n".join(lines))
