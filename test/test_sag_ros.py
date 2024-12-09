import os
import pickle
import pytest
import logging

from src.sag_algorithms.ros import ScheduleGraphConstructionAlgorithmROS
from utils import get_job_dict, get_pred

from networkx.algorithms.isomorphism import DiGraphMatcher


def get_inputs(jobs_path, cores, pred_path=""):
    assert os.path.isfile(jobs_path) == True
    assert os.path.isfile(pred_path) or pred_path == ""
    assert cores > 0

    JDICT = get_job_dict(jobs_path)
    list_of_jobs = JDICT.keys()
    J = set(list_of_jobs)
    PRED = {j: set() for j in list_of_jobs}

    if pred_path != "":
        PRED = get_pred(pred_path)

    return J, cores, JDICT, PRED


def get_output(out_path):
    assert os.path.isfile(out_path) == True

    G = None
    with open(out_path, "rb") as f:  # Open in binary read mode
        G = pickle.load(f)

    return G


def node_match(n1, n2):
    return (n1["state"].A == n2["state"].A) and (n1["state"].PP == n2["state"].PP)


def edge_match(e1, e2):
    return e1["job"] == e2["job"]


def SAG_match(jobs, expected_graph, cores):
    assert os.path.isfile(jobs) == True
    assert os.path.isfile(expected_graph) == True

    inputs = get_inputs(jobs, cores)
    G1 = ScheduleGraphConstructionAlgorithmROS(
        *inputs, logger=logging.Logger("SAGPY", logging.CRITICAL)
    )[0]
    G2 = get_output(expected_graph)
    matcher = DiGraphMatcher(G1, G2, node_match=node_match, edge_match=edge_match)

    return matcher.is_isomorphic()


def get_test_cases():
    test_cases = list()
    curr_dir_path = os.path.dirname(os.path.realpath(__file__))
    tests = os.path.join(curr_dir_path, "tests_sag_ros")

    for root, dirs, files in os.walk(tests):
        for test in dirs:
            test_dir = os.path.join(root, test)
            input_file = f"{test_dir}/jobs.csv"
            output_file = f"{test_dir}/sag.pkl"
            test_cases.append((input_file, output_file))

    return test_cases


# @pytest.mark.parametrize("input_file, output_file", get_test_cases())
# def tests_two_cores(input_file, output_file):
#     assert SAG_match(input_file, output_file, 2)


def tests1():
    assert SAG_match(
        "test/tests_sag_ros/test1/jobs.csv", "test/tests_sag_ros/test1/sag.pkl", 2
    )


def tests2():
    assert SAG_match(
        "test/tests_sag_ros/test2/jobs.csv", "test/tests_sag_ros/test2/sag.pkl", 2
    )


def tests3():
    assert SAG_match(
        "test/tests_sag_ros/test3/jobs.csv", "test/tests_sag_ros/test3/sag.pkl", 3
    )
