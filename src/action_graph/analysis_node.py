import os
from .node_types import AgentState, log
from .clients import openai_client, embed_model

def analysis_node(state: AgentState) -> dict:
    log("analysis", state)

    context = "\n---\n".join(
        f"[{d['id']}] (score={d['score']:.2f}) {d['compdesc']} {d['cdescr']}" for d in state["retrieved_docs"]
    )

    revision_instruction = (
        f"\n\nBản trước bị từ chối vì: {state['critique']}\nHãy sửa lại, khắc phục đúng điểm đó."
        if state.get("critique") else ""
    )

    prompt = f"""Bạn là kỹ sư chất lượng (Quality Engineer) phân tích nguyên nhân gốc rễ (root cause) của một sự cố.

SỰ CỐ MỚI:
{state['incident_text']}

CÁC SỰ CỐ TƯƠNG TỰ TRONG LỊCH SỬ:
{context}

YÊU CẦU:
- Xác định root cause khả dĩ nhất, dựa trên bằng chứng từ các sự cố lịch sử ở trên.
- Trích dẫn RÕ RÀNG mã sự cố (ví dụ [INC-001]) khi dùng nó làm bằng chứng.
- Nếu bằng chứng không đủ, nói thẳng là "chưa đủ dữ liệu để kết luận", đừng bịa.
{revision_instruction}

Trả lời bằng tiếng Việt, dạng đoạn văn ngắn gọn, có trích dẫn mã sự cố.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    draft = response.choices[0].message.content
    print(f"    -> draft mới ({len(draft)} ký tự)")
    return {"draft_report": draft}