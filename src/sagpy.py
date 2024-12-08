import networkx as nx
import matplotlib.pyplot as plt
import argparse
import csv
import time
import os

from generate_jobs import generate_jobs
from drawio_diagram import generate_diagram

from sag_rtas2019 import ScheduleGraphConstructionAlgorithm
from sag_rosJazzy import ScheduleGraphConstructionAlgorithmROS


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("PATH")
    parser.add_argument("--algorithm", default="standard", type=str)
    parser.add_argument("--tasks_end_time", default=0, type=int)
    parser.add_argument("--pred", default="", type=str)
    parser.add_argument("--cores", default=2, type=int)
    parser.add_argument("--output-folder", default="~/.sagpy/")
    parser.add_argument("--drawio", action="store_true")
    parser.add_argument("--run-name", default="", type=str)
    args = parser.parse_args()

    output_folder = os.path.expanduser(args.output_folder)
    run_name = f"run_{round(time.time())}" if args.run_name == "" else args.run_name
    output_folder = os.path.join(output_folder, run_name)

    if os.path.isdir(output_folder):
        output_folder = os.path.join(output_folder, f"run_{round(time.time())}")
        print(
            f"[SAGPY] Output folder already exists! Instead, we're making a new folder at {output_folder}"
        )

    os.makedirs(output_folder)

    if args.tasks_end_time > 0:
        print("[SAGPY] Processing CSV with TASKS...")
        jobs_csv_path = os.path.join(output_folder, "jobs.csv")
        generate_jobs(args.PATH, jobs_csv_path, args.tasks_end_time, True)
        print(f"[SAGPY] Generated CSV with JOBS at {jobs_csv_path}!")

        JDICT = get_job_dict(jobs_csv_path)

        if args.drawio == True:
            drawio_path = os.path.join(output_folder, "tasks.drawio")
            generate_diagram(args.PATH, drawio_path, args.tasks_end_time)
            print(f"[SAGPY] Generated drawio file for TASKS at {drawio_path}!")
    else:
        print("[SAGPY] Processing CSV with JOBS...")
        JDICT = get_job_dict(
            args.PATH
        )  # Dictionary of jobs which contains all info about each job

    list_of_jobs = JDICT.keys()
    J = set(list_of_jobs)  # The set of all jobs

    PRED = {
        j: set() for j in list_of_jobs
    }  # Dictionary that has the precedence constraints for each job

    m = args.cores  # nr of cores

    if args.pred != "":
        get_pred(args.pred)
        print(PRED)

    if args.algorithm == "standard":
        print(f"[SAGPY] Running {args.algorithm} SAG algorithm...")
        G, BR, WR = ScheduleGraphConstructionAlgorithm(J, m, JDICT, PRED)
        node_labels = {node: f"{data['state'].A}" for node, data in G.nodes(data=True)}
        print(f"[SAGPY] DONE!")
    elif args.algorithm == "ROS":
        G, BR, WR = ScheduleGraphConstructionAlgorithmROS(J, m, JDICT, PRED)
        node_labels = {
            node: f"{data['state'].A}{data['state'].PP}"
            for node, data in G.nodes(data=True)
        }
    else:
        raise ValueError("The given algorithm option is not available!")

    # Write drawio file from job csv
    if args.drawio == True:
        drawio_path = os.path.join(output_folder, "jobs.drawio")
        generate_diagram(args.PATH, drawio_path)
        print(f"[SAGPY] Generated drawio file for JOBS at {drawio_path}!")

    # Write BR and WR to csv
    csv_path = os.path.join(output_folder, "response_times.csv")
    csv_file = open(csv_path, "w+")
    writer = csv.writer(csv_file)
    for j in list_of_jobs:
        row = [j, BR[j], WR[j]]
        writer.writerow(row)
    csv_file.close()
    print(f"[SAGPY] BCRT and WCRT saved at {csv_path}!")

    # Draw SAG and save to file
    edge_labels = {(u, v): f"{data['job']}" for u, v, data in G.edges(data=True)}
    plt.figure(figsize=(30, 25))  # Bigger figure
    pos = nx.nx_agraph.graphviz_layout(
        G, prog="dot", args="-Gnodesep=1 -Granksep=2"
    )  # Adjust spacing
    nx.draw(
        G, pos, with_labels=False, node_color="lightblue", node_size=500
    )  # Increase node size
    nx.draw_networkx_labels(
        G, pos, labels=node_labels, font_size=10
    )  # Smaller font size for labels
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels, font_size=8
    )  # Smaller edge label font
    fig_path = os.path.join(output_folder, "sag.png")
    plt.savefig(fig_path, dpi=300, bbox_inches="tight")

    print(f"[SAGPY] SAG figure saved at {fig_path}!")
