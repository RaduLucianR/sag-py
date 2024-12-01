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


def get_pred(path):
    global PRED
    csv_file = open(path, "r")
    reader = csv.reader(csv_file, delimiter=",")

    for row in reader:
        key = row[0].strip()  # Get the first column as the key (e.g., "J15")
        values = set(
            map(str, row[1:])
        )  # Convert the remaining columns to strings and make a tuple
        PRED[key] = values


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
        R_P = set([job for job in J.difference(J_P) if PRED[job].issubset(J_P)])
        v_p = G.nodes[P[-1]]["state"]
        A = v_p.A
        X = v_p.X
        FTI = v_p.FTI
        A1 = A[0]
        A1_min = A1[0]
        A1_max = A1[1]

        for Ji in R_P:
            r_min, r_max, C_min, C_max, p_i = JDICT[Ji]

            def EFT_star(Jx):
                if Jx in X:
                    return FTI[Jx][0]  # EFT_x(v_p)
                else:
                    return BR[Jx]

            def LFT_star(Jx):
                if Jx in X:
                    return FTI[Jx][1]  # LFT_x(v_p)
                else:
                    return WR[Jx]

            def th(Jx):
                rx_max = JDICT[Jx][1]
                return max(
                    rx_max,
                    max(
                        [LFT_star(Jy) for Jy in PRED[Jx].difference(PRED[Ji])],
                        default=0,
                    ),
                )

            def R_min(Ja):
                ra_min = JDICT[Ja][0]
                return max(ra_min, max([EFT_star(Jy) for Jy in PRED[Ja]], default=0))

            def R_max(Ja):
                ra_max = JDICT[Ja][1]
                return max(ra_max, max([LFT_star(Jy) for Jy in PRED[Ja]], default=0))

            ESTi = max(R_min(Ji), A1_min)
            t_wc = max(A1_max, min([R_max(Jb) for Jb in R_P], default=INF))
            t_high = min([th(Jz) for Jz in R_P if JDICT[Jz][4] < p_i], default=INF)
            LSTi = min(t_wc, t_high - 1)

            if ESTi <= LSTi:
                EFTi = ESTi + C_min
                LFTi = LSTi + C_max
                PA = [
                    max(ESTi, A[idx][0]) for idx in range(1, m)
                ]  # {max{ESTi, A_x_min} | 2 <= x <= m}
                CA = [
                    max(ESTi, A[idx][1]) for idx in range(1, m)
                ]  # {max{ESTi, A_x_max} | 2 <= x <= m}

                PA.append(EFTi)
                CA.append(LFTi)

                for Jc in X.intersection(PRED[Ji]):
                    LFTc = FTI[Jc][1]
                    if LSTi < LFTc and LFTc in CA:
                        CA[CA.index(LFTc)] = LSTi

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

                BR[Ji] = min(EFTi - r_min, BR[Ji])
                WR[Ji] = max(LFTi - r_max, WR[Ji])

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

        ################ ROS ##############
        # r_min of all jobs in J / J^P
        all_r_min = [JDICT[Jx][0] for Jx in J.difference(J_P)]

        jobs_before_pp = 0  # Number of jobs that are potentially released before a polling point (PP) definitely happens
        for j in all_r_min:
            if j <= PP[1]:
                jobs_before_pp += 1

        # print(P)
        # print("Start of iter:", PP)
        if (
            jobs_before_pp == 0
        ):  # If there is no job released before the previous PP, then the next PP:
            # - potentially happens when 1 core potentially becomes available i.e. at A1_min
            # but only if the job was potentially released before the core becomes available
            # if the job is released after A1_min, then the PP potentially happens at the release time of that job.
            # - certainly happens when 1 core certainly becomes available i.e. A1_max
            # but only if the job was certainly released before the core becomes available
            # if the job is released after A1-max, then the PP certainly happens at the relese time of that job.
            pp_min = max(min(all_r_min), A1_min)
            pp_max = max(min(all_r_min), A1_max)
            PP = (pp_min, pp_max)

        E_P = set([Ji for Ji in R_P if JDICT[Ji][0] <= PP[1]])

        # print("After if:", PP)
        ####################################

        for Ji in E_P:
            r_min, r_max, C_min, C_max, p_i = JDICT[Ji]
            all_Rx_max = [JDICT[Jx][1] for Jx in E_P]
            rx_max_higher_priority = [
                JDICT[Jx][1] for Jx in E_P if (JDICT[Jx][4] < p_i)
            ]

            # if (
            #     r_min > PP[1]
            # ):  # If the task is released *after* a PP certainly happens, then it cannot be in the wait set
            #     ESTi = INF
            # else:
            #     ESTi = max(
            #         r_min, A1_min
            #     )  # PP_min coincides with A_min because the moment a core/thread is available, a polling point happens
            ESTi = max(r_min, A1_min)
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
                # if jobs_before_pp == 0 or (jobs_before_pp > 1 and PP[0] == PP[1]):
                #     new_PP = PP

                # if jobs_before_pp == 1:
                #     new_PP = new_A[0]

                # if jobs_before_pp > 1 and PP[0] != PP[1]:
                #     new_PP = (ESTi, LSTi)

                aux_E_P = E_P.difference(set([Ji]))

                if len(aux_E_P) > 0 and PP[0] == PP[1]:
                    new_PP = PP

                if len(aux_E_P) > 0 and PP[0] != PP[1]:
                    new_PP = (ESTi, LSTi)

                if len(aux_E_P) == 0:
                    new_PP = new_A[0]
                ###########################

                new_state = StateROS(new_A, new_X, new_FTI, new_PP)
                new_state_id = get_rand_node_id()
                G.add_node(new_state_id, state=new_state)
                G.add_edge(P[-1], new_state_id, job=Ji)
                # print(f"Dispatched {Ji}")
                BR[Ji] = min(EFTi - r_min, BR[Ji])
                WR[Ji] = max(LFTi - r_max, WR[Ji])
            else:
                # print(f"Can't dispatch {Ji}")
                pass

        # Next iteration
        P = shortestPathFromSourceToLeaf(G)
        # breakpoint()

    print("BR:", BR)
    print("WR:", WR)
    return G


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("PATH")
    parser.add_argument("--ROS", action="store_true")
    parser.add_argument("--end_time", default=0, type=int)
    parser.add_argument("--pred", default="", type=str)
    args = parser.parse_args()

    if args.end_time > 0:
        generate_jobs("tasks.csv", args.PATH, args.end_time, True)
        generate_diagram("tasks.csv", "./tasks.drawio", args.end_time)

    JDICT = convert_csv_to_dict(args.PATH)
    list_of_jobs = JDICT.keys()
    J = set(list_of_jobs)
    PRED = {j: set() for j in list_of_jobs}
    m = 2  # nr of cores

    if args.pred != "":
        get_pred(args.pred)
        print(PRED)

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
