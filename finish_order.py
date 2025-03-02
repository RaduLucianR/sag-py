import time
from functools import lru_cache

# Global variables that will be set in main()
m = None  # number of cores
tasks_info = {}  # mapping task id -> (ft_min, ft_max, exec_min, exec_max, dispatch)

# @lru_cache(maxsize=None)
def dp(current_time, waiting, running):
    """
    Dynamic programming function that propagates finish intervals using the analytical bounds.
    
    waiting: tuple of task ids (in dispatch order) not yet dispatched.
    running: tuple of tuples (task_id, finish_time, dispatch) for currently running tasks.
    """
    results = {}  # Mapping finish_ordering -> { task_id: (min_finish, max_finish) }
    
    # If there are waiting tasks and free cores, dispatch the next task.
    if waiting and len(running) < m:
        task_id = waiting[0]
        ft_min, ft_max, exec_min, exec_max, task_dispatch = tasks_info[task_id]
        new_waiting = waiting[1:]
        
        # Calculate the potential finish time interval using current_time and exec bounds.
        start_possible = current_time + exec_min
        end_possible   = current_time + exec_max
        
        # Intersect with the analytical finish time bounds.
        effective_lower = max(start_possible, ft_min)
        effective_upper = min(end_possible, ft_max)
        
        if effective_lower > effective_upper:
            # No valid finish time exists.
            return {}
        
        # Instead of iterating over every integer in the interval,
        # we branch on the critical points: the lower and upper bounds.
        new_results = {}
        for finish_time in (effective_lower, effective_upper):
            new_running = list(running) + [(task_id, finish_time, task_dispatch)]
            new_running.sort(key=lambda t: (t[1], t[2], t[0]))
            branch_results = dp(current_time, new_waiting, tuple(new_running))
            # Merge branch_results into new_results.
            for order, mapping in branch_results.items():
                if order in new_results:
                    for tid, (curr_min, curr_max) in mapping.items():
                        if tid in new_results[order]:
                            prev_min, prev_max = new_results[order][tid]
                            new_results[order][tid] = (min(prev_min, curr_min), max(prev_max, curr_max))
                        else:
                            new_results[order][tid] = (curr_min, curr_max)
                else:
                    new_results[order] = mapping.copy()
        return new_results

    # If no new task can be dispatched, process the next finish event.
    if running:
        next_time = min(task[1] for task in running)
        finishing_tasks = [task for task in running if task[1] == next_time]
        finishing_tasks.sort(key=lambda t: t[2])
        finished_ids = tuple(task[0] for task in finishing_tasks)
        new_running = tuple(task for task in running if task[1] != next_time)
        branch_results = dp(next_time, waiting, new_running)
        for order, mapping in branch_results.items():
            new_order = finished_ids + order
            new_mapping = {tid: (next_time, next_time) for tid in finished_ids}
            for tid, (prev_min, prev_max) in mapping.items():
                new_mapping[tid] = (prev_min, prev_max)
            if new_order in results:
                for tid, (curr_min, curr_max) in new_mapping.items():
                    if tid in results[new_order]:
                        old_min, old_max = results[new_order][tid]
                        results[new_order][tid] = (min(old_min, curr_min), max(old_max, curr_max))
                    else:
                        results[new_order][tid] = (curr_min, curr_max)
            else:
                results[new_order] = new_mapping
        return results

    # Base case: no waiting tasks and no running tasks.
    return {(): {}}

