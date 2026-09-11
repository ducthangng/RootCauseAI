import json
from .node_types import AgentState, log
from .clients import openai_client

EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["pass", "fail"]},
        "critique": {"type": "string", "description": "Reason for failure, or empty string if passed"},
    },
    "required": ["status", "critique"],
    "additionalProperties": False,
}


def evaluation_node(state: AgentState) -> dict:
    log("evaluation", state)

    prompt = f"""You are a strict evaluator for a Root Cause Analysis report.

REPORT TO GRADE:
{state['draft_report']}

PASS CRITERIA:
- Must cite at least 1 historical incident code (e.g. [id]) as concrete evidence.
- If the evidence supports a single clear root cause, it must be stated explicitly, not vaguely.
- If the historical data does NOT converge on a single root cause (multiple different failure
  modes present), the report IS ALLOWED to list 2-3 plausible causes, as long as:
  (a) each cause has its own specific citation, and
  (b) the report clearly states this is a list of possibilities rather than a single conclusion,
      and suggests a next diagnostic step.
- CRITICAL CHECK: For each citation used, verify the cited incident's actual described
  component/failure mechanism genuinely matches the claim being made about it. Reject the
  report if it conflates two different components or mechanisms (e.g. citing an incident
  about an accelerator cable failure as evidence for a brake system defect, or citing a case
  where brakes were used to react to a failure as if the brakes themselves had failed).
  A citation that exists but is misapplied to an unrelated mechanism must FAIL.
- DO NOT PASS if: no citations at all, information is fabricated beyond what the data supports,
  or the report is generic without grounding each specific claim in a citation
  ("could be due to multiple causes" with no citation = FAIL).

If FAIL, the critique must state EXACTLY what is missing or incorrect.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "evaluation_result", "strict": True, "schema": EVAL_SCHEMA},
        },
    )
    result = json.loads(response.choices[0].message.content)

    new_count = state["revision_count"] + 1
    print(f"    -> graded: {result['status'].upper()} (attempt #{new_count})")
    return {
        "status": result["status"],
        "critique": result["critique"],
        "revision_count": new_count,
    }