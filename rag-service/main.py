# server/http_app.py
from fastapi import FastAPI
from action_graph import build_graph, AgentState

app = FastAPI()
graph = build_graph()

@app.post("/incidents/analyze")
def analyze(payload: dict):
    initial_state: AgentState = {
        "incident_text": payload["incident_text"],
        "retrieved_docs": [],
        "draft_report": "",
        "critique": "",
        "revision_count": 0,
        "max_revision": 3,
        "status": "pending",
    }
    final_state = graph.invoke(initial_state)
    return {k: v for k, v in final_state.items() if k != "retrieved_docs"}