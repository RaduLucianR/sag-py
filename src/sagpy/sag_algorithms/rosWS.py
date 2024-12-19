import networkx as nx
import random
import logging
from typing import Literal
from sagpy.sag_template import sag_algorithm


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


class StateROS:
    """
    A state in the Schedule Abstraction Graph.

    Attributes:
        A   List of core availability intervals
        X   Set of jobs that are being executed by one of the cores
        FTI Finish Time Intervals - a tuple [EFT, LFT] for each job in X
            EFT = Earliest Finish Time
            LFT = Latest Finish TIme
    """

    def __init__(self, A: list[tuple], X: set, FTI: dict, PP: tuple[int, int]):
        self.A = A
        self.X = X
        self.FTI = FTI
        self.PP = PP

    def __repr__(self):
        return f"{self.A}{self.PP}"


@sag_algorithm
def ScheduleGraphConstructionAlgorithm(
    J: set,
    m: int,
    JDICT: dict,
    PRED: dict,
    logger=logging.Logger("SAGPY", logging.CRITICAL),
) -> tuple[nx.DiGraph, dict, dict]:
    ############## Init ################
    INF = 100000  # Representation for infinity
    G = nx.DiGraph()
    BR = {Ji: INF for Ji in J}
    WR = {Ji: 0 for Ji in J}
    ####################################

    #######################
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

    def R_min(Ja):
        ra_min = JDICT[Ja]["r_min"]
        return max(ra_min, max([EFT_star(Jy) for Jy in PRED[Ja]], default=0))

    def R_max(Ja):
        ra_max = JDICT[Ja]["r_max"]
        return max(ra_max, max([LFT_star(Jy) for Jy in PRED[Ja]], default=0))

    ########################

    ############# Init ##############
    ERT0 = min([R_min(Jy) for Jy in J])
    LRT0 = min([R_max(Jy) for Jy in J])
    PP0 = (ERT0, LRT0)
    InitNode = StateROS([(0, 0) for core in range(m)], set(), dict(), PP0)
    G.add_node(0, state=InitNode)
    ##################################

    P = shortestPathFromSourceToLeaf(G)
    while len(P) - 1 < len(J):
        J_P = set([G[u][v]["job"] for u, v in zip(P[:-1], P[1:])])
        R_P = set([job for job in J.difference(J_P) if PRED[job].issubset(J_P)])
        v_p = G.nodes[P[-1]]["state"]
        parent_state = G.nodes[P[-2]]["state"] if v_p != InitNode else None
        last_dispatched_job = G[P[-2]][P[-1]]["job"] if v_p != InitNode else ""
        A = v_p.A
        X = v_p.X
        FTI = v_p.FTI
        PP = v_p.PP  # previous polling point
        A1 = A[0]
        A1_min = A1[0]
        A1_max = A1[1]

        #### ROS ####
        # All jobs that have lower priority than the last dispatched job
        LP = (
            set([Jy for Jy in R_P if JDICT[Jy]["p"] > JDICT[last_dispatched_job]["p"]])
            if parent_state != None
            else set()
        )
        # Maximum Wait Set i.e. WS with maximum number of jobs in this state
        MWS = set([Jy for Jy in LP if R_min(Jy) <= PP[1]])
        # Minimum Wait Set i.e. WS with minimum number of jobs in this state
        mWS = set([Jy for Jy in LP if R_max(Jy) <= PP[0]])

        for Ji in R_P:
            r_min = JDICT[Ji]["r_min"]
            r_max = JDICT[Ji]["r_max"]
            C_min = JDICT[Ji]["C_min"]
            C_max = JDICT[Ji]["C_max"]
            p_i = JDICT[Ji]["p"]

            ########### AUX FUNCTIONS ##############
            def th(Jx):
                rx_max = JDICT[Jx]["r_max"]
                return max(
                    rx_max,
                    max(
                        [LFT_star(Jy) for Jy in PRED[Jx].difference(PRED[Ji])],
                        default=0,
                    ),
                )

            def is_eligible(WS: set):
                ESTi = max(R_min(Ji), A1_min)
                t_wc = max(A1_max, min([R_max(Jb) for Jb in WS], default=INF))
                t_high = min([th(Jz) for Jz in WS if JDICT[Jz]["p"] < p_i], default=INF)
                LSTi = min(t_wc, t_high - 1)

                return ESTi <= LSTi

            def get_ST(WS: set):
                ESTi = max(R_min(Ji), A1_min)
                t_wc = max(A1_max, min([R_max(Jb) for Jb in WS], default=INF))
                t_high = min([th(Jz) for Jz in WS if JDICT[Jz]["p"] < p_i], default=INF)
                LSTi = min(t_wc, t_high - 1)

                return ESTi, LSTi, t_high

            ########################################

            dispatch = False
            which_WS = set()

            if len(mWS) > 0:
                if Ji in mWS:
                    if is_eligible(mWS) is True:
                        dispatch = True
                        which_WS = mWS
                elif Ji in MWS:
                    if is_eligible(MWS) is True:
                        dispatch = True
                        which_WS = MWS
                    elif is_eligible(set([Ji]).union(mWS)):
                        dispatch = True
                        which_WS = set([Ji]).union(mWS)
            else:
                if Ji in MWS:
                    if is_eligible(MWS) is True:
                        dispatch = True
                        which_WS = MWS
                    elif is_eligible(set([Ji]).union(mWS)):
                        dispatch = True
                        which_WS = set([Ji]).union(mWS)
                else:
                    if is_eligible(R_P) is True:
                        dispatch = True
                        which_WS = R_P

            if dispatch is True:
                ESTi, LSTi, t_high = get_ST(which_WS)
                EFTi = ESTi + C_min
                LFTi = LSTi + C_max
                PA = [max(ESTi, A[idx][0]) for idx in range(1, m)]
                CA = [max(ESTi, A[idx][1]) for idx in range(1, m)]

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

                new_PP = [0, 0]
                new_PP2 = [0, 0]
                two_states = False

                if parent_state != None:
                    # Ji is higher priority than last dispatched job
                    if p_i < JDICT[last_dispatched_job]["p"]:
                        new_PP[0] = ESTi
                        new_PP[1] = LSTi
                        # LRT = min([R_max(Jy) for Jy in R_P])
                        # if LRT <= R_max(Ji):
                        #     if LRT > A1_max:
                        #         new_PP[1] = min(LRT, t_high - 1)
                        #     else:  # if LRT <= A1_max
                        #         new_PP[1] = LRT
                        # else:  # if LRT > R_max
                        #     new_PP[1] = max(A1_max, R_max(Ji))
                    else:  # if p_i > p_L i.e. Ji is lower priority than last dispatched job
                        if Ji in mWS:
                            new_PP = PP  # doesn't change
                        elif Ji in MWS:
                            if len(mWS) > 0:
                                new_PP = PP  # doesn't change
                            else:  # mWS is empty
                                diff = R_P.difference(MWS.difference(set([Ji])))

                                max_p = max(JDICT[Jy]["p"] for Jy in diff)
                                if p_i == max_p:
                                    new_PP = PP
                                    new_PP2 = (ESTi, LSTi)
                                    two_states = True
                                else:
                                    new_PP = PP
                        else:  # if Ji in R_P but Ji *not* in MWS:
                            new_PP[0] = ESTi
                            new_PP[1] = LSTi
                else:
                    new_PP = PP

                new_PP = tuple(new_PP)

                if two_states is False:
                    new_state = StateROS(new_A, new_X, new_FTI, new_PP)
                    new_state_id = get_rand_node_id()
                    G.add_node(new_state_id, state=new_state)
                    G.add_edge(P[-1], new_state_id, job=Ji)
                else:
                    new_state = StateROS(new_A, new_X, new_FTI, new_PP)
                    new_state_id = get_rand_node_id()
                    G.add_node(new_state_id, state=new_state)
                    G.add_edge(P[-1], new_state_id, job=Ji)

                    new_state = StateROS(new_A, new_X, new_FTI, new_PP2)
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
