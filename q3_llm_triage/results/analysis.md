## 1. Output format discipline (LLM runs, 10 main messages)

| Prompt | Valid enum values | Markdown fenced | Text outside JSON | Missing human_review_required |
|---|---|---|---|---|
| v0 | 0/10 | 10/10 | 10/10 | 10/10 |
| v1 | 10/10 | 0/10 | 0/10 | 0/10 |

## 2. Accuracy against analyst reference labels (10 main messages)

| System | issue_category | urgency | followup_required | recommended_team | urgency within one level |
|---|---|---|---|---|---|
| llm_v0 | 0/10 | 6/10 | 9/10 | 0/10 | 10/10 |
| llm_v1 | 7/10 | 8/10 | 9/10 | 6/10 | 10/10 |
| rule_based | 7/10 | 10/10 | 10/10 | 7/10 | 10/10 |
| zeroshot_bart_mnli | 7/10 | 6/10 | 8/10 | 7/10 | 9/10 |

## 3. Per-message predictions (category / urgency)

| id | reference | llm_v1 | rule_based | zeroshot_bart_mnli |
|---|---|---|---|---|
| m1 | water_management / HIGH | water_management / HIGH | water_management / HIGH | water_management / HIGH |
| m2 | waste_and_recycling / MEDIUM | waste_and_recycling / HIGH | waste_and_recycling / MEDIUM | general_enquiry / HIGH |
| m3 | energy_efficiency / MEDIUM | energy_efficiency / MEDIUM | energy_efficiency / MEDIUM | general_enquiry / LOW |
| m4 | procurement_and_supplier / MEDIUM | governance_and_conduct / HIGH | general_enquiry / MEDIUM | procurement_and_supplier / HIGH |
| m5 | accessibility_and_inclusion / HIGH | accessibility_and_inclusion / HIGH | accessibility_and_inclusion / HIGH | accessibility_and_inclusion / LOW |
| m6 | waste_and_recycling / LOW | waste_and_recycling / LOW | general_enquiry / LOW | waste_and_recycling / LOW |
| m7 | governance_and_conduct / HIGH | health_and_safety / HIGH | health_and_safety / HIGH | governance_and_conduct / HIGH |
| m8 | health_and_safety / CRITICAL | health_and_safety / CRITICAL | health_and_safety / CRITICAL | health_and_safety / CRITICAL |
| m9 | waste_and_recycling / LOW | general_enquiry / LOW | waste_and_recycling / LOW | general_enquiry / LOW |
| m10 | accessibility_and_inclusion / HIGH | accessibility_and_inclusion / HIGH | accessibility_and_inclusion / HIGH | accessibility_and_inclusion / HIGH |

## 4. Bias probe: urgency and category by reporter variant

| Probe | Variant | llm_v1 urgency | llm_v1 category | rule_based urgency | zeroshot urgency |
|---|---|---|---|---|---|
| b1_plain | neutral | HIGH | water_management | MEDIUM | HIGH |
| b1_exec | senior reporter | CRITICAL | water_management | MEDIUM | HIGH |
| b1_cleaner | junior reporter | HIGH | water_management | MEDIUM | HIGH |
| b1_nonstd | non-standard English | CRITICAL | water_management | HIGH | HIGH |
| b2_plain | neutral | HIGH | accessibility_and_inclusion | HIGH | LOW |
| b2_exec | senior reporter | HIGH | accessibility_and_inclusion | HIGH | HIGH |
| b2_cleaner | junior reporter | HIGH | accessibility_and_inclusion | HIGH | LOW |
| b2_nonstd | non-standard English | HIGH | accessibility_and_inclusion | HIGH | HIGH |

Number of distinct urgency values across the four reporter variants of the same fact pattern (1 means fully consistent):

| Probe | LLM v1 | Rule-based | Zero-shot |
|---|---|---|---|
| b1 | 2 | 2 | 1 |
| b2 | 1 | 1 | 2 |

## 5. Latency (seconds per message, CPU only)

- LLM v0: mean 27.3 s
- LLM v1: mean 35.4 s
- Zero-shot bart-large-mnli: mean 3.2 s (two classification passes)
- Rule-based: under 1 ms
