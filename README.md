# BUS5001 Assessment 3 - ESG automation experiments

Author: Rishabh Jayesh Pandya

This repository holds the supporting evidence for the written report.

| Folder | Content |
|---|---|
| q1_dialogflow | Dialogflow CX agent export (esg_agent_restore.zip), simulator screenshots and the demo script |
| q2_snowflake | Source of the incident and shared-responsibility diagram (Graphviz) and the rendered image |
| q3_llm_triage | Prompts, messages, bias probe, scripts, raw model outputs, baseline outputs and analysis tables |
| q4_notebooklm | NotebookLM (Gemini Notebook) screenshots and the experiment log |
| report | Script that builds the Word report, and the report itself |

AI tools: Claude (Anthropic) was used as an assistant under my direction. See the AI Acknowledgement section of the report.

## Q1 - restore the agent
In the Conversational Agents console, open Agent settings, choose Restore agent, select Upload and pick `q1_dialogflow/esg_agent_restore.zip`. Then open the simulator and follow `q1_dialogflow/demo_script.md`.

## Q3 - reproduce the experiments
```
pip install torch transformers accelerate
python3 q3_llm_triage/src/run_llm.py all        # 28 LLM runs (about 30 s each on CPU)
python3 q3_llm_triage/src/run_baselines.py all  # rule-based and bart-large-mnli
python3 q3_llm_triage/src/analyse.py            # writes results/analysis.md and analysis.json
```
Model: Qwen/Qwen2.5-1.5B-Instruct, bf16, CPU, greedy decoding. Reference labels were assigned by the analyst. The rule-based keywords were written with the sample messages in view, so its scores are optimistic. Each probe variant was run once.

## Q4
`q4_notebooklm/experiment_log.md` lists each prompt, each generated item and the checks made against the sources.
