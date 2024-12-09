import csv
import os


def get_job_dict(path):
    """
    Reads a csv that has the following format:
    Ji_j, r_min, r_max, C_min, C_max, p

    Ji_j = the jth job of the ith task
    r_min = min release time
    r_max = max release time
    C_min = best-case execution time (BCET)
    C_max = worst-case execution time (WCET)
    p = priority (which must be unique)
    """
    csv_file = open(path, "r")
    reader = csv.reader(csv_file, delimiter=",")
    result = {}
    for row in reader:
        key = row[0].strip()  # Get the first column as the key (e.g., "J15")
        values = {
            "r_min": int(row[1]),
            "r_max": int(row[2]),
            "C_min": int(row[3]),
            "C_max": int(row[4]),
            "p": int(row[5]),
        }

        result[key] = values

    return result


def get_job_dict2(path) -> dict:
    """
    Reads a csv that has the following format:
    task id, job id, r_min, r_max, C_min, C_max, d, p

    task id = the task identifier to which the job belongs
    job id = the unique job identifier
    r_min = min release time
    r_max = max release time
    C_min = best-case execution time (BCET)
    C_max = worst-case execution time (WCET)
    d = deadline
    p = priority (which must be unique)
    """
    assert is_job_set_csv(path) == True

    csv_file = open(path, "r")
    reader = csv.reader(csv_file, delimiter=",")
    result = {}
    first_row = next(reader)

    for row in reader:
        task = row[0].strip()
        job = row[1].strip()
        key = f"J{task}_{job}"

        values = {
            "r_min": int(row[2]),
            "r_max": int(row[3]),
            "C_min": int(row[4]),
            "C_max": int(row[5]),
            "d": int(row[6]),
            "p": int(row[7]),
        }

        result[key] = values

    return result


def get_pred(path):
    """
    Reads a csv that has the following format:
    Ji_j, Ja_b, Jc_d, ...

    Ji_j = the jth job of the ith task which is in the set of all jobs J
    Ja_b, Jc_d, etc = jobs that are in the set of all jobs on which Ji_j depends
    """
    PRED = dict()
    csv_file = open(path, "r")
    reader = csv.reader(csv_file, delimiter=",")
    # first_row = next(reader)

    for row in reader:
        key = row[0].strip()  # Get the first column as the key (e.g., "J15")
        values = set(
            map(str, row[1:])
        )  # Convert the remaining columns to strings and make a tuple
        PRED[key] = values

    return PRED


def get_pred2(path) -> dict:
    """
    Reads a csv that has the following format:
    Predecessor TID, Predecessor JID, Successor TID, Successor JID

    The csv shall define a dependency DAG where one line in the csv represents an edge in the DAG.
    The output is a dictionary PRED which holds the set of precedence constraints for each key.
    PRED[j] is the set of all jobs that must complete before job j can be released.
    """
    assert is_pred_set_csv(path) == True

    PRED = dict()
    csv_file = open(path, "r")
    reader = csv.reader(csv_file, delimiter=",")
    first_row = next(reader)

    for row in reader:
        task_pred = row[0].strip()
        job_pred = row[1].strip()
        task_succ = row[2].strip()
        job_succ = row[3].strip()
        key = f"J{task_succ}_{job_succ}"
        value = f"J{task_pred}_{job_pred}"

        if key in PRED:
            PRED[key].add(value)
        else:
            PRED[key] = set([value])

    return PRED


def is_job_set_csv(path: str) -> bool:
    """
    Checks whether a given csv file via a path follows the job set csv specification.
    """

    if os.path.isfile(path) == False:
        raise ValueError("The given path doesn't exist!")

    file = open(path)
    reader = csv.reader(file, delimiter=",")
    job_ids = list()
    first_row = next(reader)
    first_row = [s.strip().lower() for s in first_row]

    if first_row != [
        "task id",
        "job id",
        "arrival min",
        "arrival max",
        "cost min",
        "cost max",
        "deadline",
        "priority",
    ]:
        raise ValueError(
            "First column is incorrect! It should be (case insensitive):\
                [Task ID, Job ID, Arrival min, Arrival max, Cost min, Cost max, Deadline, Priority]"
        )

    for index, row in enumerate(reader):
        if len(row) != 8:
            raise ValueError(
                f"Row {index} has {len(row)} columns instead of 8! In csv file at {path}"
            )

        for val in row:
            try:
                int(val)
            except ValueError:
                raise ValueError(
                    f"Row {index}'s values cannot be converted to int! In csv file at {path}"
                )

        job_ids.append(int(row[1]))

    if len(job_ids) != len(set(job_ids)):
        raise ValueError(f"There are jobs with the same ID in the csv file at {path}")

    return True


def is_pred_set_csv(path: str) -> bool:
    """
    Checks whether a given csv file via a path follows the predecessor set csv specification.
    """

    if os.path.isfile(path) == False:
        raise ValueError("The given path doesn't exist!")

    file = open(path)
    reader = csv.reader(file, delimiter=",")
    first_row = next(reader)
    first_row = [s.strip().lower() for s in first_row]

    if first_row != [
        "predecessor tid",
        "predecessor jid",
        "successor tid",
        "successor jid",
    ]:
        raise ValueError(
            "First column is incorrect! It should be (case insensitive):\
                [predecessor tid, predecessor jid, successor tid, successor jid]"
        )

    for index, row in enumerate(reader):
        if len(row) != 4:
            raise ValueError(
                f"Row {index} has {len(row)} columns instead of 4! In csv file at {path}"
            )

        for val in row:
            try:
                int(val)
            except ValueError:
                raise ValueError(
                    f"Row {index}'s values cannot be converted to int! In csv file at {path}"
                )

    return True
