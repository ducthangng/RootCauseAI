from .action_node import action_node
from .analysis_node import analysis_node
from .evaluation_node import evaluation_node
from .retrival_node import retrieve_node
from .node_types import AgentState
from typing import TypedDict, List, Literal
from .route import route_after_evaluation

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy
from openai import RateLimitError, APITimeoutError, APIConnectionError


# Chỉ retry các lỗi TẠM THỜI của OpenAI (rate limit, timeout, connection drop)
# KHÔNG retry lỗi do cậu gửi request sai (400 BadRequest) — retry cái đó vô ích, sai vẫn hoàn sai
llm_retry_policy = RetryPolicy(
    retry_on=(RateLimitError, APITimeoutError, APIConnectionError),
    max_attempts=4,
    initial_interval=1.0,
    backoff_factor=2.0,
    jitter=True,  # tránh "thundering herd" nếu cậu chạy nhiều incident song song
)

def build_graph() -> CompiledStateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("retrieve", retrieve_node)  # không cần LLM, không cần retry policy này
    builder.add_node("analysis", analysis_node, retry=llm_retry_policy)
    builder.add_node("evaluation", evaluation_node, retry=llm_retry_policy)
    builder.add_node("action", action_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "analysis")
    builder.add_edge("analysis", "evaluation")
    builder.add_conditional_edges(
        "evaluation",
        route_after_evaluation,
        {"analysis": "analysis", "action": "action"},
    )
    builder.add_edge("action", END)

    return builder.compile()