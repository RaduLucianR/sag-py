import csv


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
        values = tuple(
            map(int, row[1:])
        )  # Convert the remaining columns to integers and make a tuple
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

    for row in reader:
        key = row[0].strip()  # Get the first column as the key (e.g., "J15")
        values = set(
            map(str, row[1:])
        )  # Convert the remaining columns to strings and make a tuple
        PRED[key] = values

    return PRED
