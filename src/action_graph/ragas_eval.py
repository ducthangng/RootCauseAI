"""
RootCause AI -- eval harness.

What this script does:
  1. Loads eval_set.jsonl (5 hand-authored, deliberately diverse incidents --
     see the "targets" field on each case for WHY that case exists).
  2. Runs each incident through YOUR compiled LangGraph app to get the
     final AgentState (retrieved_docs + draft_report after the
     analysis/evaluation revise loop).
  3. Runs a cheap, deterministic, non-LLM sanity check FIRST:
     does retrieved_docs even contain the expected NHTSA component?
     This costs nothing and catches an HNSW/retrieval regression (bug #1)
     before you spend LLM-judge calls on it.
  4. Formats everything into a ragas EvaluationDataset and scores it with:
       - Faithfulness                       (checks bug #3: citation grounding)
       - LLMContextPrecisionWithoutReference (checks bug #1: retrieval quality)
       - AnswerRelevancy                     (checks: does the report answer
                                               THIS incident, or is it generic)

You have to wire in step 2 yourself (import your compiled graph). That's
intentional -- this file does not fabricate a pipeline you haven't run.

Before trusting these import names, verify against YOUR installed version:
    python -c "import ragas; print(ragas.__version__)"
    python -c "import ragas.metrics as m; print([x for x in dir(m) if not x.startswith('_')])"
Ragas has been mid-migration between a legacy sync API (ragas.metrics +
evaluate()) and a newer async "collections" API -- the names below are the
legacy/stable ones as documented at docs.ragas.io as of Sept 2026. Don't
assume; check.
"""

import os
import json
from pathlib import Path
from .node_types import AgentState, RetrievedDoc
from .graph import build_graph


from ragas import EvaluationDataset, evaluate
from ragas.metrics import Faithfulness, LLMContextPrecisionWithoutReference, AnswerRelevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.run_config import RunConfig

# ---------------------------------------------------------------------------
# 0. Config
# ---------------------------------------------------------------------------
EVAL_SET_PATH = Path(__file__).resolve().parents[2] / "evals" / "eval_sets.jsonl"
OUT_CSV_PATH = Path(__file__).resolve().parents[2] / "assets" / "ragas_results.csv"

# Use a DIFFERENT judge model than your pipeline's gpt-4o-mini generator.
# Grading your own homework with the same model that wrote it is a weaker
# eval -- it shares the same blind spots. gpt-4o (bigger) as judge is the
# minimum bar; swapping in a different model family is even better if you
# have access to one.
JUDGE_MODEL = "gpt-4o"

evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model=JUDGE_MODEL, temperature=0))
evaluator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())


# ---------------------------------------------------------------------------
# 1. Wire in YOUR graph here
# ---------------------------------------------------------------------------
def run_incident_through_graph(incident_text: str, id: str) -> dict:
    """
    Replace the body of this function with a call into your compiled
    StateGraph. It must return the FINAL AgentState dict (i.e. after the
    analysis_node <-> evaluation_node loop has resolved to pass/max_revision).

    Example, once you import your actual graph module:

        from rootcause_ai.graph import app  # your compiled StateGraph

        initial_state = {
            "incident_text": incident_text,
            "retrieved_docs": [],
            "draft_report": "",
            "critique": "",
            "revision_count": 0,
            "max_revision": 3,
            "status": "pending",
        }
        final_state = app.invoke(initial_state)
        return final_state
    """

    initial_state: AgentState = {
            "incident_text": incident_text,
            "retrieved_docs": [],
            "draft_report": "",
            "critique": "", 
            "revision_count": 0,
            "max_revision": 3,
            "status": "pending",
        }
    
    print("=" * 60)
    print("BẮT ĐẦU CHẠY GRAPH")
    print("=" * 60)

    graph = build_graph()
    # final_state = graph.invoke(initial_state)
    final_state = graph.invoke(
        initial_state,
        config={
            "run_name": f"incident-{id}",   # hoặc odino/cmplid nếu có sẵn
            "tags": ["rootcause-ai"],
            "metadata": {"incident_id": id},
        },
    )

    return final_state

"""
    Turn your RetrievedDoc records into the flat strings ragas expects for
    `retrieved_contexts`. Keep enough structure that an LLM judge (and you,
    reading the CSV later) can tell WHICH vehicle/component a context came
    from -- that's what makes the component-match sanity check below legible.
    """
def docs_to_context_strings(retrieved_docs: list[dict]) -> list[str]:
    return [
        f"[doc_id={d['id']} mfr={d['mfr_name']} model={d['modeltxt']} "
        f"component={d['compdesc']}] {d['cdescr']}"
        for d in retrieved_docs
    ]

