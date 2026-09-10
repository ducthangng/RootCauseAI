import json
from .node_types import AgentState, log
from .clients import openai_client

EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["pass", "fail"]},
        "critique": {"type": "string", "description": "Lý do fail, hoặc chuỗi rỗng nếu pass"},
    },
    "required": ["status", "critique"],
    "additionalProperties": False,
}


def evaluation_node(state: AgentState) -> dict:
    log("evaluation", state)

    prompt = f"""Bạn là người thẩm định (evaluator) nghiêm khắc cho báo cáo Root Cause Analysis.

BÁO CÁO CẦN CHẤM:
{state['draft_report']}

TIÊU CHÍ PASS:
- Phải trích dẫn ít nhất 1 mã sự cố lịch sử (dạng [INC-xxx]) làm bằng chứng.
- Root cause phải cụ thể, không mơ hồ chung chung kiểu "có thể do nhiều nguyên nhân".
- Không được bịa thông tin không có trong dữ liệu được cung cấp.

Nếu FAIL, critique phải nêu CHÍNH XÁC điểm thiếu, để Analysis Agent sửa đúng chỗ đó.
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
    print(f"    -> chấm điểm: {result['status'].upper()} (lần thứ {new_count})")
    return {
        "status": result["status"],
        "critique": result["critique"],
        "revision_count": new_count,
    }