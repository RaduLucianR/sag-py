#!/usr/bin/env python3

def can_finish_before_j(jobs, m, j_id):
    """
    Given a list of jobs (each a dict with fields: 'id', 'dispatch_time', 'exec_min', 'F_max'),
    and m cores, return a list of job ids (dispatched no later than job j)
    that can possibly finish before job j.
    
    We assume that each job i cannot finish before:
         L_i = max(dispatch_time_i, (sum of exec_min for jobs dispatched <= i) / m)
    So if L_i < F_max of job j, then there is a scenario in which job i finishes before j.
    """
    # sort jobs by dispatch time (assumed to be the dispatch order)
    jobs_sorted = sorted(jobs, key=lambda job: job['dispatch_time'])
    
    # Find job j in the sorted list
    job_j = None
    for job in jobs_sorted:
        if job['id'] == j_id:
            job_j = job
            break
    if job_j is None:
        raise ValueError("Job with id '{}' not found.".format(j_id))
    
    # Only consider jobs that are dispatched no later than j.
    candidate_jobs = [job for job in jobs_sorted if job['dispatch_time'] <= job_j['dispatch_time']]
    
    jobs_before_j = []
    cumulative_exec = 0.0
    for job in candidate_jobs:
        cumulative_exec += job['exec_min']
        # Lower bound on finish time of job i given perfect parallelism on m cores
        L_i = max(job['dispatch_time'], cumulative_exec / m)
        # If this lower bound is less than job j's worst-case finish time,
        # then there exists at least one scenario (with job i using its best-case and j its worst-case)
        # where job i can finish before job j.
        if L_i < job_j['F_max']:
            jobs_before_j.append(job['id'])
    
    return jobs_before_j


if __name__ == "__main__":
    # Example list of jobs.
    # Each job is represented as a dictionary with:
    # - 'id': a unique job identifier
    # - 'dispatch_time': when the job is dispatched (or becomes available)
    # - 'exec_min': best-case (minimal) execution time (lower bound)
    # - 'exec_max': worst-case (maximal) execution time (not used in this simple check)
    # - 'F_max': worst-case finish time (e.g., dispatch_time + exec_max, or given by analysis)
    #
    # In a real system, these values might be derived from analytical bounds.
    jobs = [
        {'id': 't2', 'dispatch_time': 1, 'exec_min': 1, 'exec_max': 3, 'F_max': 14},  # F_min would be 2, F_max given as 4
        {'id': 't3', 'dispatch_time': 2, 'exec_min': 2, 'exec_max': 4, 'F_max': 18},  # F_min=4, F_max=6
        {'id': 't7', 'dispatch_time': 3, 'exec_min': 6, 'exec_max': 12, 'F_max': 30},  # F_min=3, F_max=5
        {'id': 't9', 'dispatch_time': 0, 'exec_min': 10, 'exec_max': 21, 'F_max': 23},  # F_min=5, F_max=7
    ]
    
    m = 2  # number of cores in the system
    
    for j in jobs:
        print(f"{can_finish_before_j(jobs, m, j['id'])} can finish before {j['id']} triggers the polling point")
