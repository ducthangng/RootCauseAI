from .node_types import AgentState, log
from src.data_processing.guardrails import sanitize_urls
import re

def action_node(state: AgentState) -> dict:
    log("action", state)

    cited_ids = set(re.findall(r"\[(\d+)\]", state["draft_report"]))
    cited_docs = [d for d in state["retrieved_docs"] if str(d["id"]) in cited_ids]

    references = chr(10).join(
        f"- [{d['id']}] ODI #{d['odino']} | {d['mfr_name']} {d['modeltxt']} | {d['compdesc'] or 'N/A'} (score={d['score']:.2f})"
        for d in cited_docs
    )

    final_report = f"""# Root Cause Analysis Report

## Sự cố
{sanitize_urls(state['incident_text'])}

## Phân tích
{sanitize_urls(state['draft_report'])}

## Số lần sửa
{state['revision_count']}

## Nguồn tham khảo
{sanitize_urls(references)}
"""
    print("    -> đã render report markdown")
    return {"report": final_report}