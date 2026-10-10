"""Run the original (v0) and revised (v1) triage prompts through an open-source LLM.
Model: Qwen/Qwen2.5-1.5B-Instruct, greedy decoding, CPU, bfloat16."""
import json, re, sys, time, platform
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ENUMS = {
 "issue_category": {"water_management","energy_efficiency","waste_and_recycling","procurement_and_supplier","accessibility_and_inclusion","governance_and_conduct","health_and_safety","general_enquiry"},
 "urgency": {"LOW","MEDIUM","HIGH","CRITICAL"},
 "sentiment": {"POSITIVE","NEUTRAL","NEGATIVE"},
 "followup_required": {"Y","N"},
 "recommended_team": {"Facilities","Sustainability Office","Procurement","Accessibility and Inclusion Office","Governance and Compliance","WHS and Emergency","Helpdesk"},
 "data_sensitivity_risk": {"NONE","LOW","HIGH"},
 "human_review_required": {"Y","N"},
}
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16)
model.eval()

v0 = open("prompts/prompt_v0_original.txt").read()
v1_sys = open("prompts/prompt_v1_revised_system.txt").read()

def build(version, text):
    if version == "v0":
        msgs = [{"role": "user", "content": v0.replace("{message}", text)}]
    else:
        msgs = [{"role": "system", "content": v1_sys},
                {"role": "user", "content": f"<message>{text}</message>"}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

def generate(prompt):
    ids = tok(prompt, return_tensors="pt")
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=230, do_sample=False)
    dt = time.time() - t0
    return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True), dt

def parse(raw):
    s = raw.strip()
    fenced = s.startswith("```")
    extra_text = False
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return None, fenced, True, ["no JSON object found"]
    if m.group(0) != s:
        extra_text = True
    try:
        obj = json.loads(m.group(0))
    except Exception as e:
        return None, fenced, extra_text, [f"invalid JSON: {e}"]
    issues = []
    for k, allowed in ENUMS.items():
        if k not in obj: issues.append(f"missing {k}")
        elif obj[k] not in allowed: issues.append(f"{k} outside allowed values: {obj[k]!r}")
    return obj, fenced, extra_text, issues

jobs = []
for m in json.load(open("data/messages.json")):
    for v in ("v0", "v1"):
        jobs.append((v, m["id"], m["text"], "main"))
for b in json.load(open("data/bias_probe.json")):
    jobs.append(("v1", b["id"], b["text"], "bias"))

sel = sys.argv[1] if len(sys.argv) > 1 else "all"
with open("results/llm_runs.jsonl", "w") as f:
    for v, mid, text, kind in jobs:
        if sel != "all" and mid not in sel.split(","): continue
        raw, dt = generate(build(v, text))
        obj, fenced, extra, issues = parse(raw)
        rec = {"prompt_version": v, "id": mid, "set": kind, "text": text, "raw_output": raw,
               "parsed": obj, "markdown_fenced": fenced, "text_outside_json": extra,
               "schema_issues": issues, "seconds": round(dt, 1), "model": MODEL,
               "torch": torch.__version__, "platform": platform.platform()}
        f.write(json.dumps(rec) + "\n"); f.flush()
        print(v, mid, f"{dt:.0f}s", "OK" if obj and not issues else issues, flush=True)
