import src.data_processing.clean_data as clean_data
import src.data_processing.inject_data as inject_data
import src.data_processing.copy_data as copy_data
from src.action_graph.node_types import AgentState
from src.action_graph.graph import build_graph

def main():
    # copy_data.import_csv()
    # copy_data.get_line()
    # clean_data.clean_row_quotation()
    # clean_data.clean_date()
    # inject_data.inject()

    initial_state: AgentState = {
        "incident_text": "Xe mất phanh đột ngột ở tốc độ cao",
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
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
