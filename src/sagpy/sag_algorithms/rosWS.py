import networkx as nx
import random
import logging
from typing import Literal
from sagpy.sag_template import sag_algorithm
from itertools import chain, combinations

SET_IDs = set()


######## Utility functions #######
def get_rand_node_id():
    """
    Acts like a hash function for node IDs.
    It just spits random integers between 10^6 to 10^7 - 1.
    """

    n = 6
    lower_bound = 10 ** (n - 1)
    upper_bound = 10**n - 1
    id = random.randint(lower_bound, upper_bound)

    while id in SET_IDs:
        id = random.randint(lower_bound, upper_bound)

    SET_IDs.add(id)

    return id


def shortestPathFromSourceToLeaf(G):
    leaves = [node for node in G.nodes if G.out_degree(node) == 0]
    shortest_paths = []

    for leaf in leaves:
        sp = nx.shortest_path(G, source=0, target=leaf)
        shortest_paths.append(sp)

    return min(shortest_paths, key=len)


def subsets_with_constraint(X, C):
    # Ensure C is a subset of X
    if not C.issubset(X):
        raise ValueError("C must be a subset of X")

    # Compute X' = X \ C
    X_prime = X - C

    # Generate all subsets of X'
    def all_subsets(iterable):
        "Returns all subsets of the iterable"
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

    # Add C to each subset of X'
    result = [set(subset).union(C) for subset in all_subsets(X_prime)]
    return result


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
    INF = 10000000000000000000000000  # Representation for infinity
    G = nx.DiGraph()
    BR = {Ji: INF for Ji in J}
    WR = {Ji: 0 for Ji in J}
    LFT_J = {Ji: 0 for Ji in J}
    SCHED = True
    logger.info(f"Starting analysis for {len(J)} jobs")
    ####################################

    ############# Init ##############
    ERT0 = min([JDICT[Jy]["r_min"] for Jy in J])
    LRT0 = min([JDICT[Jy]["r_max"] for Jy in J])
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
            d_i = JDICT[Ji]["d"]
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
            BWS = set([Ji]).union(mWS)

            if Ji in MWS:
                if is_eligible(BWS) is True:
                    dispatch = True
                    which_WS = BWS
                # max_LST = 0
                # all_WS = subsets_with_constraint(MWS, set([Ji]).union(mWS))

                # for WS in all_WS:
                #     if is_eligible(WS) is True:
                #         dispatch = True
                #         lst = get_ST(WS)[1]

                #         if lst > max_LST:
                #             max_LST = lst
                #             which_WS = WS

            elif Ji in R_P and len(mWS) == 0:
                if is_eligible(R_P) is True:
                    dispatch = True
                    which_WS = R_P

            if dispatch is True:
                ESTi, LSTi, t_high = get_ST(which_WS)
                EFTi = ESTi + C_min
                LFTi = LSTi + C_max

                # if LFTi == 6:
                #     breakpoint()

                if LFTi > d_i:  # Check if this job doesn't have a deadline miss
                    # If it misses the deadline, then the job set is NOT schedulable
                    # So no need to check the rest of the paths, just return
                    logger.info("Not schedulable!")
                    return G, BR, WR, False

                PA = [max(ESTi, A[idx][0]) for idx in range(1, m)]
                CA = [max(ESTi, A[idx][1]) for idx in range(1, m)]

                PA.append(EFTi)
                CA.append(LFTi)

                # for Jc in X.intersection(PRED[Ji]):
                #     LFTc = FTI[Jc][1]
                #     if LSTi < LFTc and LFTc in CA:
                #         # TODO: Check if CA.index(LFTc) is correct here
                #         CA[CA.index(LFTc)] = LSTi

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
                new_A_2 = [(0, 0) for i in range(m)]
                two_states = False

                if parent_state != None:
                    if Ji in MWS:
                        new_PP = PP
                    if (Ji in MWS) and (len(mWS) == 0) and is_eligible(R_P):
                        EST, LST, t_h = get_ST(R_P)
                        EFT = EST + C_min
                        LFT = LST + C_max
                        new_PP2 = (EST, LST)

                        PA = [max(ESTi, A[idx][0]) for idx in range(1, m)]
                        CA = [max(ESTi, A[idx][1]) for idx in range(1, m)]

                        PA.append(EFT)
                        CA.append(LFT)

                        PA.sort()
                        CA.sort()

                        for i in range(m):
                            new_A_2[i] = (PA[i], CA[i])

                        two_states = True
                    if Ji not in MWS:  # if Ji in R_P but Ji *not* in MWS:
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

                    new_state = StateROS(new_A_2, new_X, new_FTI, new_PP2)
                    new_state_id = get_rand_node_id()
                    G.add_node(new_state_id, state=new_state)
                    G.add_edge(P[-1], new_state_id, job=Ji)

                BR[Ji] = min(EFTi - r_min, BR[Ji])
                WR[Ji] = max(LFTi - r_min, WR[Ji])
                # logger.info(f"job {Ji} with ESTi = {ESTi} and LSTi = {LSTi}")

        # Next iteration
        P = shortestPathFromSourceToLeaf(G)
        # breakpoint()
        if len(G.nodes) % 10 == 0:
            logger.info(f"The graph has {len(G.nodes)} nodes")

    # logger.info(f"BR: {BR}")
    # logger.info(f"WR: {WR}")

    return G, BR, WR, True