def compute_idle_trigger_tasks(m, dispatch_order, finish_order, finish_times):
    """
    Computes the tasks after which at least one core becomes idle based solely on finish orderings.
    
    Parameters:
        m : int
            Number of cores.
        dispatch_order : list of str
            Tasks in the order they were dispatched.
        finish_order : tuple of str
            Tasks in the order they finish.
        finish_times : dict
            Mapping from task ID to (min_finish, max_finish).
            
    Returns:
        A list of task IDs representing the first finishing group after which a core becomes idle.
        This group is determined by taking the (n-m+1)-th finish event and including any subsequent tasks 
        whose finish time intervals overlap with that of the base idle event.
    """
    n = len(dispatch_order)
    # The idle event happens when the finished count reaches (n - m + 1)
    idle_index = n - m + 1  # using 1-based indexing
    if idle_index < 1 or idle_index > len(finish_order):
        return []
    
    # Identify the base task (the (n-m+1)-th finish) and its finish interval.
    base_task = finish_order[idle_index - 1]  # convert to 0-index
    base_interval = finish_times[base_task]
    
    idle_tasks = [base_task]
    
    # Check subsequent tasks: if their finish interval overlaps with the base task's interval,
    # then they could finish concurrently, so add them to the idle group.
    for task in finish_order[idle_index:]:
        current_interval = finish_times[task]
        # Check if intervals overlap:
        if max(base_interval[0], current_interval[0]) <= min(base_interval[1], current_interval[1]):
            idle_tasks.append(task)
        else:
            break
            
    return idle_tasks

def main():
    global m, tasks_info

    tasks = [
        {"id": "t1", "ft": (1, 3),   "exec_range": (1, 3)},
        {"id": "t6", "ft": (5, 11),  "exec_range": (5, 11)},
        {"id": "t9", "ft": (11, 23), "exec_range": (10, 20)},
        {"id": "t2", "ft": (6, 14),  "exec_range": (1, 3)},
        {"id": "t3", "ft": (8, 18),  "exec_range": (2, 4)},
        {"id": "t7", "ft": (14, 30), "exec_range": (6, 12)},
        {"id": "t4", "ft": (13, 28), "exec_range": (2, 5)},
        # {"id": "t8", "ft": (19, 40), "exec_range": (6, 12)},
    ]
    # tasks = [
    #     {"id": "t1", "ft": (1000, 3000),   "exec_range": (1000, 3000)},
    #     {"id": "t6", "ft": (5000, 11000),  "exec_range": (5000, 11000)},
    #     {"id": "t9", "ft": (11000, 23000), "exec_range": (10000, 20000)},
    #     {"id": "t2", "ft": (6000, 14000),  "exec_range": (1000, 3000)},
    #     {"id": "t3", "ft": (8000, 18000),  "exec_range": (2000, 4000)},
    #     {"id": "t7", "ft": (14000, 30000), "exec_range": (6000, 12000)},
    #     {"id": "t4", "ft": (13000, 28000), "exec_range": (2000, 5000)},
    #     {"id": "t8", "ft": (19000, 40000), "exec_range": (6000, 12000)},
    # ]
    
    m = 2  # number of cores

    # Known dispatch order.
    dispatch_order = ["t1", "t6", "t9", "t2", "t3", "t7", "t4"]#, "t8"]
    dispatch_index = {tid: idx for idx, tid in enumerate(dispatch_order)}
    
    # Build tasks_info: mapping task id -> (ft_min, ft_max, exec_min, exec_max, dispatch)
    tasks_info = {}
    for task in tasks:
        tid = task["id"]
        ft_min, ft_max = task["ft"]
        exec_min, exec_max = task["exec_range"]
        tasks_info[tid] = (ft_min, ft_max, exec_min, exec_max, dispatch_index[tid])
    
    waiting = tuple(dispatch_order)
    running = tuple()
    
    # dp.cache_clear()  # clear the DP cache in case main() is run more than once
    ordering_bounds = dp(0, waiting, running)
    
    print("All possible finish orderings for dispatch sequence: ")
    print(dispatch_order)
    for order in sorted(ordering_bounds):
        bounds = ordering_bounds[order]
        idle_tasks = compute_idle_trigger_tasks(m, dispatch_order, order, bounds)
        order_str = " -> ".join(f"{tid}[{bounds[tid][0]}, {bounds[tid][1]}]" for tid in order)
        print(order_str)
        print("Tasks after which at least one core becomes idle:", idle_tasks)

    # PP = (11, 23)
    # A = [(14, 30), (19, 40)]
    # print(A, PP)



if __name__ == "__main__":
    start = time.time()
    main()
    stop = time.time()
    print(f"Execution time: {stop - start:.4f} seconds")
