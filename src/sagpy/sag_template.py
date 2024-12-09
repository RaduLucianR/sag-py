import inspect
import logging
import networkx


def sag_algorithm(func):
    """
    Decorator that ensures a function is a "proper" SAG algorithm.
    "Proper" is defined according to the requirements of the sagpy CLI.
    """

    def wrapper(
        J: set, m: int, JDICT: dict, PRED: dict, logger: logging.Logger
    ) -> tuple[networkx.DiGraph, dict, dict]:
        base_name = "SAG algorithm"
        sig = inspect.signature(func)
        params = sig.parameters

        if list(params.keys()) != ["J", "m", "JDICT", "PRED", "logger"]:
            raise TypeError(
                f"{base_name} must have the following parameters\
                    J: set,\n\
                    m: int,\n\
                    JDICT: dict,\n\
                    PRED: dict[set],\n\
                    logger: logging.Logger"
            )

        if params["J"].annotation != set:
            raise TypeError(f"Parameter 'J' of {base_name} must be of type set!")

        if params["m"].annotation != int:
            raise TypeError(f"Parameter 'm' of {base_name} must be of type int!")

        if params["JDICT"].annotation != dict:
            raise TypeError(f"Parameter 'JDICT' of {base_name} must be of type dict!")

        if params["PRED"].annotation != dict:
            raise TypeError(f"Parameter 'PRED' of {base_name} must be of type dict!")

        # TODO: This is too strict (because it checks for an annotation). Fix it with a type check.
        # if params["logger"].annotation != logging.Logger:
        #     raise TypeError(
        #         f"Parameter 'logger' of {base_name} must be of type logging.Logger!"
        #     )

        if sig.return_annotation != tuple[networkx.DiGraph, dict, dict]:
            raise TypeError(
                f"{base_name} must return a tuple of type (networkx.DiGraph, dict, dict)"
            )

        return func(J, m, JDICT, PRED, logger)

    wrapper._is_sag_algorithm = True
    return wrapper
