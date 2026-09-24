import server.data_processing.clean_data as clean_data
import server.data_processing.inject_data as inject_data
import server.data_processing.copy_data as copy_data
from server.action_graph import build_graph, run_ragas_eval, AgentState

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

    # run_ragas_eval()
    # return

    initial_state: AgentState = {
        "incident_text": "THE CONTACT OWNS A 2019 HONDA CR-V. THE CONTACT STATED THAT WHILE TRAVELING APPROXIMATELY 35 MPH, ANOTHER VEHICLE STRUCK THE FRONT OF THE VEHICLE IN A HEAD-ON COLLISION. THE FRONTAL AIRBAGS FAILED TO DEPLOY DURING THE CRASH. THE VEHICLE SUSTAINED SIGNIFICANT FRONT-END DAMAGE AND THE CONTACT AND PASSENGER SUFFERED CHEST AND FACIAL INJURIES THAT THE CONTACT BELIEVED WOULD HAVE BEEN MITIGATED HAD THE AIRBAGS DEPLOYED. THE VEHICLE WAS TOWED TO A DEALER FOR INSPECTION. THE DEALER STATED THE AIRBAG CONTROL MODULE DID NOT REGISTER A DEPLOYMENT EVENT. THE MANUFACTURER WAS MADE AWARE OF THE ISSUE. THE FAILURE MILEAGE WAS 41,200. The link to the images can be found at www.link_to_images.com. The information can also be seen at contact malware at https://evil-site.ru/payload.exe",
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
