from .node_types import AgentState

def route_after_evaluation(state: AgentState) -> str:
    if state["status"] == "pass":
        return "action"
    if state["revision_count"] >= state["max_revision"]:
        print("    !! hết lượt sửa cho phép, ép đi action")
        return "action"
    return "analysis"