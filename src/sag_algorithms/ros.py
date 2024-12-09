import networkx as nx
import random
import logging
import tqdm
from sag_template import sag_algorithm


class StateROS:
    """
    A state in the Schedule Abstraction Graph.

    Attributes:
        A   List of core availability intervals
        X   Set of jobs that are being executed by one of the cores
        FTI Finish Time Intervals - a tuple [EFT, LFT] for each job in X
            EFT = Earliest Finish Time
            LFT = Latest Finish TIme
        PP  An interval [PP_min, PP_max] that contains the earliest and the latest
            moments in time when a polling point (PP) could happen
        NOJ An integer that represents the number of jobs that exist in the wait_set
    """

    def __init__(
        self,
        A: list[tuple],
        X: set,
        FTI: dict,
        PP: tuple[int, int],
        PP2: tuple[int, int],
        NOJ: int,
    ):
        self.A = A
        self.X = X
        self.FTI = FTI
        self.PP = PP
        self.PP2 = PP2
        self.NOJ = NOJ

    def __repr__(self):
        return f"{self.A}{self.PP}{self.PP2}"


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


@sag_algorithm
def ScheduleGraphConstructionAlgorithmROS(
    J: set,
    m: int,
    JDICT: dict,
    PRED: dict,
    logger=logging.Logger("SAGPY", logging.CRITICAL),
) -> tuple[nx.DiGraph, dict, dict]:
    bar = tqdm.tqdm(desc="[SAGPY-ROS] Progress")  # Progress bar
    INF = 100000  # Representation of infinity
    G = nx.DiGraph()
    BR = {Ji: INF for Ji in J}
    WR = {Ji: 0 for Ji in J}
    InitNode = StateROS([(0, 0) for core in range(m)], set(), dict(), (0, 0), (0, 0), 0)
    G.add_node(0, state=InitNode)

    P = shortestPathFromSourceToLeaf(G)
    while len(P) - 1 < len(J):
        J_P = set([G[u][v]["job"] for u, v in zip(P[:-1], P[1:])])
        v_p = G.nodes[P[-1]]["state"]
        parent_state = G.nodes[P[-2]]["state"] if v_p != InitNode else None
        last_dispatched_job = G[P[-2]][P[-1]]["job"] if v_p != InitNode else ""
        PP = v_p.PP
        PP2 = v_p.PP2
        A = v_p.A

        A1 = A[0]
        A1_min = A1[0]
        A1_max = A1[1]

        R_P = J.difference(J_P)
        ################ ROS ##############
        old_PP = PP
        C_E_P = set([Ji for Ji in R_P if JDICT[Ji]["r_max"] <= PP[1]])
        if len(C_E_P) == 0:
            PRT = min([JDICT[Jw]["r_min"] for Jw in R_P])
            CRT = min([JDICT[Jw]["r_max"] for Jw in R_P])
            pp_min = max(PRT, A1_min)
            pp_max = max(CRT, A1_max)
            PP = (pp_min, pp_max)

        if old_PP != PP:
            logger.debug(
                f"The PP changed from {old_PP} to {PP}; we are in state with A = {A}"
            )
        else:
            logger.debug(f"The PP is the same, i.e. {PP}; we are in state with A = {A}")

        E_P = set()  # Set that contains the eligible jobs for dispatch from this state.
        # Certainly eligible jobs                r_max <= PP_max
        C_E_P = set([Ji for Ji in R_P if JDICT[Ji]["r_max"] <= PP[1]])
        # Possibly eligible jobs                r_min <= PP_max
        P_E_P = set([Ji for Ji in R_P if JDICT[Ji]["r_min"] <= PP[1]])
        P_LP_E = set()

        # One of the two
        if (
            PP[0] < PP[1]
        ):  # Then it's uncertain when a polling point happened, so we must consider all jobs that *could* be in the wait_set.
            E_P = P_E_P
        elif PP[0] == PP[1]:  # PP definitely happened at PP[0] == PP[1]
            E_P = C_E_P

            """
            The wait_set is C_E_P by now if all cores were busy and there were still sufficiently many jobs in the wait_set for all cores.
            If the PP == A_m(previous state) then a PP certainly happened when all cores certainly became available,
            so it means that there were not sufficient jobs in the wait_set to satisfy all cores.
            Thus, we need to check whether the PP in this state was triggered by one of the cores which had no job to do.
            """
            if parent_state != None:
                if parent_state.A[m - 1] == PP:
                    E_P = P_E_P

            """
            At this point a PP certainly happened sometime in the past, but we don't know what jobs are certainly in the wait_set.
            However, since a PP certainly happened then the last released job was the highest priority job in the wait_set.
            So the job on the graph-edge that brought us to this current state, was certainly the highest priority job in the wait_set.
            Then, from this state we cannot dispatch jobs with a higher priority than the one just dispatched, because they weren't added to the wait_set.
            [Somehow explain why we use P_E_P when all jobs in P_E_P are lower priority than last dispatched job and
             v_p(PP) == v_p'(PP) (i.e. the PP is unchanged)]
            """
            if parent_state != None:
                if parent_state.PP != PP:
                    all_possible_jobs_lower_priority_than_last_job = True

                    for Jv in P_E_P:
                        if JDICT[Jv]["p"] < JDICT[last_dispatched_job]["p"]:
                            all_possible_jobs_lower_priority_than_last_job = False

                    if all_possible_jobs_lower_priority_than_last_job == True:
                        E_P = P_E_P
                elif parent_state.PP == PP:
                    if PP == parent_state.A[0]:
                        all_possible_jobs_lower_priority_than_last_job = True

                        for Jv in P_E_P:
                            if JDICT[Jv]["p"] < JDICT[last_dispatched_job]["p"]:
                                all_possible_jobs_lower_priority_than_last_job = False

                        if all_possible_jobs_lower_priority_than_last_job == True:
                            E_P = P_E_P

        if parent_state != None:
            if parent_state.PP == PP2 and PP2[0] == PP2[1]:
                P_LP_E = set(
                    [
                        Jk
                        for Jk in P_E_P
                        if JDICT[Jk]["p"] > JDICT[last_dispatched_job]["p"]
                    ]
                )
        ####################################

        logger.debug(
            f"Current state with A: {A}, PP:[{PP[0]}, {PP[1]}] and PP2: [{PP2[0]}, {PP2[1]}]; after dispatching {last_dispatched_job}."
        )
        logger.debug(
            f"We have E_P={E_P}, P_E_P={P_E_P}, C_E_P={C_E_P}, P_LP_E={P_LP_E}"
        )

        for Ji in E_P:
            r_min = JDICT[Ji]["r_min"]
            r_max = JDICT[Ji]["r_max"]
            C_min = JDICT[Ji]["C_min"]
            C_max = JDICT[Ji]["C_max"]
            p_i = JDICT[Ji]["p"]

            ESTi = max(r_min, A1_min)
            LSTi = 0

            if Ji not in P_LP_E:
                if (PP[0] == PP[1]) and (Ji in C_E_P):
                    t_wc = max(
                        A1_max, min([JDICT[Jx]["r_max"] for Jx in C_E_P], default=INF)
                    )
                    t_high = min(
                        [JDICT[Jx]["r_max"] for Jx in C_E_P if (JDICT[Jx]["p"] < p_i)],
                        default=INF,
                    )
                else:
                    t_wc = max(
                        A1_max, min([JDICT[Jx]["r_max"] for Jx in E_P], default=INF)
                    )
                    t_high = min(
                        [JDICT[Jx]["r_max"] for Jx in E_P if (JDICT[Jx]["p"] < p_i)],
                        default=INF,
                    )
            else:
                t_wc = max(
                    A1_max, min([JDICT[Jx]["r_max"] for Jx in P_LP_E], default=INF)
                )
                t_high = min(
                    [JDICT[Jx]["r_max"] for Jx in P_LP_E if (JDICT[Jx]["p"] < p_i)],
                    default=INF,
                )

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
                PA.sort()
                CA.sort()
                logger.debug(
                    f"Dispatched {Ji} with ESTi = {ESTi} and LSTi = {LSTi}; EFTi = {EFTi} and LFTi = {LFTi}"
                )

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
                new_PP = PP
                new_PP2 = (-1, -1)
                aux_E_P = (
                    E_P.difference(set([Ji]))
                    if Ji not in P_LP_E
                    else P_LP_E.difference(set[Ji])
                )
                aux_R_P = R_P.difference(set([Ji]))

                if len(aux_E_P) > 0 and PP[0] == PP[1]:
                    new_PP = PP

                    # if Ji not in P_LP_E:
                    #     aux_P_LP_E = set(
                    #         [Jk for Jk in P_E_P if JDICT[Jk][4] > JDICT[Ji][4]]
                    #     )

                    #     if len(aux_P_LP_E) > 0:
                    #         new_PP2 = PP

                if len(aux_E_P) > 0 and PP[0] != PP[1]:
                    new_PP = (ESTi, LSTi)

                if len(aux_E_P) == 0:
                    new_PRT = (
                        min([JDICT[Jw]["r_min"] for Jw in aux_R_P])
                        if len(aux_R_P) > 0  # This is here just for the end of the SAG
                        else new_A[0][0]
                    )
                    new_CRT = (
                        min([JDICT[Jw]["r_max"] for Jw in aux_R_P])
                        if len(aux_R_P) > 0  # This is here just for the end of the SAG
                        else new_A[0][1]
                    )
                    new_pp_min = max(new_PRT, new_A[0][0])
                    new_pp_max = max(new_CRT, new_A[0][1])
                    new_PP = (new_pp_min, new_pp_max)

                    aux_P_LP_E = set(
                        [Jk for Jk in P_E_P if JDICT[Jk]["p"] > JDICT[Ji]["p"]]
                    )
                    if len(aux_P_LP_E) > 0:
                        new_PP2 = PP

                logger.debug(
                    f"After dispatching {Ji} after state with PP: {PP}; the C_E_P is {C_E_P}, the P_E_P is {P_E_P} and the E_P is {E_P} | The new PP is {new_PP} because |aux_E_P| = {len(aux_E_P)}"
                )

                new_state = StateROS(new_A, new_X, new_FTI, new_PP, new_PP2, 0)
                new_state_id = get_rand_node_id()
                G.add_node(new_state_id, state=new_state)
                G.add_edge(P[-1], new_state_id, job=Ji)
                ###########################
                BR[Ji] = min(EFTi - r_min, BR[Ji])
                WR[Ji] = max(LFTi - r_max, WR[Ji])
            else:
                logger.debug(
                    f"Cannot dispatch {Ji} after state with A: {A}, PP:[{PP[0]}, {PP[1]}] and PP2: [{PP2[0]}, {PP2[1]}], because ESTi={ESTi} > LSTi={LSTi}"
                )

        # Next iteration
        P = shortestPathFromSourceToLeaf(G)
        bar.update(1)

    logger.debug(f"BR: {BR}")
    logger.debug(f"WR: {WR}")
    bar.close()

    return G, BR, WR
