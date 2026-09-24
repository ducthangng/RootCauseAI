# NHTSA Complaints Dataset (Processed & Embedded Version)

This document describes the data structure after cleaning, slimming down, and enriching for analysis and feature extraction.

### 📝 Summary of Changes
*   **Slimmed Down:** Removed unnecessary columns, keeping only the top 8 most important original fields.
*   **Cleaned:** Fixed date parsing errors; moved invalid date strings to the `_RAW_DATE` column.
*   **Enriched:** Added `summary` (concatenated rich text) and `embedding` (768-dim vector using model `nomic-ai/nomic-embed-text-v1.5`).

root_cause_ai/
├── ingestion_service/            # lifecycle: trigger bởi file event, batch, không cần layer sâu
│   ├── watcher.py
│   ├── chunker.py
│   └── vectorstore_writer.py
│
├── server/                  # lifecycle: request/response API — clean architecture skeleton
│   ├── domain/
│   │   ├── entities.py           # Query, RetrievedChunk, Answer
│   │   └── ports.py              # Protocol: Retriever, Generator, VectorStoreRepository
│   ├── application/
│   │   └── use_cases/
│   │       └── answer_question.py   # chỉ phụ thuộc Protocol, không biết FastAPI/LangGraph tồn tại
│   ├── adapters/
│   │   ├── api/
│   │   │   └── router.py          # FastAPI /query, gọi use case
│   │   ├── retrieval/
│   │   │   └── pgvector_retriever.py   # implement Retriever
│   │   └── generation/
│   │       └── llm_client.py      # implement Generator, LangGraph nếu dùng nằm ở đây
│   └── main/
│       ├── app.py                 # DI wiring, assemble FastAPI app
│       └── config.py
│
├── shared/                         # import bởi cả 2 service — bắt buộc, không phải DRY tuỳ chọn
│   ├── embeddings.py                # 1 nguồn duy nhất cho embedding model/version
│   └── vectorstore_client.py
│
└── data/                             # runtime, gitignored
    ├── incoming/
    ├── processed/
    └── failed/
---

## 📊 Data Schema

The table below includes the 8 most important original columns and 3 newly added columns to support semantic search capabilities.

| Field Name | Data Type | Source | Description |
|:---|:---|:---:|:---|
| **CMPLID** | CHAR(9) | Original | Unique ID for the complaint (Primary Key). |
| **MAKETXT** | CHAR(25) | Original | Vehicle Make (e.g., TOYOTA, FORD). |
| **MODELTXT** | CHAR(256)| Original | Vehicle Model (e.g., CAMRY, MUSTANG). |
| **YEARTXT** | CHAR(4) | Original | Model Year of the vehicle. |
| **FAILDATE** | DATE | Original | Date of the incident (YYYY-MM-DD). |
| **COMPDESC** | CHAR(256)| Original | Description of the specific component involved (comdesc). |
| **CDESCR** | TEXT | Original | Detailed consumer complaint narrative. |
| **MILES** | NUMBER(7)| Original | Vehicle mileage at the time of failure. |
| **summary** | TEXT | **New** | **(New Column)** Concatenated rich text combining: `MFR_NAME`, `MODELTXT`, `COMPDESC`, and `CDESCR`. Used as input for embedding generation. |
| **embedding** | VECTOR(768)| **New** | **(New Column)** 768-dimensional vector derived from the `summary` column. Generated using model **`nomic-ai/nomic-embed-text-v1.5`**. |
| **\*_RAW_DATE** | TEXT | **New** | **(New Column)** Contains the raw string value for dates that failed parsing. Valid dates are formatted correctly; invalid data is preserved here for debugging. |

---

### 💡 Details on New Fields

1.  **`summary`**:
    *   **Purpose:** Creates a single rich text field so the AI model understands the full context of the complaint (Manufacturer + Model + Component + Details).
    *   **Logic:** Concatenates the relevant text fields.

2.  **`embedding`**:
    *   **Purpose:** Enables similarity search in vector databases (e.g., Pinecone, Milvus, pgvector).
    *   **Model:** `nomic-ai/nomic-embed-text-v1.5`.
    *   **Dimensions:** 768.

3.  **`_RAW_DATE`**:
    *   **Purpose:** Preserves original data integrity for auditing. If a date cannot be parsed into a standard format, it is moved here to prevent data loss.



### Evaluations
1. Initially:

| case_id | category | component_hit_rate | faithfulness | llm_context_precision_without_reference | answer_relevancy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| EVAL-01 | airbag_nondeployment | 0.95 | 0.150000 | 0.116993 | 0.000000 |
| EVAL-02 | unintended_acceleration_ambiguous | 1.00 | 0.285714 | 0.265703 | 0.845759 |
| EVAL-03 | steering_loss | 0.00 | 0.583333 | 0.052632 | 0.838621 |
| EVAL-04 | ev_battery_fire | 0.85 | 0.136364 | 0.000000 | 0.856997 |
| EVAL-05 | fuel_leak_engine_fire | 0.00 | 0.263158 | 0.000000 | 0.840019 |

## Evaluation Limitations

RAGAS-based evaluation (`faithfulness`, `llm_context_precision_without_reference`, `answer_relevancy`) was run on a 5-case, manually-curated eval set. Results should be read as *directional signal*, not a certified benchmark. Key limitations below.

## Evaluation Limitations

RAGAS metrics were run on a 5-case eval set (`faithfulness`, `llm_context_precision_without_reference`, `answer_relevancy`). Read as directional signal, not a certified benchmark.

| Limitation | Evidence | Impact |
|---|---|---|
| Small sample | n = 5 incidents | No statistical confidence — indicative only. |
| LLM-judge non-determinism | Same case scored 0.10–0.79 faithfulness across runs at low temperature | Trust only patterns that repeat across runs, not single scores. |
| `answer_relevancy` unreliable | Score forced to 0 by a binary "noncommittal" flag; penalizes honest hedging | Not used as a quality signal. |
| Faithfulness capped (~0.6) | Citations topically correct but mechanistically imprecise (e.g. "pump" cited for "assist motor" claim) | Needs a prompt fix in `analysis_node`: match claim specificity to citation specificity. |
| Context precision = 0.0 (reproducible) | EV battery-fire, fuel-leak-fire cases | Corpus lacks real precedents for these failure modes — a data gap, not a retrieval bug. |
| Reference-free metrics | No ground-truth answers used | Check consistency/relevance, not correctness — a confident, well-cited, wrong answer can still score well. |




