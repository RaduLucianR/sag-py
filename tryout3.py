#!/usr/bin/env python3
import itertools

def schedule_chain(jobs_chain, assignment):
    """
    Given a list of jobs (each a dict with keys:
         'id', 'FTmin', 'Cmin', 'FTmax', 'Cmax'),
    and an assignment (a list of booleans of the same length)
    where True means we choose the “early” (best-case) mode and
          False means we choose the “delayed” (worst-case) mode,
    simulate a contiguous schedule on a single core as follows:
      - Each job i is allowed to start no earlier than STmin(i) = FTmin(i) - Cmin(i).
      - We assume we schedule as early as possible: the first job starts at its STmin.
      - Each subsequent job starts at max(previous finish, its STmin).
      - (We require that no gap appears—that is, we insist that the scheduled start equals the previous finish.)
    For each job, its processing time is chosen as:
         p = Cmin(i)   if assigned early,
         p = Cmax(i)   if assigned delayed.
    Returns (feasible, start_times, finish_times) where feasible is True if no idle gap occurred.
    """
    start_times = []
    finish_times = []
    feasible = True
    current_time = None
    for idx, job in enumerate(jobs_chain):
        # Earliest allowed start:
        st_min = job['FTmin'] - job['Cmin']
        if idx == 0:
            # For the first job, we force start at its earliest allowed time.
            current_time = st_min
        else:
            # For contiguity, we require that the next job can start immediately.
            # That is, if current_time is less than the job's earliest start, then we’d have to wait—which creates an idle gap.
            if current_time < st_min:
                feasible = False
                break
            # Otherwise, we start immediately (at current_time).
        start_times.append(current_time)
        # Processing time depends on the mode chosen.
        if assignment[idx]:
            proc_time = job['Cmin']
        else:
            proc_time = job['Cmax']
        finish_time = current_time + proc_time
        finish_times.append(finish_time)
        current_time = finish_time
    return feasible, start_times, finish_times

def find_early_finishers(jobs, m, j_id, T_j):
    """
    For the 2-core case (m=2) assume:
      - jobs is the list of jobs in dispatch order.
      - j_id is the designated job that frees its core first (i.e. job j).
      - T_j is the chosen finish time for job j (with T_j in [FTmin(j), FTmax(j)]).

    We assume that all jobs other than j must be scheduled on the other core,
    in the given dispatch order.
    
    We perform an exhaustive search over the 2^(number of non-j jobs) possible
    mode assignments (True=early, False=delayed) and simulate the chain.
    For each feasible contiguous schedule in which the chain’s final finish time is ≥ T_j
    (so that the other core does not go idle before T_j),
    we record those jobs that were scheduled in early mode (i.e. best-case)
    and that finish before T_j.
    
    Returns the set of job IDs (from among the non-j jobs) that can finish before j.
    """
    # Find job j in the dispatch order.
    j_index = None
    for idx, job in enumerate(jobs):
        if job['id'] == j_id:
            j_index = idx
            j_job = job
            break
    if j_index is None:
        raise ValueError(f"Job {j_id} not found.")
    # For this 2-core example, we assume job j is on one core
    # and all other jobs are on the other core.
    # (In a full model, jobs might be split among m-1 cores.)
    chain = [job for idx, job in enumerate(jobs) if job['id'] != j_id]
    
    n = len(chain)
    early_finishers = set()
    # Iterate over all binary assignments for the chain.
    for assignment in itertools.product([True, False], repeat=n):
        feasible, starts, finishes = schedule_chain(chain, assignment)
        if not feasible:
            continue
        # To keep the core busy until T_j, the chain’s final finish must be at least T_j.
        if finishes[-1] < T_j:
            continue
        # For each job in the chain that is run in early mode,
        # if its finish time is less than T_j, then it can finish before j.
        for idx, mode in enumerate(assignment):
            if mode and finishes[idx] < T_j:
                early_finishers.add(chain[idx]['id'])
    return early_finishers

if __name__ == "__main__":
    # Example data (dispatch order is as given):
    jobs = [
        {'id': 't9', 'FTmin': 11, 'FTmax': 23, 'Cmin': 10, 'Cmax': 21},
        {'id': 't2', 'FTmin': 6,  'FTmax': 14, 'Cmin': 1,  'Cmax': 3}, 
        {'id': 't3', 'FTmin': 8,  'FTmax': 18, 'Cmin': 2,  'Cmax': 4}, 
        {'id': 't7', 'FTmin': 14, 'FTmax': 30, 'Cmin': 6,  'Cmax': 12}, 
    ]
    m = 2  # two cores
    j_id = 't9'
    # Choose a candidate finish time for job t9.
    # In the scenario described, we choose T_j = 15 (which is in [11,23]).
    T_j = 15
    
    early = find_early_finishers(jobs, m, j_id, T_j)
    print(f"With T_{j_id} = {T_j} and dispatch order { ' -> '.join(job['id'] for job in jobs) },")
    print("the following jobs can finish before job {}:".format(j_id))
    print(sorted(early))
