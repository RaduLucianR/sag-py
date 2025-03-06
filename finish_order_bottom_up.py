import time

tasks_info = {}  # mapping task id -> (ft_min, ft_max, exec_min, exec_max, dispatch)

def bottom_up_dp(initial_time, waiting, running, m):
    """
    Bottom-up dynamic programming that computes all possible finish orderings.
    
    Parameters:
      initial_time: starting time (usually 0)
      waiting: tuple of task ids (in dispatch order) not yet dispatched.
      running: tuple of tuples (task_id, finish_time, task_dispatch) for tasks already dispatched and running.
      m: number of cores
    
    Returns:
      A dictionary mapping finish_order (a tuple of task ids in finish order) 
      to a dict mapping task_id -> (min_finish, max_finish) (the resolved finish times).
      
    Note:
      job_info must be defined globally (or passed in) as a mapping:
         task_id -> (ft_min, ft_max, exec_min, exec_max, task_dispatch)
    """
    
    # Each state is a tuple:
    #   (current_time, waiting, running, finish_order, finish_intervals)
    # where finish_intervals is a dict: task_id -> (min_finish, max_finish)
    # Use a list for states and a set for seen states to avoid duplicates.
    initial_state = (initial_time, waiting, running, (), {})
    states = [initial_state]
    seen = set()
    final_results = {}
    
    while states:
        new_states = []
        for state in states:
            current_time, waiting, running, finish_order, finish_intervals = state
            
            # Terminal state: no waiting tasks and nothing running.
            if not waiting and not running:
                final_results[finish_order] = finish_intervals
                continue
            
            # If there are waiting tasks and free cores, dispatch the next task.
            if waiting and len(running) < m:
                task_id = waiting[0]
                # Unpack job_info for this task.
                ft_min, ft_max, exec_min, exec_max, task_dispatch = tasks_info[task_id]
                new_waiting = waiting[1:]
                # Calculate potential finish interval based on current time.
                start_possible = current_time + exec_min
                end_possible   = current_time + exec_max
                # Intersect with analytical finish time bounds.
                effective_lower = max(start_possible, ft_min)
                effective_upper = min(end_possible, ft_max)
                
                # If the intersection is empty, skip this branch.
                if effective_lower > effective_upper:
                    continue
                
                # We branch on the critical finish times.
                for finish_time in (effective_lower, effective_upper):
                    new_running = list(running)
                    new_running.append((task_id, finish_time, task_dispatch))
                    # Sort running tasks by finish_time, then dispatch order, then task id.
                    new_running.sort(key=lambda t: (t[1], t[2], t[0]))
                    new_state = (current_time,
                                 new_waiting,
                                 tuple(new_running),
                                 finish_order,
                                 finish_intervals.copy())
                    # Create a hashable key for the state.
                    state_key = (current_time, new_waiting, tuple(new_running),
                                 finish_order, tuple(sorted(new_state[4].items())))
                    if state_key not in seen:
                        seen.add(state_key)
                        new_states.append(new_state)
            
            # Otherwise, if no new task can be dispatched, process the next finish event.
            elif running:
                # Find the earliest finish time.
                next_time = min(task[1] for task in running)
                # Identify all tasks finishing at that time.
                finishing_tasks = [task for task in running if task[1] == next_time]
                finishing_tasks.sort(key=lambda t: t[2])  # sort by dispatch order
                finished_ids = tuple(task[0] for task in finishing_tasks)
                new_finish_order = finish_order + finished_ids
                # In this branch, the tasks that finish now get their finish time fixed.
                new_finish_intervals = finish_intervals.copy()
                for tid in finished_ids:
                    new_finish_intervals[tid] = (next_time, next_time)
                # Remove finished tasks from running.
                new_running = tuple(task for task in running if task[1] != next_time)
                new_state = (next_time, waiting, new_running, new_finish_order, new_finish_intervals)
                state_key = (next_time, waiting, new_running,
                             new_finish_order, tuple(sorted(new_state[4].items())))
                if state_key not in seen:
                    seen.add(state_key)
                    new_states.append(new_state)
        states = new_states
    return final_results

def main():
    global m, tasks_info

    tasks = [
        {"id": "t1", "ft": (1, 3),   "exec_range": (1, 3)},
        {"id": "t6", "ft": (5, 11),  "exec_range": (5, 11)},
        {"id": "t9", "ft": (11, 23), "exec_range": (10, 20)},
        {"id": "t2", "ft": (6, 14),  "exec_range": (1, 3)},
        {"id": "t3", "ft": (8, 18),  "exec_range": (2, 4)},
        {"id": "t7", "ft": (14, 30), "exec_range": (6, 12)},
        # {"id": "t4", "ft": (13, 28), "exec_range": (2, 5)},
        # {"id": "t8", "ft": (19, 40), "exec_range": (6, 12)},
        # {"id": "t10", "ft": (34, 71), "exec_range": (20, 41)},
        # {"id": "t5", "ft": (22, 46), "exec_range": (3, 6)},
        # {"id": "t1_2", "ft": (51, 53), "exec_range": (1, 3)},
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
    dispatch_order = ["t1", "t6", "t9", "t2", "t3", "t7"]#, "t4"]#, "t8", "t10", "t5"]#, "t1_2"]
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
    ordering_bounds = bottom_up_dp(0, waiting, running, 2)
    
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