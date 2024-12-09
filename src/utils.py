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


def is_job_set_csv(path: str):
    """
    Checks whether a given csv file via a path follows the job set csv specification.
    """

    if os.path.isfile(path) == False:
        raise ValueError("The given path doesn't exist!")

    file = open(path)
    reader = csv.reader(file, delimiter=",")
    job_ids = list()

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


is_job_set_csv("/home/radu/repos/rtas2019/src/hey.csv")
