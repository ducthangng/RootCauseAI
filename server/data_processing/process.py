# process.py
import glob
import sys

import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

# ── Data contract ─────────────────────────────────────────────
# TODO: chỉnh lại nếu schema Postgres của bạn khác
SUMMARY_COLS = ["MAKETXT", "MODELTXT", "YEARTXT", "COMPDESC", "CDESCR"]
EMBED_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
EMBED_DIM = 768  # phải khớp vector(768) trong schema.sql

CHUNK_SIZE = 5000
BATCH_SIZE_EMBED = 64

INPUT_DIR = "/opt/ml/processing/input/data"
OUTPUT_PATH = "/opt/ml/processing/output/processed.csv"


def build_summary(row: pd.Series) -> str:
    parts = [str(row[c]) for c in SUMMARY_COLS if str(row.get(c, "")).strip()]
    return " | ".join(parts)


def main() -> None:
    # 1. Đọc input — không hardcode tên file, y hệt bài học lần trước
    matches = glob.glob(f"{INPUT_DIR}/*.csv")
    if not matches:
        print(f"FATAL: no CSV found in {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(matches[0])
    print(f"loaded {len(df)} rows from {matches[0]}")

    # 2. Chuẩn hoá tên cột — khớp schema.sql (lowercase)
    df = df.rename(columns=str.lower)
    # SUMMARY_COLS viết hoa vì lấy từ notebook gốc; map sang cột đã lowercase
    summary_cols_lower = [c.lower() for c in SUMMARY_COLS]

    missing = [c for c in summary_cols_lower if c not in df.columns]
    if missing:
        print(f"FATAL: missing expected columns: {missing}", file=sys.stderr)
        print(f"available columns: {list(df.columns)}", file=sys.stderr)
        sys.exit(1)

    # 3. Build cột summary — NOT NULL, nên có fallback rõ ràng
    df["summary"] = df.apply(
        lambda row: " | ".join(
            str(row[c]) for c in summary_cols_lower if str(row[c]).strip()
        ),
        axis=1,
    )
    empty_summary = (df["summary"].str.strip() == "").sum()
    if empty_summary:
        print(f"WARNING: {empty_summary} rows had empty summary, filled with placeholder")
    df.loc[df["summary"].str.strip() == "", "summary"] = "NO_DESCRIPTION_AVAILABLE"

    # 4. Load model — CPU trong Processing Job (không có GPU ở đây)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"using device: {device}")
    model = SentenceTransformer(EMBED_MODEL_NAME, trust_remote_code=True, device=device)

    # 5. Embed theo chunk — giữ nguyên prefix bắt buộc của Nomic
    def embed_batch(texts: list[str]):
        prefixed = [f"search_document: {t if isinstance(t, str) else ''}" for t in texts]
        return model.encode(
            prefixed,
            batch_size=BATCH_SIZE_EMBED,
            show_progress_bar=False,
            normalize_embeddings=True,  # bắt buộc: index dùng vector_cosine_ops
        )

    all_embeddings = []
    for start in range(0, len(df), CHUNK_SIZE):
        chunk = df["summary"].iloc[start : start + CHUNK_SIZE].tolist()
        all_embeddings.append(embed_batch(chunk))
        print(f"embedded {min(start + CHUNK_SIZE, len(df))}/{len(df)}")

    import numpy as np

    embeddings = np.vstack(all_embeddings)
    assert embeddings.shape == (len(df), EMBED_DIM), (
        f"expected ({len(df)}, {EMBED_DIM}), got {embeddings.shape} — "
        "model/schema đang lệch, kiểm tra EMBED_DIM"
    )

    # 6. Format literal pgvector — Postgres COPY đọc thẳng được
    df["embedding"] = ["[" + ",".join(map(str, row)) + "]" for row in embeddings]

    # 7. Ghi output — SageMaker tự upload thư mục này lên S3
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"saved {len(df)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()