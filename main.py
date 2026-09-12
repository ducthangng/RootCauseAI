import src.data_processing.clean_data as clean_data
import src.data_processing.inject_data as inject_data
import src.data_processing.copy_data as copy_data
from src.action_graph import build_graph, run_ragas_eval, AgentState

import time


def main():
    # copy_data.import_csv()
    # copy_data.get_line()
    # clean_data.clean_row_quotation()
    # clean_data.clean_date()
    # inject_data.inject()

    # t0 = time.perf_counter()
    # cur.execute(query, (query_vector, query_vector))
    # rows = cur.fetchall()
    # print(f"Latency: {(time.perf_counter() - t0) * 1000:.2f}ms")

    run_ragas_eval()
    return

    initial_state: AgentState = {
        "incident_text": "car broke down because the break was stuck",
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
    final_state = graph.invoke(initial_state)

    print("\n" + "=" * 60)
    print("STATE CUỐI CÙNG:")
    print("=" * 60)
    for k, v in final_state.items():
        if k != "retrieved_docs":
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
