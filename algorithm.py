import networkx as nx
import matplotlib.pyplot as plt
import argparse
import csv
import random
from generate_jobs import generate_jobs
from task_diagram import generate_diagram

######## Global constants ########
INF = 100000

######## Helper functions ########
"""
Acts like a hash function for node IDs.
It just spits random integers between 10^6 to 10^7 - 1.
"""


def get_rand_node_id():
    n = 6
    lower_bound = 10 ** (n - 1)
    upper_bound = 10**n - 1
    return random.randint(lower_bound, upper_bound)


def convert_csv_to_dict(path):
    csv_file = open(path, "r")
    reader = csv.reader(csv_file, delimiter=",")
    result = {}
    for row in reader:
        key = row[0].strip()  # Get the first column as the key (e.g., "J15")
        values = tuple(
            map(int, row[1:])
        )  # Convert the remaining columns to integers and make a tuple
        result[key] = values

    return result


##### Classes that encapsulate a state in the SAG ####
class State:
    def __init__(self, A: list[tuple], X: set, FTI: dict):
        self.A = A
        self.X = X
        self.FTI = FTI

    def __repr__(self):
        return f"{self.A}"


class StateROS:
    def __init__(self, A: list[tuple], X: set, FTI: dict, PP: tuple[int, int]):
        self.A = A
        self.X = X
        self.FTI = FTI
        self.PP = PP

    def __repr__(self):
        return f"{self.A}"


#### SAG functions for standard WC JLFP ####
def shortestPathFromSourceToLeaf(G):
    leaves = [node for node in G.nodes if G.out_degree(node) == 0]
    shortest_paths = []

    for leaf in leaves:
        sp = nx.shortest_path(G, source=0, target=leaf)
        shortest_paths.append(sp)

    return min(shortest_paths, key=len)


def ScheduleGraphConstructionAlgorithm(J, m):
    G = nx.DiGraph()
    BR = {Ji: INF for Ji in J}
    WR = {Ji: 0 for Ji in J}
    InitNode = State([(0, 0) for core in range(m)], set(), dict())
    G.add_node(0, state=InitNode)

    P = shortestPathFromSourceToLeaf(G)
    while len(P) - 1 < len(J):
        J_P = set([G[u][v]["job"] for u, v in zip(P[:-1], P[1:])])
        R_P = J.difference(J_P)
        v_p = G.nodes[P[-1]]["state"]
        A1 = v_p.A[0]
        A1_min = A1[0]
        A1_max = A1[1]

        A2 = v_p.A[1]
        A2_min = A2[0]
        A2_max = A2[1]

        for Ji in R_P:
            r_min, r_max, C_min, C_max, p_i = JDICT[Ji]
            all_Rx_max = [JDICT[Jx][1] for Jx in R_P]
            rx_max_higher_priority = [JDICT[Jx][1] for Jx in R_P if JDICT[Jx][4] < p_i]
            ESTi = max(r_min, A1_min)

            t_wc = max(A1_max, min(all_Rx_max, default=INF))
            t_high = min(rx_max_higher_priority, default=INF)
            LSTi = min(t_wc, t_high - 1)
            breakpoint()

            if ESTi <= LSTi:
                EFTi = ESTi + C_min
                LFTi = LSTi + C_max
                PA, CA = [], []
                PA.append(max(ESTi, A2_min))
                PA.append(EFTi)
                CA.append(max(ESTi, A2_max))
                CA.append(LFTi)
                PA.sort()
                CA.sort()

                new_A = [(0, 0) for i in range(m)]
                for i in range(m):
                    new_A[i] = (PA[i], CA[i])

                new_X = set()
                for Jx in v_p.X:
                    EFTx = v_p.FTI[Jx][0]
                    if LSTi <= EFTx:
                        new_X.add(Jx)
                new_X.add(Ji)

                new_FTI = dict()
                for Jx in new_X:
                    if Jx in v_p.FTI:
                        new_FTI[Jx] = v_p.FTI[Jx]
                new_FTI[Ji] = (EFTi, LFTi)

                new_state = State(new_A, new_X, new_FTI)
                new_state_id = get_rand_node_id()
                G.add_node(new_state_id, state=new_state)
                G.add_edge(P[-1], new_state_id, job=Ji)
                print(f"Dispatched: {Ji}")

        # Next iteration
        P = shortestPathFromSourceToLeaf(G)

    return G


#### SAG functions for ROS-flavored WC JLFP ####


def collect_released_jobs(J, J_P, PP):
    R_P = set()

    for Ji in J.difference(J_P):
        if JDICT[Ji][1] <= PP[1]:
            R_P.add(Ji)

    return R_P


def get_R_P(J, J_P, PP):
    R_P = set()
    R_P = collect_released_jobs(J, J_P, PP)

    if len(R_P) == 0:  # If set is empty
        all_r_min = [JDICT[Jx][0] for Jx in J.difference(J_P)]
        PP = (min(all_r_min), min(all_r_min))
        R_P = collect_released_jobs(J, J_P, PP)

    return R_P, PP


