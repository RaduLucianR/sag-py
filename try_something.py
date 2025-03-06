# dispatch_order = ["t9", "t2", "t3", "t7"]
# Z_new = ["t2", "t3", "t7"]
# Z_old = ["t9"]

# dispatch_order = ["t9", "t7", "t4"]
# Z_new = ["t4"]
# Z_old = ["t9", "t7"]

dispatch_order = ["t1", "t6", "t9"]
Z_new = ["t1", "t6", "t9"]
Z_old = []

PO = dict()
counter = 1
for j in Z_new:
    PO[j] = counter
    counter += 1
print(PO)

card_Z = len(Z_old) + len(Z_new)

def if_j_triggers_pp_then_these_jobs_finish_before_pp(j: str, m: int):
    jobs = set()

    if j in PO:
        for k in PO:
            if PO[k] < PO[j]:
                jobs.add(k)
    else:
        counter = 0
        for k in PO:
            # TODO: add an 'if' -> if FT(k) \cap FT(j) != \varnothing
            if counter < m:
                jobs.add(k)
                counter += 1
    
    if len(jobs) < card_Z - m:
        for k in Z_old:
            jobs.add(k)
    
    if len(jobs) < card_Z - m:
        counter = len(jobs)
        for k in PO:
            if j != k and counter < card_Z - m:
                jobs.add(k)
                counter += 1
    
    return jobs.union(set([j]))

if __name__ == "__main__":
    m = 2

    for j in dispatch_order:
        a = if_j_triggers_pp_then_these_jobs_finish_before_pp(j, m)
        print(f"If {j} triggers a polling point, then all jobs {a} finish before the polling point")