"""
    Cheap, deterministic, zero-LLM-cost check: what fraction of retrieved
    docs actually belong to the NHTSA component category this incident is
    about? This is your first line of defense -- run it before you burn
    LLM-judge calls on a retrieval set that's obviously off-topic.

    Do NOT expect 1.0. A real RCA case legitimately pulls some cross-
    component context (e.g. a wiring-harness doc showing up for an airbag
    non-deployment). Treat a hit rate near 0 as the real alarm.
"""
def component_hit_rate(retrieved_docs: list[dict], expected_component: str) -> float:   
    if not retrieved_docs:
        return 0.0
    hits = sum(1 for d in retrieved_docs if expected_component.upper() in d["compdesc"].upper())
    return hits / len(retrieved_docs)


# ---------------------------------------------------------------------------
# 2. Run the eval set through the pipeline
# ---------------------------------------------------------------------------
def build_ragas_rows() -> list[dict]:
    rows = []
    # encoding = utf-8-sig to remove unseeable white spaces
    # encoding="utf-8-sig"
    with open(EVAL_SET_PATH) as f:
        cases = [json.loads(line) for line in f if line.strip()]

    for case in cases:
        final_state = run_incident_through_graph(case["incident_text"], case["case_id"])

        hit_rate = component_hit_rate(final_state["retrieved_docs"], case["expected_component"])
        print(
            f"{case['case_id']} ({case['category']}): "
            f"component_hit_rate={hit_rate:.2f}  "
            f"revisions={final_state.get('revision_count')}  "
            f"status={final_state.get('status')}"
        )
        if hit_rate == 0.0:
            print(
                f"  !! ALARM: zero docs matched expected_component="
                f"'{case['expected_component']}'. This smells like bug #1 "
                f"again (HNSW recall collapse) -- go check the raw retrieval "
                f"for this case BEFORE looking at the ragas scores."
            )

        rows.append(
            {
                "user_input": case["incident_text"],
                "retrieved_contexts": docs_to_context_strings(final_state["retrieved_docs"]),
                "response": final_state["draft_report"],
                # metadata carried through for your own analysis, not scored by ragas
                "case_id": case["case_id"],
                "category": case["category"],
                "component_hit_rate": hit_rate,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 3. Score with ragas
# ---------------------------------------------------------------------------
def run_ragas_eval():
    rows = build_ragas_rows()

    dataset = EvaluationDataset.from_list(
        [
            {
                "user_input": r["user_input"],
                "retrieved_contexts": r["retrieved_contexts"],
                "response": r["response"],
            }
            for r in rows
        ]
    )

    metrics = [
        Faithfulness(llm=evaluator_llm),
        LLMContextPrecisionWithoutReference(llm=evaluator_llm),
        AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
    ]

    # without RaiseException, the output might contain lots of NaN
    run_config = RunConfig(max_workers=1, max_retries=5, max_wait=60)
    result = evaluate(dataset=dataset, metrics=metrics, raise_exceptions=True, run_config=run_config)
    # result = evaluate(dataset=dataset, metrics=metrics)
    df = result.to_pandas()

    # reattach your own metadata so the CSV is actually readable per-case
    df["case_id"] = [r["case_id"] for r in rows]
    df["category"] = [r["category"] for r in rows]
    df["component_hit_rate"] = [r["component_hit_rate"] for r in rows]

    df.to_csv(OUT_CSV_PATH, index=False)
    print(f"\nWrote {OUT_CSV_PATH}")
    print(df[["case_id", "category", "component_hit_rate", "faithfulness",
              "llm_context_precision_without_reference", "answer_relevancy"]])

    # ---- how to read this, case by case -----------------------------------
    # low faithfulness              -> analysis_node cited something that
    #                                   doesn't actually support the claim
    #                                   (bug #3 regression -- check EVAL-05
    #                                   first, it's designed to trigger this)
    # low context precision + low
    # component_hit_rate together   -> retrieval regression (bug #1 -- check
    #                                   EVAL-04 first, dense EV-fire cluster)
    # high faithfulness + low
    # answer_relevancy               -> the report is well-grounded but generic
    #                                   / not actually addressing what THIS
    #                                   incident asked -- a prompt problem in
    #                                   analysis_node, not a retrieval problem
    # EVAL-02 gets flagged "fail" by
    # evaluation_node on every run     -> bug #2 fix regressed (it's the case
    #                                   designed to need a multi-cause answer)
    # EVAL-03 sails through with a
    # vague multi-cause hedge          -> bug #2 fix over-corrected into
    #                                   rubber-stamping vagueness everywhere
