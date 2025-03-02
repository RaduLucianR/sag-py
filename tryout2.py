import time
from functools import lru_cache

# Global simulation parameters.
m = None  # number of cores
tasks_info = {}  # mapping: task id -> (ft_min, ft_max, exec_min, exec_max, dispatch_index)

@lru_cache(maxsize=None)
def dp(prefix, agg_frozen, current_time, waiting, running):
    """
    Recursively computes aggregated finish orderings for the remaining tasks.
    
    Parameters:
      prefix      : Tuple of task IDs already finished (in finish order).
      agg_frozen  : A frozenset encoding a dict mapping finished task IDs 
                    to their aggregated finish time bounds, i.e. {tid: (min_finish, max_finish)}.
      current_time: Current simulation time.
      waiting     : Tuple of task IDs (in dispatch order) not yet dispatched.
      running     : Tuple of tuples (task_id, finish_time, dispatch) for tasks currently running.
    
    Returns:
      A dictionary mapping a finish ordering (tuple of task IDs) to a dictionary
      of finish time bounds {task_id: (min_finish, max_finish)}.
    """
    results = {}
    # Rebuild aggregation dictionary from its frozenset representation.
    agg = dict(agg_frozen)
    
    # Dispatch branch: if there are waiting tasks and a free core, try dispatching the next task.
    if waiting and len(running) < m:
        task_id = waiting[0]
        ft_min, ft_max, exec_min, exec_max, task_dispatch = tasks_info[task_id]
        new_waiting = waiting[1:]
        start_possible = current_time + exec_min
        end_possible   = current_time + exec_max
        effective_lower = max(start_possible, ft_min)
        effective_upper = min(end_possible, ft_max)
        if effective_lower > effective_upper:
            # No valid finish time for this task.
            return {}
        # Instead of iterating over every value, we branch on the two endpoints.
        for finish_time in (effective_lower, effective_upper):
            new_running = list(running) + [(task_id, finish_time, task_dispatch)]
            new_running.sort(key=lambda t: (t[1], t[2], t[0]))
            branch_results = dp(prefix, agg_frozen, current_time, new_waiting, tuple(new_running))
            # Merge the branch results into our results.
            for order, mapping in branch_results.items():
                if order in results:
                    for tid, (new_min, new_max) in mapping.items():
                        if tid in results[order]:
                            curr_min, curr_max = results[order][tid]
                            results[order][tid] = (min(curr_min, new_min), max(curr_max, new_max))
                        else:
                            results[order][tid] = (new_min, new_max)
                else:
                    results[order] = mapping.copy()
        return results

    # Finishing branch: if no new dispatch is possible, process the next finish event.
    if running:
        next_time = min(task[1] for task in running)
        # Identify all tasks finishing at next_time.
        finishing_tasks = [task for task in running if task[1] == next_time]
        finishing_tasks.sort(key=lambda t: t[2])  # Tie-break by dispatch order.
        finished_ids = tuple(task[0] for task in finishing_tasks)
        new_running = tuple(task for task in running if task[1] != next_time)
        # Update the aggregated finish times for the finished tasks.
        new_agg = dict(agg)
        for tid in finished_ids:
            if tid in new_agg:
                old_min, old_max = new_agg[tid]
                new_agg[tid] = (min(old_min, next_time), max(old_max, next_time))
            else:
                new_agg[tid] = (next_time, next_time)
        new_agg_frozen = frozenset(new_agg.items())
        new_prefix = prefix + finished_ids
        branch_results = dp(new_prefix, new_agg_frozen, next_time, waiting, new_running)
        # Merge branch results.
        for order, mapping in branch_results.items():
            if order in results:
                for tid, (new_min, new_max) in mapping.items():
                    if tid in results[order]:
                        curr_min, curr_max = results[order][tid]
                        results[order][tid] = (min(curr_min, new_min), max(curr_max, new_max))
                    else:
                        results[order][tid] = (new_min, new_max)
            else:
                results[order] = mapping.copy()
        return results

    # Base case: no tasks waiting and none running.
    return {prefix: dict(agg)}

def simulate_dispatch_order(dispatch_order):
    """
    Given a dispatch order (a list of task IDs), build the simulation state,
    clear the DP cache, and call dp() from the initial state.
    
    Returns the aggregated finish orderings.
    """
    global m, tasks_info
    # For each task in the dispatch order, update tasks_info with its parameters.
    for idx, tid in enumerate(dispatch_order):
        if tid in tasks_data:
            task = tasks_data[tid]
            ft_min, ft_max = task["ft"]
            exec_min, exec_max = task["exec_range"]
            # The dispatch order (for tie-breaking) is given by the index.
            tasks_info[tid] = (ft_min, ft_max, exec_min, exec_max, idx)
        else:
            print(f"Task {tid} not found in tasks_data")
    waiting = tuple(dispatch_order)
    running = tuple()
    prefix = tuple()
    initial_agg_frozen = frozenset({})
    dp.cache_clear()
    return dp(prefix, initial_agg_frozen, 0, waiting, running)

# A dictionary of task parameters.
# (Each task has analytical finish time bounds and an allowed execution duration interval.)
tasks_data = {
    "t1":  {"id": "t1",  "ft": (1, 3),    "exec_range": (1, 3)},
    "t6":  {"id": "t6",  "ft": (5, 11),   "exec_range": (5, 11)},
    "t9":  {"id": "t9",  "ft": (11, 23),  "exec_range": (10, 20)},
    "t2":  {"id": "t2",  "ft": (6, 14),   "exec_range": (1, 3)},
    "t3":  {"id": "t3",  "ft": (8, 18),   "exec_range": (2, 4)},
    "t7":  {"id": "t7",  "ft": (14, 30),  "exec_range": (6, 12)},
    # "t4":  {"id": "t4",  "ft": (13, 28),  "exec_range": (2, 5)},
    # "t8":  {"id": "t8",  "ft": (19, 40),  "exec_range": (6, 12)},
    # # New task to extend the dispatch order.
    # "t10": {"id": "t10", "ft": (22, 35),  "exec_range": (3, 5)}
}

def main():
    global m
    m = 2  # number of cores
    
    # First, simulate a state (v9) with a fixed dispatch order of eight tasks.
    dispatch_order_8 = ["t1", "t6", "t9", "t2", "t3"]#, "t7", "t4", "t8"]
    aggregated_v9 = simulate_dispatch_order(dispatch_order_8)
    
    print("Aggregated finish time bounds for dispatch order (v9):")
    for order in sorted(aggregated_v9):
        order_str = " -> ".join(order)
        print(order_str, aggregated_v9[order])
    
    print("\nExtending with t10 (state v10):")
    # Now extend the dispatch order with t10.
    dispatch_order_9 = ["t1", "t6", "t9", "t2", "t3", "t7"]#, "t4", "t8", "t10"]
    aggregated_v10 = simulate_dispatch_order(dispatch_order_9)
    
    print("Aggregated finish time bounds for dispatch order (v10):")
    for order in sorted(aggregated_v10):
        order_str = " -> ".join(order)
        print(order_str, aggregated_v10[order])

if __name__ == "__main__":
    start = time.time()
    main()
    stop = time.time()
    print(f"\nTotal Execution time: {stop - start:.4f} seconds")
