import time
from copy import deepcopy

# ---------------------------
# Global simulation parameters
# ---------------------------
m = 2  # number of cores
# tasks_info maps task_id -> (ft_min, ft_max, exec_min, exec_max, dispatch_index)
tasks_info = {}

# Task definitions: each task has analytical finish bounds and an allowed execution range.
tasks_data = {
    "t1":  {"id": "t1",  "ft": (1, 3),    "exec_range": (1, 3)},
    "t6":  {"id": "t6",  "ft": (5, 11),   "exec_range": (5, 11)},
    "t9":  {"id": "t9",  "ft": (11, 23),  "exec_range": (10, 20)},
    "t2":  {"id": "t2",  "ft": (6, 14),   "exec_range": (1, 3)},
    "t3":  {"id": "t3",  "ft": (8, 18),   "exec_range": (2, 4)},
    "t7":  {"id": "t7",  "ft": (14, 30),  "exec_range": (6, 12)},
    "t4":  {"id": "t4",  "ft": (13, 28),  "exec_range": (2, 5)},
    "t8":  {"id": "t8",  "ft": (19, 40),  "exec_range": (6, 12)},
    "t10": {"id": "t10", "ft": (22, 35),  "exec_range": (3, 5)}
}


def init_tasks_info(dispatch_order):
    """
    Initialize the global tasks_info using the given dispatch_order
    (which sets the tie-break indices).
    """
    global tasks_info
    tasks_info.clear()
    for idx, tid in enumerate(dispatch_order):
        task = tasks_data[tid]
        ft_min, ft_max = task["ft"]
        exec_min, exec_max = task["exec_range"]
        tasks_info[tid] = (ft_min, ft_max, exec_min, exec_max, idx)


# ---------------------------
# Simulation state container
# ---------------------------
class SimulationState:
    def __init__(self, prefix, current_time, waiting, running, agg):
        """
        prefix: tuple of finished task IDs (finish order so far)
        current_time: current simulation time
        waiting: list of task IDs not yet dispatched (in dispatch order)
        running: list of tuples (task_id, finish_time, dispatch_index) for tasks in progress
        agg: dict mapping finished task IDs -> (min_finish, max_finish)
        """
        self.prefix = tuple(prefix)
        self.current_time = current_time
        self.waiting = list(waiting)
        self.running = list(running)
        self.agg = dict(agg)  # aggregated finish times for finished tasks

    def clone(self):
        return SimulationState(self.prefix, self.current_time,
                               self.waiting.copy(), self.running.copy(),
                               self.agg.copy())

    def __repr__(self):
        return (f"State(prefix={self.prefix}, time={self.current_time}, "
                f"waiting={self.waiting}, running={self.running}, agg={self.agg})")


# ---------------------------
# The core simulation engine
# ---------------------------
def simulate_state(state):
    """
    Recursively simulate scheduling events from the given state.
    Returns a list of final SimulationState objects (where waiting and running are empty).
    """
    results = []
    
    # Dispatch event: if there are waiting tasks and a free core, dispatch the next task.
    if state.waiting and (len(state.running) < m):
        next_state = state.clone()
        task_id = next_state.waiting.pop(0)  # dispatch the first waiting task
        ft_min, ft_max, exec_min, exec_max, dispatch_idx = tasks_info[task_id]
        start_possible = state.current_time + exec_min
        end_possible = state.current_time + exec_max
        effective_lower = max(start_possible, ft_min)
        effective_upper = min(end_possible, ft_max)
        if effective_lower > effective_upper:
            # This branch is infeasible.
            return []
        # Branch on the two endpoints.
        for finish_time in (effective_lower, effective_upper):
            branch = next_state.clone()
            branch.running.append((task_id, finish_time, dispatch_idx))
            branch.running.sort(key=lambda t: (t[1], t[2], t[0]))
            results.extend(simulate_state(branch))
        return results

    # Finishing event: if no dispatch is possible but there are running tasks, jump to the next finish time.
    if state.running:
        next_time = min(task[1] for task in state.running)
        finishing = [t for t in state.running if t[1] == next_time]
        finishing.sort(key=lambda t: t[2])  # tie-break by dispatch order
        finished_ids = tuple(t[0] for t in finishing)
        new_state = state.clone()
        new_state.running = [t for t in new_state.running if t[1] != next_time]
        # Update aggregated finish times.
        for tid in finished_ids:
            if tid in new_state.agg:
                old_min, old_max = new_state.agg[tid]
                new_state.agg[tid] = (min(old_min, next_time), max(old_max, next_time))
            else:
                new_state.agg[tid] = (next_time, next_time)
        new_state.prefix = new_state.prefix + finished_ids
        new_state.current_time = next_time
        return simulate_state(new_state)

    # Terminal state: no waiting and no running.
    results.append(state)
    return results


def simulate_dispatch_order(dispatch_order):
    """
    Given a full dispatch order, initialize the simulation state and run the simulation.
    Returns a list of final SimulationState objects.
    """
    init_tasks_info(dispatch_order)
    init_state = SimulationState(prefix=(), current_time=0,
                                 waiting=list(dispatch_order),
                                 running=[], agg={})
    return simulate_state(init_state)


# ---------------------------
# Extension: re-use intermediate states
# ---------------------------
def extend_states_from_final(states, extended_dispatch_order):
    """
    Given a list of final states computed from a partial dispatch order, extend each state by
    updating its waiting list to be those tasks (from extended_dispatch_order) not already finished.
    Then resume simulation from that updated state.
    
    This function re-uses the simulation work done in the partial states.
    """
    new_states = []
    for st in states:
        # The finished tasks are in st.prefix.
        # Compute new waiting list as the tasks in the extended dispatch order that are not finished.
        new_waiting = [tid for tid in extended_dispatch_order if tid not in st.prefix]
        new_state = st.clone()
        new_state.waiting = new_waiting
        new_states.extend(simulate_state(new_state))
    return new_states


# ---------------------------
# Main demonstration
# ---------------------------
def main():
    # Example: partial simulation (v9) with dispatch order = ["t1", "t6", "t9"]
    dispatch_order_v9 = ["t1", "t6", "t9"]
    print("Simulating state v9 with dispatch order:", dispatch_order_v9)
    states_v9 = simulate_dispatch_order(dispatch_order_v9)
    for st in states_v9:
        ordering = " -> ".join(st.prefix)
        print("v9 final state:", ordering, st.agg)
    
    # Now, suppose we extend the dispatch order.
    # For example, the full dispatch order (v10) is:
    dispatch_order_v10 = ["t1", "t6", "t9", "t2"]
    print("\nSimulating full dispatch order from scratch (v10):", dispatch_order_v10)
    full_states = simulate_dispatch_order(dispatch_order_v10)
    for st in full_states:
        ordering = " -> ".join(st.prefix)
        print("Full state:", ordering, st.agg)
    
    # Now, extend the states computed for v9 using the new dispatch order.
    # (In other words, reuse the v9 simulation and then process the additional tasks.)
    extended_states = extend_states_from_final(states_v9, dispatch_order_v10)
    print("\nExtended states (from v9 to v10):")
    for st in extended_states:
        ordering = " -> ".join(st.prefix)
        print("Extended state:", ordering, st.agg)


if __name__ == "__main__":
    start = time.time()
    main()
    print("\nTotal Execution Time: {:.4f} seconds".format(time.time()-start))
