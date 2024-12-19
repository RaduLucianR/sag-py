import networkx as nx
import matplotlib.pyplot as plt
import argparse
import csv
import time
import os
import pickle
import logging

from sagpy.generate_jobs import generate_jobs
from sagpy.drawio_diagram import generate_diagram
from sagpy.utils import *
from sagpy.sag_algorithms import ALGORITHMS


def main():
    # Command-Line Tool setup
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "PATH_TO_CSV",
        help="The csv that contains a list of jobs.\
              The csv follows the format specified on the official SAG repository.",
        type=str,
    )
    parser.add_argument(
        "--algorithm",
        help="The specific SAG algorithm to be used. There are currently only two options: standard or ROS.\
              The standard SAG algorithm refers to the one described in the ECRTS 2019 paper. The default is standard",
        choices=ALGORITHMS.keys(),
        required=True,
        type=str,
    )
    parser.add_argument(
        "--output-folder",
        help="Folder where the output information is stored after each run of the selected SAG algorithm.\
              The default is ~/.sagpy/",
        default="~/.sagpy/",
    )
    parser.add_argument(
        "--run-name",
        help="The name of the folder that will contain the output for this run of the SAG algorithm.",
        default="",
        type=str,
    )
    parser.add_argument(
        "--logging_level",
        help="The desired logging level. By default it's INFO.",
        default="info",
        choices=["info", "debug", "disable"],
        type=str,
    )
    parser.add_argument(
        "--pred", help="Path to csv with predecessor constraints", default="", type=str
    )
    parser.add_argument(
        "--cores",
        help="Number of cores that the SAG algorithm should consider for analysis.",
        default=2,
        type=int,
    )
    parser.add_argument(
        "--drawio",
        help="Set it to generate a drawio file with the task/job-release pattern.",
        action="store_true",
    )
    parser.add_argument(
        "--pickle",
        help="Set it to save the SAG graph as a pickle file.",
        action="store_true",
    )
    parser.add_argument(
        "--tasks_end_time",
        help="If you want to pass as input a csv with tasks instead of jobs,\
            then set the latest simulation time until which the tool should analyze.",
        default=0,
        type=int,
    )
    args = parser.parse_args()

    # Logger setup
    app_name = "SAGPY"
    logger = logging.getLogger(app_name)
    console_handler = logging.StreamHandler()
    log_format = f"[{app_name}] %(levelname)s: %(message)s"
    formatter = logging.Formatter(log_format)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    if args.logging_level == "info":
        logger.setLevel(logging.INFO)
    elif args.logging_level == "debug":
        logger.setLevel(logging.DEBUG)
    elif args.logging_level == "disable":
        logger.disable(logging.CRITICAL)

    # Output folder setup
    output_folder = os.path.expanduser(args.output_folder)
    run_name = f"run_{round(time.time())}" if args.run_name == "" else args.run_name
    output_folder = os.path.join(output_folder, run_name)
    if os.path.isdir(output_folder) == True:
        output_folder = os.path.join(output_folder, f"run_{round(time.time())}")
        logger.warning(
            f"Output folder already exists! Instead, we're making a new folder at {output_folder}"
        )
    os.makedirs(output_folder)

    # Inputs for SAG algorithms
    J = set()  # Set of jobs
    JDICT = dict()  # Dictionary of jobs which contains all info about each job
    PRED = dict()  # Dictionary that has the precedence constraints for each job
    m = int()  # Number of cores

    if args.tasks_end_time > 0:
        logger.info("Processing CSV with TASKS...")
        jobs_csv_path = os.path.join(output_folder, "jobs.csv")
        generate_jobs(args.PATH_TO_CSV, jobs_csv_path, args.tasks_end_time, True)
        logger.info(f"Generated CSV with JOBS at {jobs_csv_path}!")
        JDICT = get_job_dict(jobs_csv_path)

        if args.drawio == True:
            drawio_path = os.path.join(output_folder, "tasks.drawio")
            generate_diagram(args.PATH_TO_CSV, drawio_path, args.tasks_end_time)
            logger.info(f"Generated drawio file for TASKS at {drawio_path}!")
    else:
        logger.info("Processing CSV with JOBS...")
        try:
            JDICT = get_job_dict2(args.PATH_TO_CSV)
        except:
            JDICT = get_job_dict(args.PATH_TO_CSV)

    list_of_jobs = JDICT.keys()
    J = set(list_of_jobs)
    PRED = {j: set() for j in list_of_jobs}
    m = args.cores

    if args.pred != "":
        try:
            aux_PRED = get_pred2(args.pred)
        except:
            aux_PRED = get_pred(args.pred)

        for k in aux_PRED.keys():
            PRED[k] = aux_PRED[k]

    # Run the SAG algorithm
    algorithm = ALGORITHMS.get(args.algorithm)
    logger.info(f"Running {args.algorithm} SAG algorithm...")
    G, BR, WR = algorithm(J, m, JDICT, PRED, logger)
    # This assumes that every node has a field 'state'. TODO: This might not be the case, fix it or assert it!
    node_labels = {node: f"{data['state']}" for node, data in G.nodes(data=True)}
    edge_labels = {(u, v): f"{data['job']}" for u, v, data in G.edges(data=True)}
    logger.info(f"DONE!")

    # Write drawio file from job csv
    if args.drawio == True:
        drawio_path = os.path.join(output_folder, "jobs.drawio")
        generate_diagram(args.PATH_TO_CSV, drawio_path)
        logger.info(f"Generated drawio file for JOBS at {drawio_path}!")

    # Save SAG as a pickle file
    if args.pickle == True:
        pickle_path = os.path.join(output_folder, "graph.pkl")
        with open(pickle_path, "wb+") as f:
            pickle.dump(G, f)
        logger.info(f"Saved SAG as pickle at {pickle_path}")

    # Write BR and WR to csv
    csv_path = os.path.join(output_folder, "response_times.csv")
    csv_file = open(csv_path, "w+")
    writer = csv.writer(csv_file)
    for j in list_of_jobs:
        row = [j, BR[j], WR[j]]
        writer.writerow(row)
    csv_file.close()
    logger.info(f"BCRT and WCRT saved at {csv_path}!")

    # Draw SAG and save to file
    plt.figure(figsize=(30, 25))
    pos = nx.nx_agraph.graphviz_layout(G, prog="dot", args="-Gnodesep=1 -Granksep=2")
    nx.draw(G, pos, with_labels=False, node_color="lightblue", node_size=500)
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=20)
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=20)
    fig_path = os.path.join(output_folder, "sag.png")
    logger.info(f"Saving SAG as PNG...")
    plt.savefig(fig_path, dpi=300, bbox_inches="tight")
    logger.info(f"SAG figure saved at {fig_path}!")


if __name__ == "__main__":
    main()
