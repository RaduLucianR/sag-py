import networkx as nx
import matplotlib.pyplot as plt
import argparse
import csv
import random

from generate_jobs import generate_jobs

def get_rand_node_id():
    n = 6
    lower_bound = 10**(n-1)
    upper_bound = 10**n - 1
    return random.randint(lower_bound, upper_bound)

def convert_csv_to_dict(path): 
    csv_file = open(path, 'r')
    reader = csv.reader(csv_file, delimiter=',')
    result = {}
    for row in reader:
        key = row[0].strip()  # Get the first column as the key (e.g., "J15")
        values = tuple(map(int, row[1:]))  # Convert the remaining columns to integers and make a tuple
        result[key] = values
    
    return result

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


def shortestPathFromSourceToLeaf(G):
    leaves = [node for node in G.nodes if G.out_degree(node) == 0]
    shortest_paths = []

    for leaf in leaves:
        sp = nx.shortest_path(G, source = 0, target = leaf)
        shortest_paths.append(sp)
    
    return min(shortest_paths, key = len)

def ScheduleGraphConstructionAlgorithm(J, m):
    G = nx.DiGraph()
    BR = {Ji: INF for Ji in J}
    WR = {Ji: 0 for Ji in J}
    InitNode = State([(0, 0) for core in range(m)], set(), dict())
    G.add_node(0, state = InitNode)

    P = shortestPathFromSourceToLeaf(G)
    while len(P) - 1 < len(J):
        J_P = set([G[u][v]['job'] for u, v in zip(P[:-1], P[1:])])
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

            t_wc = max(A1_max, min(all_Rx_max, default = INF))
            t_high = min(rx_max_higher_priority, default = INF)
            LSTi = min(t_wc, t_high - 1)

            if ESTi <= LSTi:
                print(f"Dispatched {Ji}")
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
                G.add_node(new_state_id, state = new_state)
                G.add_edge(P[-1], new_state_id, job = Ji)

        # Next iteration
        P = shortestPathFromSourceToLeaf(G)
    
    return G

def collect_released_jobs(J, J_P, PP):
    R_P = set()

    for Ji in J.difference(J_P):
        if JDICT[Ji][1] <= PP[1]:
            R_P.add(Ji)
    
    return R_P

def get_R_P(J, J_P, PP):
    R_P = set()    
    R_P = collect_released_jobs(J, J_P, PP)
    
    if len(R_P) == 0: # If set is empty
        all_r_min = [JDICT[Jx][0] for Jx in J.difference(J_P)]
        PP = (min(all_r_min), min(all_r_min))
        R_P = collect_released_jobs(J, J_P, PP)

    return R_P, PP

def ScheduleGraphConstructionAlgorithmROS(J, m):
    G = nx.DiGraph()
    BR = {Ji: INF for Ji in J}
    WR = {Ji: 0 for Ji in J}
    InitNode = StateROS([(0, 0) for core in range(m)], set(), dict(), (0, 0))
    G.add_node(0, state = InitNode)

    P = shortestPathFromSourceToLeaf(G)
    while len(P) - 1 < len(J):
        J_P = set([G[u][v]['job'] for u, v in zip(P[:-1], P[1:])])
        v_p = G.nodes[P[-1]]["state"]
        PP = v_p.PP

        A1 = v_p.A[0]
        A1_min = A1[0]
        A1_max = A1[1]

        A2 = v_p.A[1]
        A2_min = A2[0]
        A2_max = A2[1]

        ##### Modifications for ROS ######
        R_P, PP = get_R_P(J, J_P, PP)
        if len(R_P) == 1:
            PP = A1_min, A1_max
        ##################################

        for Ji in R_P:
            r_min, r_max, C_min, C_max, p_i = JDICT[Ji]
            all_Rx_max = [JDICT[Jx][1] for Jx in R_P]
            rx_max_higher_priority = [JDICT[Jx][1] for Jx in R_P if JDICT[Jx][4] < p_i] 
            ESTi = max(r_min, A1_min)

            t_wc = max(A1_max, min(all_Rx_max, default = INF))
            t_high = min(rx_max_higher_priority, default = INF)
            LSTi = min(t_wc, t_high - 1)

            if ESTi <= LSTi:
                print(f"Dispatched {Ji}")
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

                new_state = StateROS(new_A, new_X, new_FTI, PP)
                new_state_id = get_rand_node_id()
                G.add_node(new_state_id, state = new_state)
                G.add_edge(P[-1], new_state_id, job = Ji)

        # Next iteration
        P = shortestPathFromSourceToLeaf(G)
    
    return G


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("PATH")
    parser.add_argument("--ROS", action = "store_true")
    parser.add_argument("end_time", type = int)
    args = parser.parse_args()

    # Run algorithm with inputs
    INF = 100000
    # generate_jobs("tasks.csv", args.PATH, args.end_time, True)
    JDICT = convert_csv_to_dict(args.PATH)
    list_of_jobs = JDICT.keys()
    J = set(list_of_jobs)
    m = 2 # nr of cores

    if args.ROS:
        G = ScheduleGraphConstructionAlgorithmROS(J, m)
    else:
        G = ScheduleGraphConstructionAlgorithm(J, m)

    # Draw
    node_labels = {node: f"{data['state'].A}{data['state'].PP}" for node, data in G.nodes(data=True)}
    edge_labels = {(u, v): f"{data['job']}" for u, v, data in G.edges(data=True)}
    # pos = nx.nx_agraph.graphviz_layout(G, prog='dot', args='-Grankdir=LR')
    pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    nx.draw(G, pos, with_labels=False, node_color="lightblue", node_size = 300)
    nx.draw_networkx_labels(G, pos, labels=node_labels)
    nx.draw_networkx_edge_labels(G, pos, edge_labels)
    plt.show()