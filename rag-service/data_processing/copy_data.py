"""
Import file CSV (đã có sẵn cột embedding dạng pgvector literal "[0.1,0.2,...]",
tải về từ Colab) thẳng vào Postgres bằng COPY — nhanh hơn insert row-by-row
hay execute_values rất nhiều vì Postgres đọc trực tiếp stream, không qua
round-trip Python cho từng dòng.
"""

import csv
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "rootcauseai",
    "user": "rootcauseai",
    "password": "changeme",
}

CSV_PATH = "assets/complaints_ready_for_pg.csv"
TABLE = "complaints"


def get_csv_columns(path: str) -> list[str]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return next(reader)

def get_line() -> list[str]:
    with open('assets/complaints_ready_for_pg.csv', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        row = next(reader)  # dòng data đầu tiên = "line 2" trong thông báo lỗi COPY
        idx = header.index('compdesc')
        print(f"Length: {len(row[idx])}")
        print(row[idx])

    return  

def import_csv(csv_path: str = CSV_PATH, table: str = TABLE):

    columns = get_csv_columns(csv_path)
    col_str = ", ".join(columns)

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur, open(csv_path, "r", encoding="utf-8") as f:
            copy_sql = (
                f"COPY {table} ({col_str}) FROM STDIN "
                f"WITH (FORMAT csv, HEADER true)"
            )
            cur.copy_expert(copy_sql, f)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"Import xong. Tổng số dòng trong bảng: {cur.fetchone()[0]}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()