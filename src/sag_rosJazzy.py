import networkx as nx
import random


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
        NJ  An interval [NJ_min, NJ_max] that contains the earliest and the latest
            moments in time when there would be no job (NJ) in the wait_set
        NOJ An integer that represents the number of jobs that exist in the wait_set
    """

    def __init__(
        self,
        A: list[tuple],
        X: set,
        FTI: dict,
        PP: tuple[int, int],
        NJ: tuple[int, int],
        NOJ: int,
    ):
        self.A = A
        self.X = X
        self.FTI = FTI
        self.PP = PP
        self.NJ = NJ
        self.NOJ = NOJ

    def __repr__(self):
        return f"{self.A}"


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


def ScheduleGraphConstructionAlgorithmROS(J, m, JDICT, PRED):
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
        PP = v_p.PP
        NJ = v_p.NJ

        A1 = v_p.A[0]
        A1_min = A1[0]
        A1_max = A1[1]

        A2 = v_p.A[1]
        A2_min = A2[0]
        A2_max = A2[1]

        R_P = J.difference(J_P)
        print(f"Current state with PP:[{PP[0]}, {PP[1]}] and NJ: [{NJ[0]}, {NJ[1]}]")

        ################ ROS ##############
        # Certainly eligible jobs             r_max <= PP_max
        old_PP = PP
        C_E_P = set([Ji for Ji in R_P if JDICT[Ji][1] <= PP[1]])
        if len(C_E_P) == 0:
            PRT = min([JDICT[Jw][0] for Jw in R_P])
            CRT = min([JDICT[Jw][1] for Jw in R_P])
            pp_min = max(PRT, A1_min)
            pp_max = max(CRT, A1_max)
            PP = (pp_min, pp_max)
            print("wtf")

        # Certainly eligible jobs                r_max <= PP_max
        C_E_P = set([Ji for Ji in R_P if JDICT[Ji][1] <= PP[1]])
        # Possibly eligible jobs                r_min <= PP_max
        P_E_P = set([Ji for Ji in R_P if JDICT[Ji][0] <= PP[1]])

        # One of the two
        if PP[0] < PP[1]:
            E_P = P_E_P
        elif PP[0] == PP[1]:
            # The wait_set is C_E_P by now if all cores were busy and there were still sufficiently many jobs in the wait_set for all cores.
            # If the PP == A_m(previous state) then a PP certainly happened when all cores certainly became available,
            # so it means that there were not sufficient jobs in the wait_set to satisfy all cores.
            # Thus, we need to check whether the PP in this state was triggered by one of the cores which had no job to do.
            core_triggered_current_pp = False

            if parent_state != None:
                if parent_state.A[m - 1] == PP:
                    core_triggered_current_pp = True

            if core_triggered_current_pp:
                E_P = P_E_P  # Then it might be that potentially released job are brought to the wait_set
            else:
                E_P = C_E_P  # Then the PP was triggered beforehand, so the wait_set is NOT yet empty
        ####################################
        if old_PP == PP:
            print(f"The PP remained {old_PP}")
        else:
            print(f"The PP changed from {old_PP} to {PP}")
        print(f"Starting loop for C_E_P = {C_E_P}, P_E_P = {P_E_P}")
        for Ji in E_P:
            r_min, r_max, C_min, C_max, p_i = JDICT[Ji]

            ESTi = max(r_min, A1_min)
            t_wc = max(A1_max, min([JDICT[Jx][1] for Jx in E_P], default=INF))
            t_high = min(
                # r_max                                p_x
                [JDICT[Jx][1] for Jx in E_P if (JDICT[Jx][4] < p_i)],
                default=INF,
            )
            LSTi = min(t_wc, t_high - 1)

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
                print(
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
                aux_E_P = E_P.difference(set([Ji]))
                aux_R_P = R_P.difference(set([Ji]))

                if len(aux_E_P) > 0 and PP[0] == PP[1]:
                    new_PP = PP

                if len(aux_E_P) > 0 and PP[0] != PP[1]:
                    new_PP = (ESTi, LSTi)

                if len(aux_E_P) == 0:
                    new_PRT = (
                        min([JDICT[Jw][0] for Jw in aux_R_P])
                        if len(aux_R_P) > 0  # This is here just for the end of the SAG
                        else new_A[0][0]
                    )
                    new_CRT = (
                        min([JDICT[Jw][1] for Jw in aux_R_P])
                        if len(aux_R_P) > 0  # This is here just for the end of the SAG
                        else new_A[0][1]
                    )
                    new_pp_min = max(new_PRT, new_A[0][0])
                    new_pp_max = max(new_CRT, new_A[0][1])
                    new_PP = (new_pp_min, new_pp_max)

                print(
                    f"After dispatching {Ji} after state with PP: {PP}; the C_E_P is {C_E_P}, the P_E_P is {P_E_P} and the E_P is {E_P} | The new PP is {new_PP} because |aux_E_P| = {len(aux_E_P)}"
                )
                ###########################

                new_state = StateROS(new_A, new_X, new_FTI, new_PP, (0, 0), 0)
                new_state_id = get_rand_node_id()
                G.add_node(new_state_id, state=new_state)
                G.add_edge(P[-1], new_state_id, job=Ji)
                BR[Ji] = min(EFTi - r_min, BR[Ji])
                WR[Ji] = max(LFTi - r_max, WR[Ji])
            else:
                print(f"Cannot dispatch {Ji} because ESTi={ESTi} > LSTi={LSTi}")

        # Next iteration
        P = shortestPathFromSourceToLeaf(G)

    print("BR:", BR)
    print("WR:", WR)
    return G, BR, WR
