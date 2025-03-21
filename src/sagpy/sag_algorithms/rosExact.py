import networkx as nx
import random
import logging
from sagpy.sag_template import sag_algorithm
import copy
from types import UnionType
from functools import lru_cache
import time
import csv

######## Utility functions #######
def extract_single_element(s):
    if not s:  # the set is empty
        return ""
    if len(s) == 1:
        return next(iter(s))
    raise ValueError("The set has more than one element")

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

############### State ##############
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

    def __init__(
        self,
        A: list[tuple],
        PP: tuple[int, int],
        SP: dict,
        GW: set,
        FT: dict,
        FJ: set
    ):
        self.A = A
        self.PP = PP
        self.SP = SP
        self.GW = GW
        self.FT = FT
        self.FJ = FJ

    def __repr__(self):
        sp_str = "\n".join(
            # f"{j}: {self.SP[j]['succ']}, {self.SP[j]['siblings']}, {self.SP[j]['captured']}"
            f"{j}: [{self.SP[j]['EFT']}, {self.SP[j]['LFT']}] {self.SP[j]['succ']}, {self.SP[j]['siblings']}, {self.SP[j]['captured']}"
            for j in self.SP
        )
        # return f"{self.A}"
        # return f"{self.A} {self.PP}\n{sp_str}"

        return f"{self.A} {self.PP}"

