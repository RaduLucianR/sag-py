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
    merge=False
) -> tuple[nx.DiGraph, dict, dict]:
    print(f"m={m}")
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
            
        def R_min(Ja):
            ra_min = JDICT[Ja]["r_min"]
            return max(ra_min, max([EFT_star(Jy) for Jy in PRED[Ja]], default=0))

        def LFT_star(Jx):
            if Jx in X:
                return FTI[Jx][1]  # LFT_x(v_p)
            else:
                return WR[Jx]

        

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

        # Minimum Wait Set i.e. WS with minimum number of jobs in this state
        mWS = set([Jy for Jy in LP if R_max(Jy) <= PP[0]])
        # Maximum Wait Set i.e. WS with maximum number of jobs in this state
        MWS = set([Jy for Jy in LP if (R_min(Jy) <= PP[1])])

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

            elif Ji in R_P and len(mWS) == 0:
                if is_eligible(R_P) is True:
                    dispatch = True
                    which_WS = R_P
            
            if last_dispatched_job == "J3_16":
                    breakpoint()

            if dispatch is True:
                # breakpoint()
                

                def create_new_state(EST_new, LST_new, PP_new):
                    EFT_new = EST_new + C_min
                    LFT_new = LST_new + C_max

                    PA = [max(EST_new, A[idx][0]) for idx in range(1, m)]
                    CA = [max(EST_new, A[idx][1]) for idx in range(1, m)]

                    PA.append(EFT_new)
                    CA.append(LFT_new)

                    PA.sort()
                    CA.sort()

                    A_new = [(0, 0) for i in range(m)]
                    for i in range(m):
                        A_new[i] = (PA[i], CA[i])

                    X_new = set()
                    for Jx in v_p.X:
                        EFTx = v_p.FTI[Jx][0]
                        if LST_new <= EFTx:
                            X_new.add(Jx)
                    X_new.add(Ji)

                    FTI_new = dict()
                    for Jx in X_new:
                        if Jx in v_p.FTI:
                            FTI_new[Jx] = v_p.FTI[Jx]
                    FTI_new[Ji] = (EFT_new, LFT_new)

                    new_state = StateROS(A_new, X_new, FTI_new, PP_new)
                    new_state_id = get_rand_node_id()
                    G.add_node(new_state_id, state=new_state)
                    G.add_edge(P[-1], new_state_id, job=Ji)

                    # BR[Ji] = min(EFT_new, BR[Ji])
                    # WR[Ji] = max(LFT_new, WR[Ji])
                    BR[Ji] = EFT_new
                    WR[Ji] = LFT_new

                    if merge == True:
                        vp_prime = G.nodes[new_state_id]["state"]
                        J_P_prime = J_P.union(set([Ji]))
                        leaves = [node for node in G.nodes if G.out_degree(node) == 0 and node != new_state_id]
                        paths_to_leaves = []
                        for leaf in leaves:
                            pf = nx.shortest_path(G, source=0, target=leaf)
                            paths_to_leaves.append(pf)
                        # breakpoint()
                        for Q in paths_to_leaves:
                            ####### Info from v on path Q ######
                            J_Q = set([G[u][v]["job"] for u, v in zip(Q[:-1], Q[1:])])
                            v_q = G.nodes[Q[-1]]["state"]
                            A_vq = v_q.A
                            PP_vq = v_q.PP
                            X_vq = v_q.X
                            FTI_vq = v_q.FTI
                            # breakpoint()
                            ###### Merge condition ######
                            if J_Q != J_P_prime:
                                continue
                            
                            all_A_intersect = True
                            for x in range(m):
                                if not (max(vp_prime.A[x][0], A_vq[x][0]) <= min(vp_prime.A[x][1], A_vq[x][1])):
                                    all_A_intersect = False
                                    break
                            if all_A_intersect == False:
                                continue

                            if not (max(vp_prime.PP[0], PP_vq[0]) <= min(vp_prime.PP[1], PP_vq[1])):
                                continue
                            
                            ####### Widen intervals #########
                            for x in range(m):
                                widened_A = (min(vp_prime.A[x][0], A_vq[x][0]), max(vp_prime.A[x][1], A_vq[x][1]))
                                vp_prime.A[x] = widened_A
                            
                            widened_PP = (min(vp_prime.PP[0], PP_vq[0]), max(vp_prime.PP[1], PP_vq[1]))
                            vp_prime.PP = widened_PP

                            vp_prime.X = vp_prime.X.intersection(X_vq)

                            for k in vp_prime.X:
                                widened_FT = (min(vp_prime.FTI[k][0], FTI_vq[k][0]), max(vp_prime.FTI[k][1], FTI_vq[k][1]))
                                vp_prime.FTI[k] = widened_FT
                            
                            ####### Redirect incoming edges from v_q to v_p' #######
                            v_q_id = Q[-1]
                            in_edges = list(G.in_edges(v_q_id, data=True))
                            for source, target, data in in_edges:
                                # Add the edge with the same attributes.
                                G.add_edge(source, new_state_id, **data)
                            
                            ####### Remove v_q and all its adjacent edges ########
                            G.remove_node(v_q_id)

                ESTi, LSTi, t_high = get_ST(which_WS)
                EFTi = ESTi + C_min
                LFTi = LSTi + C_max

                # if Ji == "J5_25":
                # if last_dispatched_job == "J3_16":
                #     breakpoint()

                # if LFTi == 6:
                #     breakpoint()

                # if LFTi > d_i:  # Check if this job doesn't have a deadline miss
                #     # If it misses the deadline, then the job set is NOT schedulable
                #     # So no need to check the rest of the paths, just return
                #     logger.info("Not schedulable!")
                #     return G, BR, WR

                if parent_state != None:
                    if Ji in MWS:
                        new_PP = PP
                        create_new_state(ESTi, LSTi, tuple(new_PP))
                    if (Ji in MWS) and (len(mWS) == 0) and is_eligible(R_P):
                        EST_R, LST_R, t_h = get_ST(R_P)
                        create_new_state(EST_R, LST_R, (EST_R, LST_R))

                    # if Ji in R_P but Ji *not* in MWS AND GWS EMPTY
                    if (Ji not in MWS) and (len(mWS) == 0):
                        # new_PP[0] = ESTi
                        # new_PP[1] = LSTi
                        create_new_state(ESTi, LSTi, (ESTi, LSTi))
                else:
                    # new_PP = PP
                    create_new_state(ESTi, LSTi, (ESTi, LSTi))

        # Next iteration
        P = shortestPathFromSourceToLeaf(G)
        # breakpoint()
        if len(G.nodes) % 10 == 0:
            logger.info(f"The graph has {len(G.nodes)} nodes")
        # if len(P) == 8:
        #     return G, BR, WR

    # logger.info(f"BR: {BR}")
    # logger.info(f"WR: {WR}")

    return G, BR, WR
