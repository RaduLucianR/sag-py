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

        if current_time < ft_min - exec_min:
            return dp(ft_min - exec_min, waiting, running)
        
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

def main():
    global m, tasks_info

    tasks = [
        {"id": "t1", "ft": (1, 6),   "exec_range": (1, 6)},
        {"id": "t6", "ft": (5, 11),  "exec_range": (5, 11)},
        {"id": "t9", "ft": (11, 26), "exec_range": (10, 20)},
        {"id": "t2", "ft": (6, 14),  "exec_range": (1, 3)},
        # {"id": "t3", "ft": (8, 18),  "exec_range": (2, 4)},
        # {"id": "t7", "ft": (14, 30), "exec_range": (6, 12)},
        # # {"id": "t4", "ft": (13, 28), "exec_range": (2, 5)},
        # {"id": "t8", "ft": (19, 40), "exec_range": (6, 12)},
        # {"id": "t10", "ft": (34, 71), "exec_range": (20, 41)},
        # {"id": "t5", "ft": (22, 46), "exec_range": (3, 6)},
        # {"id": "t1_2", "ft": (51, 53), "exec_range": (1, 3)},
    ]

    m = 2  # number of cores

    # Known dispatch order.
    dispatch_order = ["t1", "t6", "t9", "t2"]#, "t3", "t7"]#, "t4"]#, "t8", "t10", "t5"]#, "t1_2"]
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
        order_str = " -> ".join(f"{tid}[{bounds[tid][0]}, {bounds[tid][1]}]" for tid in order)
        print(order_str)

if __name__ == "__main__":
    start = time.time()
    main()
    stop = time.time()
    print(f"Execution time: {stop - start:.4f} seconds")
