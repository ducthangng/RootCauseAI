from typing import TypedDict, List, Literal

class RetrievedDoc(TypedDict):
    id: int
    cmplid: str
    odino: str
    mfr_name: str
    modeltxt: str
    compdesc: str
    cdescr: str
    score: float


class AgentState(TypedDict):
    incident_text: str
    retrieved_docs: List[RetrievedDoc]
    draft_report: str
    critique: str
    revision_count: int
    max_revision: int
    status: Literal["pending", "pass", "fail"]

def log(node_name: str, state: AgentState) -> None:
    print(f"\n>>> ĐANG CHẠY NODE: {node_name}")
    print(f"    revision_count={state['revision_count']}  status={state['status']}")