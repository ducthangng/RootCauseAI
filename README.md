# NHTSA Complaints Dataset (Processed & Embedded Version)

This document describes the data structure after cleaning, slimming down, and enriching for analysis and feature extraction.

### 📝 Summary of Changes
*   **Slimmed Down:** Removed unnecessary columns, keeping only the top 8 most important original fields.
*   **Cleaned:** Fixed date parsing errors; moved invalid date strings to the `_RAW_DATE` column.
*   **Enriched:** Added `summary` (concatenated rich text) and `embedding` (768-dim vector using model `nomic-ai/nomic-embed-text-v1.5`).

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
1. 
| case_id | category | component_hit_rate | faithfulness | llm_context_precision_without_reference | answer_relevancy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| EVAL-01 | airbag_nondeployment | 0.95 | 0.150000 | 0.116993 | 0.000000 |
| EVAL-02 | unintended_acceleration_ambiguous | 1.00 | 0.285714 | 0.265703 | 0.845759 |
| EVAL-03 | steering_loss | 0.00 | 0.583333 | 0.052632 | 0.838621 |
| EVAL-04 | ev_battery_fire | 0.85 | 0.136364 | 0.000000 | 0.856997 |
| EVAL-05 | fuel_leak_engine_fire | 0.00 | 0.263158 | 0.000000 | 0.840019 |