#!/usr/bin/env python3

def jobs_can_finish_before_j(jobs, m, j_id):
    """
    Given a list of jobs and m cores, return the job ids of those jobs (dispatched before job j)
    that can finish before job j in some valid scenario.
    
    Each job is a dictionary with:
       - 'id': job identifier.
       - 'FTmin': lower bound on the finish time.
       - 'FTmax': upper bound on the finish time.
       - 'Cmin': lower bound on the execution time.
       - 'Cmax': upper bound on the execution time.
       
    We derive:
       STmin = FTmin - Cmin   and   STmax = FTmax - Cmax.
       
    The list "jobs" is given in the dispatch order.
    
    We assume that job j (with id j_id) is in a set Z of jobs that can be the first to free a core.
    In the scenario where j is indeed the first job to free a core, no core becomes idle until j finishes.
    Thus, at most m-1 jobs (running concurrently with j) can finish before j.
    
    A necessary condition for a job i (dispatched before j) to finish before j is:
         FTmin(i) < FTmax(j)
    and then among these, only the m-1 with the smallest FTmin values can be scheduled before j.
    """
    # Find job j in the dispatch order
    j_index = None
    for idx, job in enumerate(jobs):
        if job['id'] == j_id:
            j_index = idx
            j_job = job
            break
    if j_index is None:
        raise ValueError("Job with id '{}' not found.".format(j_id))
    
    # Only jobs dispatched before j can possibly finish before j.
    candidates = []
    for idx in range(j_index):
        job = jobs[idx]
        # A necessary condition: its best-case finish is before j's worst-case finish.
        if job['FTmin'] < j_job['FTmax']:
            candidates.append(job)
    
    # Sort the candidate jobs by their best-case finish time.
    candidates_sorted = sorted(candidates, key=lambda job: job['FTmin'])
    
    # Because j is the first to free a core, at most m-1 jobs can finish before j.
    feasible = candidates_sorted[:max(m - 1, 0)]
    
    return [job['id'] for job in feasible]


if __name__ == "__main__":
    # Example jobs.
    # The jobs are given in the dispatch order.
    # For each job we provide:
    #   - FTmin: lower bound on finish time.
    #   - FTmax: upper bound on finish time.
    #   - Cmin: lower bound on execution time.
    #   - Cmax: upper bound on execution time.
    # The start time bounds are not explicitly provided but are computed as:
    #      STmin = FTmin - Cmin
    #      STmax = FTmax - Cmax
    jobs = [
        {'id': 't9', 'FTmin': 11, 'FTmax': 23, 'Cmin': 10, 'Cmax': 21},
        {'id': 't2', 'FTmin': 6, 'FTmax': 14, 'Cmin': 1, 'Cmax': 3}, 
        {'id': 't3', 'FTmin': 8, 'FTmax': 18, 'Cmin': 2, 'Cmax': 4}, 
        {'id': 't7', 'FTmin': 14, 'FTmax': 30, 'Cmin': 6, 'Cmax': 12}, 
    ]
    
    m = 2  # number of cores in the system
    
    for j in jobs:
        print(f"{jobs_can_finish_before_j(jobs, m, j['id'])} can finish before {j['id']} triggers the polling point")
