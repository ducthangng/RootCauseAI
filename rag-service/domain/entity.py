from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class ProcessJobMessage:
    job_id: str
    total_row: int
    is_done: bool
    queue_at: datetime
    # Luôn dùng timezone-aware
    time_received: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # default_factory chạy MỖI LẦN tạo object mới — khác lỗi kinh điển
    # `received_at: datetime = datetime.now()` (chỉ tính 1 lần lúc class được LOAD, sai hoàn toàn)
