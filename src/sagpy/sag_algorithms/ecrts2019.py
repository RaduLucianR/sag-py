import networkx as nx
import random
import logging
from sag_template import sag_algorithm


######## Utility functions #######
def get_rand_node_id():
    """
    Acts like a hash function for node IDs.
    It just spits random integers between 10^6 to 10^7 - 1.
    """

    n = 6
    lower_bound = 10 ** (n - 1)
    upper_bound = 10**n - 1
    return random.randint(lower_bound, upper_bound)


def shortestPathFromSourceToLeaf(G):
    leaves = [node for node in G.nodes if G.out_degree(node) == 0]
    shortest_paths = []

    for leaf in leaves:
        sp = nx.shortest_path(G, source=0, target=leaf)
        shortest_paths.append(sp)

    return min(shortest_paths, key=len)


class State:
    """
    A state in the Schedule Abstraction Graph.

    Attributes:
        A   List of core availability intervals
        X   Set of jobs that are being executed by one of the cores
        FTI Finish Time Intervals - a tuple [EFT, LFT] for each job in X
            EFT = Earliest Finish Time
            LFT = Latest Finish TIme
    """

    def __init__(self, A: list[tuple], X: set, FTI: dict):
        self.A = A
        self.X = X
        self.FTI = FTI

    def __repr__(self):
        return f"{self.A}"


@sag_algorithm
def ScheduleGraphConstructionAlgorithm(
    J: set,
    m: int,
    JDICT: dict,
    PRED: dict,
    logger=logging.Logger("SAGPY", logging.CRITICAL),
) -> tuple[nx.DiGraph, dict, dict]:
    INF = 100000  # Representation for infinity
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
                        # TODO: Check if CA.index(LFTc) is correct here
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

    logger.debug(f"BR: {BR}")
    logger.debug(f"WR: {WR}")

    return G, BR, WR