def ScheduleGraphConstructionAlgorithmROS(J, m):
    G = nx.DiGraph()
    BR = {Ji: INF for Ji in J}
    WR = {Ji: 0 for Ji in J}
    InitNode = StateROS([(0, 0) for core in range(m)], set(), dict(), (0, 0))
    G.add_node(0, state=InitNode)

    P = shortestPathFromSourceToLeaf(G)
    while len(P) - 1 < len(J):
        J_P = set([G[u][v]["job"] for u, v in zip(P[:-1], P[1:])])
        v_p = G.nodes[P[-1]]["state"]
        PP = v_p.PP

        A1 = v_p.A[0]
        A1_min = A1[0]
        A1_max = A1[1]

        A2 = v_p.A[1]
        A2_min = A2[0]
        A2_max = A2[1]

        R_P = J.difference(J_P)

        ###################################
        all_r_min = [JDICT[Jx][0] for Jx in J.difference(J_P)]

        jobs_before_pp = 0
        for j in all_r_min:
            if j <= PP[1]:
                jobs_before_pp += 1

        if (
            jobs_before_pp == 0
        ):  # If there is no job released before the previous PP, then the next PP
            # - potentially happens when 1 core potentially becomes available i.e. A1_min
            # but only if the job was potentially released before it becomes available
            # if the job is released after A1_min, then the PP potentially happens at the release time of that job.
            # - certainly happens when 1 core certainly becomes available i.e. A1_max
            # but only if the job was certainly released before it becomes available
            # if the job is released after A1-max, then the PP certainly happens at the relese time of that job.
            pp_min = max(min(all_r_min), A1_min)
            pp_max = max(min(all_r_min), A1_max)
            PP = (pp_min, pp_max)
        ####################################

        for Ji in R_P:
            r_min, r_max, C_min, C_max, p_i = JDICT[Ji]
            all_Rx_max = [JDICT[Jx][1] for Jx in R_P if JDICT[Jx][0] <= PP[1]]
            rx_max_higher_priority = [
                JDICT[Jx][1]
                for Jx in R_P
                if (JDICT[Jx][4] < p_i and JDICT[Jx][0] <= PP[1])
            ]

            if (
                r_min > PP[1]
            ):  # If the task is released *after* a PP certainly happens, then it cannot be in the wait set
                ESTi = INF
            else:
                ESTi = max(
                    r_min, A1_min
                )  # PP_min coincides with A_min because the moment a core/thread is available, a polling point happens
            # breakpoint()

            t_wc = max(A1_max, min(all_Rx_max, default=INF))
            t_high = min(rx_max_higher_priority, default=INF)
            LSTi = min(t_wc, t_high - 1)
            # breakpoint()

            if ESTi <= LSTi:
                EFTi = ESTi + C_min
                LFTi = LSTi + C_max
                PA, CA = [], []
                PA.append(max(ESTi, A2_min))
                PA.append(EFTi)
                CA.append(max(ESTi, A2_max))
                CA.append(LFTi)
                PA.sort()
                CA.sort()

                new_A = [(0, 0) for i in range(m)]
                for i in range(m):
                    new_A[i] = (PA[i], CA[i])

                new_X = set()
                for Jx in v_p.X:
                    EFTx = v_p.FTI[Jx][0]
                    if LSTi <= EFTx:
                        new_X.add(Jx)
                new_X.add(Ji)

                new_FTI = dict()
                for Jx in new_X:
                    if Jx in v_p.FTI:
                        new_FTI[Jx] = v_p.FTI[Jx]
                new_FTI[Ji] = (EFTi, LFTi)

                ############ ROS ##########
                if (jobs_before_pp == 0) or (jobs_before_pp > 1 and PP[0] == PP[1]):
                    new_PP = PP

                if jobs_before_pp == 1:
                    new_PP = new_A[0]

                if jobs_before_pp > 1 and PP[0] != PP[1]:
                    new_PP = (ESTi, LSTi)
                ###########################

                new_state = StateROS(new_A, new_X, new_FTI, new_PP)
                new_state_id = get_rand_node_id()
                G.add_node(new_state_id, state=new_state)
                G.add_edge(P[-1], new_state_id, job=Ji)

                BR[Ji] = min(EFTi, BR[Ji])
                WR[Ji] = max(LFTi, WR[Ji])

        # Next iteration
        P = shortestPathFromSourceToLeaf(G)

    print("BR:", BR)
    print("WR:", WR)
    return G


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("PATH")
    parser.add_argument("--ROS", action="store_true")
    parser.add_argument("--end_time", default=0, type=int)
    args = parser.parse_args()

    if args.end_time > 0:
        generate_jobs("tasks.csv", args.PATH, args.end_time, True)
        generate_diagram("tasks.csv", "./tasks.drawio", args.end_time)

    JDICT = convert_csv_to_dict(args.PATH)
    list_of_jobs = JDICT.keys()
    J = set(list_of_jobs)
    m = 2  # nr of cores

    if args.ROS:
        G = ScheduleGraphConstructionAlgorithmROS(J, m)
        node_labels = {
            node: f"{data['state'].A}{data['state'].PP}"
            for node, data in G.nodes(data=True)
        }
    else:
        G = ScheduleGraphConstructionAlgorithm(J, m)
        node_labels = {node: f"{data['state'].A}" for node, data in G.nodes(data=True)}

    # Draw
    edge_labels = {(u, v): f"{data['job']}" for u, v, data in G.edges(data=True)}
    plt.figure(figsize=(12, 8))
    pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    nx.draw(G, pos, with_labels=False, node_color="lightblue", node_size=300)
    nx.draw_networkx_labels(G, pos, labels=node_labels)
    nx.draw_networkx_edge_labels(G, pos, edge_labels)
    plt.savefig("sag.png", dpi=300, bbox_inches="tight")
