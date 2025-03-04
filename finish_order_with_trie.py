import time
import pygtrie  # pip install pygtrie if you don't have it installed

tasks_info = {}  # mapping task id -> (ft_min, ft_max, exec_min, exec_max, dispatch)

def print_ordering_bounds_trie(ordering_trie):
    # Iterate over all complete finish orders stored in the trie.
    for order, bounds in sorted(ordering_trie.items()):
        order_str = " -> ".join(f"{tid}[{bounds[tid][0]}, {bounds[tid][1]}]" for tid in order)
        print(order_str)

def bottom_up_dp_from_state(states, m):
    """
    Runs the bottom-up DP starting from a list of states.
    Each state is a tuple:
       (current_time, waiting, running, finish_order, finish_intervals)
    
    Returns a tuple:
      (final_results_trie, intermediate_states)
      
      - final_results_trie: a pygtrie.Trie mapping complete finish_order (tuple) -> finish_intervals,
        for states where waiting and running are empty.
      - intermediate_states: a list of states that have not reached completion.
    """
    seen = set()
    final_results_trie = pygtrie.Trie()
    worklist = list(states)
    intermediate = []  # states that are "partial" (waiting or running not empty)

    while worklist:
        next_states = []
        for state in worklist:
            current_time, waiting, running, finish_order, finish_intervals = state

            # Terminal state: no waiting and no running tasks.
            if not waiting and not running:
                final_results_trie[finish_order] = finish_intervals
                continue

            # Dispatch a waiting task if there is a free core.
            if waiting and len(running) < m:
                task_id = waiting[0]
                ft_min, ft_max, exec_min, exec_max, task_dispatch = tasks_info[task_id]
                new_waiting = waiting[1:]
                start_possible = current_time + exec_min
                end_possible   = current_time + exec_max
                effective_lower = max(start_possible, ft_min)
                effective_upper = min(end_possible, ft_max)
                if effective_lower > effective_upper:
                    # Skip branch: no valid finish interval.
                    continue
                # Consider both potential finish times (lower and upper bounds).
                for finish_time in (effective_lower, effective_upper):
                    new_running = list(running)
                    new_running.append((task_id, finish_time, task_dispatch))
                    new_running.sort(key=lambda t: (t[1], t[2], t[0]))
                    new_state = (current_time, new_waiting, tuple(new_running),
                                 finish_order, finish_intervals.copy())
                    state_key = (current_time, new_waiting, tuple(new_running),
                                 finish_order, tuple(sorted(new_state[4].items())))
                    if state_key not in seen:
                        seen.add(state_key)
                        next_states.append(new_state)
            # Process the next finish event.
            elif running:
                next_time = min(task[1] for task in running)
                finishing_tasks = [task for task in running if task[1] == next_time]
                finishing_tasks.sort(key=lambda t: t[2])
                finished_ids = tuple(task[0] for task in finishing_tasks)
                new_finish_order = finish_order + finished_ids
                new_finish_intervals = finish_intervals.copy()
                for tid in finished_ids:
                    new_finish_intervals[tid] = (next_time, next_time)
                new_running = tuple(task for task in running if task[1] != next_time)
                new_state = (next_time, waiting, new_running,
                             new_finish_order, new_finish_intervals)
                state_key = (next_time, waiting, new_running,
                             new_finish_order, tuple(sorted(new_finish_intervals.items())))
                if state_key not in seen:
                    seen.add(state_key)
                    next_states.append(new_state)
        # Collect intermediate states (those not yet complete).
        for s in next_states:
            if s[1] or s[2]:
                intermediate.append(s)
        worklist = next_states

    return final_results_trie, intermediate

def extend_dp_states(intermediate_states, new_task, m):
    """
    Given a set of intermediate DP states (from a dispatch order x),
    extend each state by appending the new_task to the waiting list,
    and then run the bottom-up DP from that state.
    
    This computes the complete finish orderings for dispatch order x+1,
    reusing previously computed DP results.
    
    Returns:
      final_results_trie: a pygtrie.Trie mapping finish_order -> finish_intervals.
    """
    extended_states = []
    for state in intermediate_states:
        current_time, waiting, running, finish_order, finish_intervals = state
        new_waiting = waiting + (new_task,)
        extended_states.append((current_time, new_waiting, running, finish_order, finish_intervals.copy()))
    
    return bottom_up_dp_from_state(extended_states, m)

def main():
    global m, tasks_info

    # Build tasks_info: mapping task id -> (ft_min, ft_max, exec_min, exec_max, dispatch)
    tasks_info.clear()
    tasks_info["t1"] = (1, 3, 1, 3, 1)
    tasks_info["t6"] = (5, 11, 5, 11, 2)
    tasks_info["t9"] = (11, 23, 10, 20, 3)
    tasks_info["t2"] = (6, 14, 1, 3, 4)
    tasks_info["t3"] = (8, 18, 2, 4, 5)
    tasks_info["t7"] = (14, 30, 6, 12, 5)
    tasks_info["t4"] = (13, 28, 2, 5, 6)

    m = 2  # number of cores
    dispatch_order = ("t1", "t6")#, "t9", "t2")
    # dispatch_order = ()
    initial_state = (0, dispatch_order, (), (), {})

    print("All possible finish orderings for dispatch sequence:")
    print(dispatch_order)
    final_results_trie, inter = bottom_up_dp_from_state([initial_state], m=m)
    print_ordering_bounds_trie(final_results_trie)
    
    new_dispatch = 't9'
    print(f"\nDispatch {new_dispatch}")
    res_trie, inter = extend_dp_states(inter, new_dispatch, m=m)
    print_ordering_bounds_trie(res_trie)
    
    new_dispatch = 't2'
    print(f"\nDispatch {new_dispatch}")
    res_trie, inter = extend_dp_states(inter, new_dispatch, m=m)
    print_ordering_bounds_trie(res_trie)
    
    new_dispatch = 't3'
    print(f"\nDispatch {new_dispatch}")
    res_trie, inter = extend_dp_states(inter, new_dispatch, m=m)
    print_ordering_bounds_trie(res_trie)

if __name__ == "__main__":
    start = time.time()
    main()
    stop = time.time()
    print(f"\nExecution time: {stop - start:.4f} seconds")
