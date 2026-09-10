from .node_types import AgentState, log

def action_node(state: AgentState) -> dict:
    log("action", state)

    references = chr(10).join(
        f"- [{d['id']}] ODI #{d['odino']} | {d['mfr_name']} {d['modeltxt']} | {d['compdesc'] or 'N/A'} (score={d['score']:.2f})"
        for d in state["retrieved_docs"]
    )

    final_report = f"""# Root Cause Analysis Report

## Sự cố
{state['incident_text']}

## Phân tích
{state['draft_report']}

## Số lần sửa
{state['revision_count']}

## Nguồn tham khảo
{references}
"""
    print("    -> đã render report markdown")
    return {"draft_report": final_report}