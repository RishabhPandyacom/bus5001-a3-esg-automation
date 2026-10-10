"""Baselines for the ESG triage task.

1. Rule-based keyword baseline (deterministic, no model).
2. Zero-shot baseline using facebook/bart-large-mnli (Hugging Face).

Both write results/baseline_runs.jsonl with the same label fields as the LLM runs
so they can be compared in src/analyse.py.
"""
import json
import platform
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATS = [
    "water_management", "energy_efficiency", "waste_and_recycling",
    "procurement_and_supplier", "accessibility_and_inclusion",
    "governance_and_conduct", "health_and_safety", "general_enquiry",
]
TEAM_FOR = {
    "water_management": "Facilities",
    "energy_efficiency": "Facilities",
    "waste_and_recycling": "Sustainability Office",
    "procurement_and_supplier": "Procurement",
    "accessibility_and_inclusion": "Accessibility and Inclusion Office",
    "governance_and_conduct": "Governance and Compliance",
    "health_and_safety": "WHS and Emergency",
    "general_enquiry": "Helpdesk",
}

# Ordered rules. The first matching category wins, so safety comes first.
CAT_RULES = [
    ("health_and_safety", r"\b(gas|fire|smoke|spill|injur|chemical|asbestos|fume|explosion)\b"),
    ("accessibility_and_inclusion", r"\b(wheelchair|accessib|ramp|lift|elevator|disabilit)\w*"),
    ("governance_and_conduct", r"\b(ignore the .*rules|bribe|harass|fraud|whistle|retaliat|misconduct|scared to report)\b"),
    ("procurement_and_supplier", r"\b(supplier|vendor|procure|contractor)\b"),
    ("water_management", r"\b(water|leak|tap|pipe|flood|sewage|drain)\b"),
    ("energy_efficiency", r"\b(air conditioning|aircon|lights?|energy|power|heating|electricity)\b"),
    ("waste_and_recycling", r"\b(bin|bins|recycl|compost|waste|rubbish|cups?)\b"),
]
CRITICAL_RE = r"\b(gas|fire|smoke|explosion|injur\w*|spill)\b"
HIGH_RE = r"\b(blocked|out of service|cannot|can't|leak|running all|scared|ignore)\b"
LOW_RE = r"\b(thanks|brilliant|great|can someone explain|which bin|how do i)\b"
NEG_RE = r"\b(blocked|leak|contaminated|not meet|scared|cannot|out of service|ignore|smell)\b"
POS_RE = r"\b(thanks|brilliant|great|love|well done)\b"


def rule_based(text: str) -> dict:
    t = text.lower()
    cat = "general_enquiry"
    for name, pat in CAT_RULES:
        if re.search(pat, t):
            cat = name
            break
    if re.search(CRITICAL_RE, t):
        urg = "CRITICAL"
    elif re.search(LOW_RE, t):
        urg = "LOW"
    elif re.search(HIGH_RE, t):
        urg = "HIGH"
    else:
        urg = "MEDIUM"
    if re.search(POS_RE, t):
        sent = "POSITIVE"
    elif re.search(NEG_RE, t):
        sent = "NEGATIVE"
    else:
        sent = "NEUTRAL"
    return {
        "issue_category": cat,
        "urgency": urg,
        "sentiment": sent,
        "followup_required": "N" if urg == "LOW" else "Y",
        "recommended_team": TEAM_FOR[cat],
    }


ZS_LABELS = {
    "water_management": "a water leak, tap, pipe or flooding problem",
    "energy_efficiency": "wasted energy, lighting, heating or air conditioning",
    "waste_and_recycling": "waste, recycling, composting or bins",
    "procurement_and_supplier": "a supplier or procurement concern",
    "accessibility_and_inclusion": "accessibility, disability access or inclusion",
    "governance_and_conduct": "misconduct, ethics or rule-breaking by a manager",
    "health_and_safety": "a health and safety hazard such as gas, fire or chemicals",
    "general_enquiry": "a general question",
}
ZS_URG = {
    "CRITICAL": "an immediate danger to life or safety",
    "HIGH": "an ongoing problem that needs action today",
    "MEDIUM": "a problem that can be fixed within a few days",
    "LOW": "a compliment or a simple question",
}


def zero_shot(items):
    from transformers import pipeline
    import torch
    clf = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
    out = []
    cat_keys = list(ZS_LABELS)
    urg_keys = list(ZS_URG)
    for it in items:
        t0 = time.time()
        r1 = clf(it["text"], [ZS_LABELS[k] for k in cat_keys], hypothesis_template="This message is about {}.")
        cat = cat_keys[[ZS_LABELS[k] for k in cat_keys].index(r1["labels"][0])]
        r2 = clf(it["text"], [ZS_URG[k] for k in urg_keys], hypothesis_template="This message reports {}.")
        urg = urg_keys[[ZS_URG[k] for k in urg_keys].index(r2["labels"][0])]
        out.append({
            "id": it["id"],
            "method": "zeroshot_bart_mnli",
            "issue_category": cat,
            "urgency": urg,
            "followup_required": "N" if urg == "LOW" else "Y",
            "recommended_team": TEAM_FOR[cat],
            "cat_score": round(r1["scores"][0], 3),
            "urg_score": round(r2["scores"][0], 3),
            "seconds": round(time.time() - t0, 2),
            "torch": torch.__version__,
            "platform": platform.platform(),
        })
        print(it["id"], cat, urg, out[-1]["cat_score"], out[-1]["urg_score"], flush=True)
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    msgs = json.load(open(ROOT / "data" / "messages.json"))
    probe = json.load(open(ROOT / "data" / "bias_probe.json"))
    items = [{"id": m["id"], "text": m["text"]} for m in msgs]
    items += [{"id": p["id"], "text": p["text"]} for p in probe]
    out_path = ROOT / "results" / "baseline_runs.jsonl"
    rows = []
    if which in ("rules", "all"):
        for it in items:
            r = rule_based(it["text"])
            r.update({"id": it["id"], "method": "rule_based"})
            rows.append(r)
    if which in ("zeroshot", "all"):
        rows += zero_shot(items)
    mode = "a" if which == "zeroshot" and out_path.exists() else "w"
    with open(out_path, mode) as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("wrote", len(rows), "rows to", out_path)


if __name__ == "__main__":
    main()
