from .node_types import AgentState, log
from .clients import openai_client


def analysis_node(state: AgentState) -> dict:
    log("analysis", state)

    context = "\n---\n".join(
        f"[{d['id']}] (score={d['score']:.2f}, component category: {d['compdesc'] or 'N/A'}) "
        f"{(d['cdescr'] or '')[:500]}"
        for d in state["retrieved_docs"]
    )

    revision_instruction = (
        f"\n\nThe previous draft was rejected because: {state['critique']}\n"
        f"Revise it to fix exactly that issue."
        if state.get("critique") else ""
    )

    prompt = f"""You are a Quality Engineer analyzing the root cause of an incident.

NEW INCIDENT:
{state['incident_text']}

SIMILAR HISTORICAL INCIDENTS:
{context}

REQUIREMENTS:
- Identify the most likely root cause, based on evidence from the historical incidents above.
- Clearly cite the incident code (e.g. [98538]) whenever you use it as evidence.
- CRITICAL: Before using a historical incident as evidence, verify that the exact
  component/system it describes actually matches the mechanism you are analyzing.
  Do NOT conflate different components just because their names sound similar
  (e.g. an "accelerator cable" is NOT a "brake cable"; a car using its brakes to
  react to a failure is NOT the same as the brakes themselves failing). If a
  retrieved incident is only superficially similar but describes a different
  failure mechanism, do not cite it as supporting evidence for this root cause.
- If the historical data does not converge on a single root cause, it is acceptable
  to list 2-3 plausible causes, each backed by its own specific citation, as long as
  you state clearly that this is a list of possibilities rather than a single
  conclusion, and suggest a next diagnostic step.
- If the evidence is insufficient, say so explicitly ("insufficient data to conclude"),
  do not fabricate.
{revision_instruction}

Respond in English, as a concise paragraph, with inline incident citations.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    draft = response.choices[0].message.content
    print(f"    -> new draft ({len(draft)} chars)")
    return {"draft_report": draft}