################### Algorithm #################
@sag_algorithm
def ScheduleGraphConstructionAlgorithm(
    J: set,
    m: int,
    JDICT: dict,
    PRED: dict,
    logger=logging.Logger("SAGPY", logging.CRITICAL),
    merge = False
) -> tuple[nx.DiGraph, dict, dict]:
    def succ(j: str):
        succ_set = set()
        for k in J:
            if j in PRED[k]:
                succ_set.add(k)
        return succ_set

    INF = 10000000000  # Representation for infinity
    G = nx.DiGraph()
    BR = {Ji: INF for Ji in J}
    WR = {Ji: 0 for Ji in J}

    logger.info(f"HOW MANY JOBS: {len(J)}")

    ERT0 = min([JDICT[Jy]["r_min"] for Jy in J])
    LRT0 = min([JDICT[Jy]["r_max"] for Jy in J])
    PP1 = (ERT0, LRT0)
    GW1 = set([j for j in J if len(PRED[j]) == 0 and JDICT[j]["r_max"] <= PP1[0]]) 
    InitNode = State([(0, 0) for core in range(m)], PP1, dict(), GW1, dict(), set())
    G.add_node(0, state=InitNode)

    P = shortestPathFromSourceToLeaf(G)
    counter = 0
    while len(P) - 1 < len(J):
        counter += 1
        J_P = set([G[u][v]["job"] for u, v in zip(P[:-1], P[1:])])
        dispatch_order = [G[u][v]["job"] for u, v in zip(P[:-1], P[1:])]
        not_dispatched_jobs = J.difference(J_P)
        v_p = G.nodes[P[-1]]["state"]
        parent_state = G.nodes[P[-2]]["state"] if v_p != InitNode else None
        last_dispatched_job = G[P[-2]][P[-1]]["job"] if v_p != InitNode else ""

        A = v_p.A
        PP_old = v_p.PP
        SP: dict[tuple[set, int, int, bool, bool]] = v_p.SP
        GW: set = v_p.GW
        FT = v_p.FT
        FJ = v_p.FJ

        A1 = A[0]
        A1_min = A1[0]
        A1_max = A1[1]

        def certainly_in_GWS():
            def x_th_largest(S: set, x: int):
                if x < 1 or x > len(S):
                    raise ValueError("x must be between 1 and the number of elements in S")
                
                sorted_elements = sorted(S, key=lambda j: FT[j][1], reverse=True)
                return FT[sorted_elements[x - 1]][1]

            B = set([j for j in J_P if FT[j][0] < A1_max and FT[j][1] > A1_min]).difference(FJ)
            APP = set([j for j in J_P if FT[j][0] >= A1_max]) # jobs that finish After Polling Point
            CFB = dict() # jobs that Certainly Finish Before job x

            for j in B:
                # Suppose j triggers the polling point
                CFB[j] = set([j])

                for k in B.difference(set([j])):
                    if FT[k][1] < FT[j][0]:
                        CFB[j].add(k)
                        continue
                    else:
                        if len(APP) < m - 1:
                            if FT[k][1] < x_th_largest(B.difference(set([j])), m - 1):
                                CFB[j].add(k)
                        else:
                            continue
            
            preds = set([j for j in SP if FT[j][1] <= A1_min]).union(set.intersection(*CFB.values())) if CFB else set([j for j in SP if FT[j][1] <= A1_min])
            D = {e for j in SP if FT[j][1] <= A1_min for e in SP[j]["succ"]}
            succ_CFB = (
                {e for j in set.intersection(*CFB.values()) 
                for e in SP.get(j, {}).get("succ", set())}
                if CFB else set()
            )
            succs = succ_CFB.union(D)
            
            # if last_dispatched_job == "J4_20":
            # breakpoint()

            # all_possible_WS = {frozenset(s) for s in CFB.values()}
            # print(last_dispatched_job)
            # print(GW)
            # all_possible_WS = {e for s in CFB.values() for j in s for e in SP.get(j, {}).get("succ", set())}
            # breakpoint()

            all_possible_WS = set() ########## TODO: Calculate all possible WS properly, i.e., PWS

            return all_possible_WS, preds, succs
        
        #########################################
        all_possible_WS, preds, succs = set(), set(), set()
        if len(GW) == 0:
            all_possible_WS, preds, succs = certainly_in_GWS()
        #########################################

        def GWS(pp: tuple[int, int], sp, new_pp = False):
            pp_min, pp_max = pp

            certainly_ready_timer_jobs = set([j for j in not_dispatched_jobs 
                                              if len(PRED[j]) == 0 and JDICT[j]["r_max"] <= pp_min])

            certainly_ready_sub_jobs = set(s for j in sp.keys() 
                                           if (sp[j]["LFT"] <= pp_min) 
                                           or (sp[j]["siblings"])
                                        #    or (sp[j]["EFT"] == pp_min and sp[j]["LFT"] == pp_max) # Jelmer's *BAD* idea
                                           for s in sp[j]["succ"]
            )

            result = certainly_ready_timer_jobs.union(certainly_ready_sub_jobs)
            # print(last_dispatched_job)
            # breakpoint()
            return result

        def RC(k: str, sp):
            return {s for j in SP.keys() if sp[j]["LFT"] <= sp[k]["EFT"] for s in sp[j]["succ"]}


        # ignore means that we ignore the 'captured' flag
        def PWS(pp, sp):
            pp_min, pp_max = pp

            timer_sets = set()
            for k in not_dispatched_jobs:
                # if pred(k) is empty and k can be scheduled before pp_max
                if len(PRED[k]) == 0 and JDICT[k]["r_min"] <= pp_max:
                    timer_set = set([k])
                    other_timers = set(
                        j for j in not_dispatched_jobs
                        if len(PRED[j]) == 0 
                        and JDICT[j]["r_min"] <= pp_max 
                        and JDICT[j]["r_max"] <= JDICT[k]["r_min"]
                    )
                    timer_sets.add(frozenset(timer_set.union(other_timers)))

            sub_sets = set()
            for k in sp:
                if (max(sp[k]["EFT"], pp_min) <= min(sp[k]["LFT"], pp_max) or sp[k]["LFT"] <= pp_min) and (sp[k]["captured"]):
                    succ_set = set(sp[k]["succ"])
                    sub_sets.add(frozenset((succ_set.union(RC(k, sp)))))

            return timer_sets.union(sub_sets)
        
        def EWS(GWS_set, PWS_set):
            # breakpoint()
            if len(PWS_set) == 0:
                return {frozenset(GWS_set)}
            else:
                return {frozenset(GWS_set.union(S)) for S in PWS_set}

        def dispatch_jobs(jobs, pp, new_pp = False, new_gws: set = set()):
            for j in jobs:
                if new_pp == False and v_p != InitNode:
                    # j is higher priority than last_dispatched_job
                    # and we have the same polling point
                    if JDICT[j]["p"] < JDICT[last_dispatched_job]["p"]:
                        continue

                PP_vp_prime = pp
                EST_j = A1_min if len(PRED[j]) != 0 else max(A1_min, JDICT[j]["r_min"])
                LST_j = A1_max if len(PRED[j]) != 0 else max(A1_max, JDICT[j]["r_max"])
                EFT_j = EST_j + JDICT[j]["C_min"]
                LFT_j = LST_j + JDICT[j]["C_max"]
                # BR[j] = min(EFT_j - JDICT[j]["r_min"], BR[j])
                # WR[j] = max(LFT_j - JDICT[j]["r_min"], WR[j])
                BR[j] = EFT_j
                WR[j] = LFT_j
                FT_vp_prime = copy.deepcopy(FT)
                FT_vp_prime[j] = (EFT_j, LFT_j)

                # Calculate A
                PA = [max(EST_j, A[idx][0]) for idx in range(1, m)]
                CA = [max(EST_j, A[idx][1]) for idx in range(1, m)]
                PA.append(EFT_j)
                CA.append(LFT_j)
                PA.sort()
                CA.sort()
                A_vp_prime = [(0, 0) for i in range(m)]
                for i in range(m):
                    A_vp_prime[i] = (PA[i], CA[i])

                # Calculate SP
                SP_vp_prime = copy.deepcopy(SP) ## COPY ##
                succ_j = succ(j)
                pred_j = extract_single_element(PRED[j])

                if pred_j in SP_vp_prime:
                    # Remove the dispatched job from the successors set of its predecessor
                    aux = SP_vp_prime[pred_j]["succ"].copy()
                    SP_vp_prime[pred_j]["succ"] = aux.difference(set([j]))

                    # If the removal created an empty set, then remove the line in the scratchpad
                    if len(SP_vp_prime[pred_j]["succ"]) == 0:
                        del SP_vp_prime[pred_j]
                    # If there are still successors for the same predecessor, then set the siblings flag
                    else:
                        SP_vp_prime[pred_j]["siblings"] = True

                if len(succ_j) != 0:
                    SP_vp_prime[j] = {
                        "succ": succ_j,
                        "EFT": EFT_j,
                        "LFT": LFT_j,
                        "siblings": False,
                        "captured": False,
                    }

                if new_pp == False:
                    GW_vp_prime = copy.deepcopy(GW) if j not in GW else GW.difference(set([j]))
                else:
                    GW_vp_prime = new_gws.difference(set([j]))
                
                FJ_vp_prime = FJ.union(preds)

                new_state = State(A_vp_prime, PP_vp_prime, SP_vp_prime, GW_vp_prime, FT_vp_prime, FJ_vp_prime)
                new_state_id = get_rand_node_id()
                G.add_node(new_state_id, state=new_state)
                G.add_edge(P[-1], new_state_id, job=j, FT=(EFT_j,LFT_j))

                '''
                (safe) MERGE condition:
                J_P = J_P'
                A[x][v_p] \cap A[x][v_p'] != empty i.e. the core intervals must intersect
                GWS(v_p) == GWS(v_p')
                [maybe this???] PP(v_p) \cap PP(v_p') != empty
                FT order (v_p) == FT order (v_p') [this appears to be too strong -> so i'm not sure if it becomes unsafe if I remove it]

                MERGE:
                widen A
                widen PP
                widen FT for each j
                '''
                if merge == True:
                    vp_prime = G.nodes[new_state_id]["state"]
                    J_P_prime = J_P.union(set([j]))
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
                        GW_vq = v_q.GW
                        PP_vq = v_q.PP
                        SP_vq = v_q.SP
                        FT_vq = v_q.FT
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

                        if GW_vq != vp_prime.GW:
                            continue

                        if not (max(vp_prime.PP[0], PP_vq[0]) <= min(vp_prime.PP[1], PP_vq[1])):
                            continue

                        if list(SP_vq.keys()) != list(SP_vp_prime.keys()):
                            continue
                        
                        ############## THIS MIGHT MAKE THE ANALYSIS WRONG/UNSAFE IF LEFT UNCOMMENTED ############
                        # if list(FT_vq.keys()) != list(vp_prime.FT.keys()):
                        #     continue
                        
                        ####### Widen intervals #########
                        for x in range(m):
                            widened_A = (min(vp_prime.A[x][0], A_vq[x][0]), max(vp_prime.A[x][1], A_vq[x][1]))
                            vp_prime.A[x] = widened_A
                        
                        widened_PP = (min(vp_prime.PP[0], PP_vq[0]), max(vp_prime.PP[1], PP_vq[1]))
                        vp_prime.PP = widened_PP

                        for k in FT_vp_prime:
                            widened_FT = (min(vp_prime.FT[k][0], FT_vq[k][0]), max(vp_prime.FT[k][1], FT_vq[k][1]))
                            vp_prime.FT[k] = widened_FT
                        
                        ####### Redirect incoming edges from v_q to v_p' #######
                        v_q_id = Q[-1]
                        in_edges = list(G.in_edges(v_q_id, data=True))
                        for source, target, data in in_edges:
                            # Add the edge with the same attributes.
                            G.add_edge(source, new_state_id, **data)
                        
                        ####### Remove v_q and all its adjacent edges ########
                        G.remove_node(v_q_id)

        #################################################
        ############## ACTUAL ALGORITHM #################
        #################################################
        # GWS_set_old = GWS(PP_old, SP)
        GWS_set_old = GW
        PWS_set_old = PWS(PP_old, SP)
        print(last_dispatched_job)
        # breakpoint()

        ############# Decision making ###################
        if len(GWS_set_old) != 0:
            EWS_old = EWS(GWS_set_old, PWS_set_old)

            # Highest-priority jobs over some WS in EWS
            jobs_to_dispatch_old = {
                min(job_set, key=lambda j: JDICT[j]["p"])
                for job_set in EWS_old if job_set  # only process non-empty job_set
            }

            if len(jobs_to_dispatch_old) == 0:
                breakpoint()

            dispatch_jobs(jobs_to_dispatch_old, PP_old)

        elif len(GWS_set_old) == 0 and len(PWS_set_old) == 0:
            if min([SP[j]["EFT"] for j in SP], default=INF) > A1_max:
                PP_min_new = max(A1_min,
                                min([JDICT[j]["r_min"] for j in not_dispatched_jobs if len(PRED[j]) == 0], default=0),
                                min([SP[j]["EFT"] for j in SP], default=0)
                                )
                PP_max_new = max(A1_max, 
                                min([JDICT[j]["r_max"] for j in not_dispatched_jobs if len(PRED[j]) == 0], default=0),
                                min([SP[j]["LFT"] for j in SP], default=0)
                                )
            else:
                PP_min_new = A1_min
                PP_max_new = A1_max

            PP_new = (PP_min_new, PP_max_new)
            for j in SP:
                SP[j]["captured"] = True

            SP_new = SP
            GWS_set_new = GWS(PP_new, SP_new, new_pp = True)
            GWS_set_new = GWS_set_new.union(succs)
            PWS_set_new = PWS(PP_new, SP_new)
            EWS_new = EWS(GWS_set_new, PWS_set_new)
            # EWS_new = all_possible_WS
            breakpoint()

            jobs_to_dispatch_new = {
                min(job_set, key=lambda j: JDICT[j]["p"])
                for job_set in EWS_new if job_set  # only process non-empty job_set
            }

            if len(jobs_to_dispatch_new) == 0:
                print("######################### (2) ################")
                breakpoint()

            dispatch_jobs(jobs_to_dispatch_new, PP_new, new_pp = True, new_gws = GWS_set_new)
        
        elif len(GWS_set_old) == 0 and len(PWS_set_old) != 0:
            EWS_old = EWS(GWS_set_old, PWS_set_old)
            jobs_to_dispatch_old = {
                min(job_set, key=lambda j: JDICT[j]["p"])
                for job_set in EWS_old if job_set  # only process non-empty job_set
            }
            dispatch_jobs(jobs_to_dispatch_old, PP_old)
            
            ############ UPDATE PP #############
            if min([SP[j]["EFT"] for j in SP], default=INF) > A1_max:
                PP_min_new = max(A1_min,
                                min([JDICT[j]["r_min"] for j in not_dispatched_jobs if len(PRED[j]) == 0], default=0),
                                min([SP[j]["EFT"] for j in SP], default=0)
                                )
                PP_max_new = max(A1_max, 
                                min([JDICT[j]["r_max"] for j in not_dispatched_jobs if len(PRED[j]) == 0], default=0),
                                min([SP[j]["LFT"] for j in SP], default=0)
                                )
            else:
                PP_min_new = A1_min
                PP_max_new = A1_max

            PP_new = (PP_min_new, PP_max_new)
            # SP_new = get_new_SP()
            for j in SP:
                SP[j]["captured"] = True
            SP_new = SP
            GWS_set_new = GWS(PP_new, SP_new, new_pp = True)
            GWS_set_new = GWS_set_new.union(succs)
            PWS_set_new = PWS(PP_new, SP_new)
            EWS_new = EWS(GWS_set_new, PWS_set_new)
            # EWS_new = all_possible_WS
            jobs_to_dispatch_new = {
                min(job_set, key=lambda j: JDICT[j]["p"])
                for job_set in EWS_new if job_set  # only process non-empty job_set
            }
            dispatch_jobs(jobs_to_dispatch_new, PP_new, new_pp = True, new_gws = GWS_set_new)
            
            if len(jobs_to_dispatch_old) == 0 or len(jobs_to_dispatch_new) == 0:
                print("######################### (3) ################")
                breakpoint()

        # Next iteration
        logger.info(f"Max path length: {len(P)},  Number of nodes in graph : {counter}")
        P = shortestPathFromSourceToLeaf(G)

    return G, BR, WR
