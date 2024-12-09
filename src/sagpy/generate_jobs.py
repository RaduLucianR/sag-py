import csv
import argparse


def generate_jobs(
    input_path: str, output_path: str, latest_release=10, allow_instant_start=False
):
    """
    Generates a csv with jobs information from a given csv file with task information.

    Format input: TaskName, Period, StartJitter, Cmin, Cmax
    Format output: JobName, r_min r_max, C_min, C_max, p
    The task priority is the index of the row in the csv,
        i.e. the task's priority is inherent to its position in the csv.
    """
    fd = open(input_path, "r")
    csv_file = csv.reader(fd, delimiter=",")

    allow_instant_start = int(allow_instant_start)
    priority = 1
    jobs = []

    for task in csv_file:
        if len(task) != 5:
            raise ValueError("Each row must have exactly 5 values!")

        if type(task[0]) == int:
            raise ValueError("The name of a task must be an integer!")

        task_name, T, jitter, C_min, C_max = task
        T, jitter, C_min, C_max = int(T), int(jitter), int(C_min), int(C_max)
        job_counter = 1
        r_min = T * (job_counter - allow_instant_start)

        while r_min <= latest_release:
            job_name = f"J{task_name}_{job_counter}"
            r_max = r_min + jitter
            job = (job_name, r_min, r_max, C_min, C_max, priority)
            jobs.append(job)

            job_counter += 1
            priority += 1
            r_min = T * (job_counter - allow_instant_start)

    fd_write = open(output_path, "w+")
    writer = csv.writer(fd_write)

    for job in jobs:
        writer.writerow(job)

    fd.close()
    fd_write.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("output_file")
    parser.add_argument("latest_release_time")
    parser.add_argument("--allow-instant-start", action="store_true")
    args = parser.parse_args()

    generate_jobs(
        args.input_file,
        args.output_file,
        int(args.latest_release_time),
        args.allow_instant_start,
    )
