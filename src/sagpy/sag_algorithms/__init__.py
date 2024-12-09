import os
import importlib
import inspect
from typing import Callable

ALGORITHMS = {}


def register_algorithms():
    """
    Automatically load and register all SAG algorithm functions from modules in this directory.
    """

    algorithm_dir = os.path.dirname(__file__)
    for filename in os.listdir(algorithm_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]  # Remove ".py"
            module = importlib.import_module(f"sagpy.sag_algorithms.{module_name}")

            # Register all functions that have the sag_algorithm decorator applied
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if getattr(func, "_is_sag_algorithm", False):
                    ALGORITHMS[module_name] = func


register_algorithms()
