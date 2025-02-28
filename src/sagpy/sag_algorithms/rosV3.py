import networkx as nx
import random
import logging
from sagpy.sag_template import sag_algorithm
import copy


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
        # X: set,
        # FTI: dict,
        PP: tuple[int, int],
        #             succ  EFT  LFT   s     c
        # SP: dict[tuple[set, int, int, bool, bool]],
        SP: dict,
    ):
        self.A = A
        # self.X = X
        # self.FTI = FTI
        self.PP = PP
        self.SP = SP

    def __repr__(self):
        return f"{self.A} {self.PP}"


@sag_algorithm
def ScheduleGraphConstructionAlgorithm(
    J: set,
    m: int,
    JDICT: dict,
    PRED: dict,
    logger=logging.Logger("SAGPY", logging.CRITICAL),
) -> tuple[nx.DiGraph, dict, dict]:
    def succ(j: str):
        succ_set = set()
        for k in J:
            if j in PRED[k]:
                succ_set.add(k)
        return succ_set

    INF = 100000  # Representation for infinity
    G = nx.DiGraph()
    BR = {Ji: INF for Ji in J}
    WR = {Ji: 0 for Ji in J}

    logger.info(f"HOW MANY JOBS: {len(J)}")

    ERT0 = min([JDICT[Jy]["r_min"] for Jy in J])
    LRT0 = min([JDICT[Jy]["r_max"] for Jy in J])
    PP0 = (ERT0, LRT0)
    InitNode = State([(0, 0) for core in range(m)], PP0, dict())
    G.add_node(0, state=InitNode)

    P = shortestPathFromSourceToLeaf(G)
    while len(P) - 1 < len(J):
        J_P = set([G[u][v]["job"] for u, v in zip(P[:-1], P[1:])])
        not_dispatched_jobs = J.difference(J_P)
        v_p = G.nodes[P[-1]]["state"]
        parent_state = G.nodes[P[-2]]["state"] if v_p != InitNode else None
        last_dispatched_job = G[P[-2]][P[-1]]["job"] if v_p != InitNode else ""

        A = v_p.A
        PP_old = v_p.PP
        SP: dict[tuple[set, int, int, bool, bool]] = v_p.SP

        A1 = A[0]
        A1_min = A1[0]
        A1_max = A1[1]

        def GWS(pp: tuple[int, int], ignore = False):
            pp_min, pp_max = pp

            certainly_ready_timer_jobs = set(
                [
                    j
                    for j in not_dispatched_jobs
                    # pred(j) = empty
                    if len(PRED[j]) == 0 and JDICT[j]["r_max"] <= pp_min
                ]
            )

            certainly_ready_sub_jobs = set(
                s 
                for j in SP.keys() 
                if SP[j]["LFT"] <= pp_min and (ignore or SP[j]["siblings"])
                for s in SP[j]["succ"]
            )

            return certainly_ready_timer_jobs.union(certainly_ready_sub_jobs)

        def RC(k: str):
            return {s for j in SP.keys() if SP[j]["LFT"] <= SP[k]["EFT"] for s in SP[j]["succ"]}


        # ignore means that we ignore the 'captured' flag
        def PWS(pp, ignore=False):
            pp_min, pp_max = pp

            # Mitra's Magic formula(ish): \forall j \in SP, if LFT(j) != A_x^{max} \forall x, 1\leq x \leq m, 
            #                              then the successors of j are coupled with any other WS
            coupled = set()
            for j in SP:
                yes = True
                for x in range(m):
                    A_x_max = A[x][1]
                    if SP[j]["LFT"] == A_x_max:
                        yes = False
                        break
                if yes:
                    coupled.update(SP[j]["succ"])

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
            for k in SP:
                # if [EFT(k), LFT(k)] intersects [pp_min, pp_max] and k is captured
                if max(SP[k]["EFT"], pp_min) <= min(SP[k]["LFT"], pp_max) and (ignore or SP[k]["captured"]):
                    succ_set = set(SP[k]["succ"])
                    # sub_sets.add(frozenset((succ_set.union(RC(k)))))
                    sub_sets.add(frozenset((succ_set.union(RC(k))).union(coupled)))

            return timer_sets.union(sub_sets)


        def EWS(pp, ignore = False):
            GWS_set = GWS(pp, ignore)
            PWS_set = PWS(pp, ignore)
            return {frozenset(GWS_set.union(S)) for S in PWS_set}

        def dispatch_jobs(jobs, pp, new_pp = False):
            for j in jobs:
                PP_vp_prime = pp
                EST_j = A1_min
                LST_j = A1_max
                EFT_j = EST_j + JDICT[j]["C_min"]
                LFT_j = LST_j + JDICT[j]["C_max"]
                print(j, LFT_j)

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

                # if len(SP) == 0:
                #     breakpoint()

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

                # for i in SP_vp_prime:
                #     if len(SP_vp_prime[i]["succ"]) == 0:
                #         SP_vp_prime.pop(i)

                # New polling point, so we must set the captured flag for all rows in SP
                if new_pp:
                    for r in SP_vp_prime:
                        SP_vp_prime[r]["captured"] = True

                if len(succ_j) != 0:
                    SP_vp_prime[j] = {
                        "succ": succ_j,
                        "EFT": EFT_j,
                        "LFT": LFT_j,
                        "siblings": False,
                        "captured": False,
                    }

                new_state = State(A_vp_prime, PP_vp_prime, SP_vp_prime)
                new_state_id = get_rand_node_id()
                G.add_node(new_state_id, state=new_state)
                G.add_edge(P[-1], new_state_id, job=j)

                for i in SP_vp_prime:
                    if len(SP_vp_prime[i]["succ"]) == 0:
                        breakpoint()

                logger.info(f"Dispatched job {j} with v_p' -> A:{A_vp_prime}, PP: {PP_vp_prime}")
                logger.info("SP:")
                try:
                    for a in SP_vp_prime:
                        logger.info(SP_vp_prime[a])
                except:
                    print("######################### (1) ################")
                    breakpoint()

        ########### ACTUAL ALGORITHM #########
        GWS_set = GWS(PP_old)
        PWS_set = PWS(PP_old)

        if len(GWS_set) != 0:
            EWS_old = EWS(PP_old)

            # Highest-priority jobs over some WS in EWS
            jobs_to_dispatch_old = {
                min(job_set, key=lambda j: JDICT[j]["p"])
                for job_set in EWS_old if job_set  # only process non-empty job_set
            }

            if len(jobs_to_dispatch_old) == 0:
                breakpoint()

            dispatch_jobs(jobs_to_dispatch_old, PP_old)

        elif len(GWS_set) == 0 and len(PWS_set) == 0:
            PP_new = (A1_min, A1_max) # TODO: This is wrong because it doesn't take into account the case when the exec-thread is idle
            EWS_new = EWS(PP_new, ignore = True) ########### NEW PP SO IGNORE FLAGS

            jobs_to_dispatch_new = {
                min(job_set, key=lambda j: JDICT[j]["p"])
                for job_set in EWS_new if job_set  # only process non-empty job_set
            }

            if len(jobs_to_dispatch_new) == 0:
                print("######################### (2) ################")
                breakpoint()

            dispatch_jobs(jobs_to_dispatch_new, PP_new, new_pp = True)
        
        elif len(GWS_set) == 0 and len(PWS_set) != 0:
            EWS_old = EWS(PP_old)
            jobs_to_dispatch_old = {
                min(job_set, key=lambda j: JDICT[j]["p"])
                for job_set in EWS_old if job_set  # only process non-empty job_set
            }
            dispatch_jobs(jobs_to_dispatch_old, PP_old)

            PP_new = (A1_min, A1_max) #TODO: fix
            EWS_new = EWS(PP_new, ignore = True) ########### NEW PP SO IGNORE FLAGS
            jobs_to_dispatch_new = {
                min(job_set, key=lambda j: JDICT[j]["p"])
                for job_set in EWS_new if job_set  # only process non-empty job_set
            }
            dispatch_jobs(jobs_to_dispatch_new, PP_new, new_pp = True)
            
            if PP_new == (8, 18):
                print("######################### (3) ################")
                breakpoint()

        # Next iteration
        logger.info(len(P))
        P = shortestPathFromSourceToLeaf(G)

    return G, BR, WR
