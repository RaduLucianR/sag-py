import drawpyo
import csv
import random
import os
import argparse

TIME_UNIT = 40


class Colors:
    LIGHTBLUE = "#dae8fc"
    LIGHTRED = "#f8cecc"

    @staticmethod
    def random_color():
        r = random.randint(50, 205)
        g = random.randint(50, 205)
        b = random.randint(50, 205)

        # Convert to hex
        return f"#{r:02x}{g:02x}{b:02x}"


def draw_horizontal_line(x: int, y: int):
    head = drawpyo.diagram.object_from_library(
        page=PAGE,
        library="general",
        obj_name="rectangle",
        value="",
        width=0,
        height=0,
        position=(x, y),
    )
    tail = drawpyo.diagram.object_from_library(
        page=PAGE,
        library="general",
        obj_name="rectangle",
        value="",
        width=0,
        height=0,
        position=(x + TIMELINE_LENGTH * TIME_UNIT, y),
    )

    dummy_style = "rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=none;strokeWidth=0;"
    head.apply_style_string(dummy_style)
    tail.apply_style_string(dummy_style)
    line_style = "endArrow=none;html=1;rounded=0;"
    arrow = drawpyo.diagram.Edge(
        page=PAGE,
        source=tail,
        target=head,
    )
    arrow.apply_style_string(line_style)


def draw_release_arrow(x: int, y: int, arrow_length=40):
    head = drawpyo.diagram.object_from_library(
        page=PAGE,
        library="general",
        obj_name="rectangle",
        value="",
        width=0,
        height=0,
        position=(x, y),
    )
    tail = drawpyo.diagram.object_from_library(
        page=PAGE,
        library="general",
        obj_name="rectangle",
        value="",
        width=0,
        height=0,
        position=(x, y + arrow_length),
    )

    dummy_style = "rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=none;strokeWidth=0;"

    head.apply_style_string(dummy_style)
    tail.apply_style_string(dummy_style)
    arrow = drawpyo.diagram.Edge(
        page=PAGE,
        source=tail,
        target=head,
    )


def draw_time_indicies(y: int):
    for i in range(TIMELINE_LENGTH + 1):
        time_text = drawpyo.diagram.object_from_library(
            page=PAGE,
            library="general",
            obj_name="text",
            value=f"{i}",
            width=0,
            height=0,
            position=(i * TIME_UNIT - 5, TIME_UNIT * y),
        )


def draw_task(task_number: int, period: int, wcet: int, color: str):
    nrof_jobs = TIMELINE_LENGTH // period
    job_height = 20
    job_style = f"rounded=0;whiteSpace=wrap;html=1;fillColor={color};strokeColor=#6c8ebf;strokeWidth=0;"
    y_offset = (task_number - 1) * (TIME_UNIT * 2)
    width = TIME_UNIT * wcet

    for i in range(nrof_jobs + 1):
        x = TIME_UNIT * period * i

        if x + width < TIMELINE_LENGTH * TIME_UNIT:
            job = drawpyo.diagram.object_from_library(
                page=PAGE,
                library="general",
                obj_name="rectangle",
                value="",
                width=width,
                height=job_height,
                position=(x, job_height + y_offset),
            )
            job.apply_style_string(job_style)

        draw_release_arrow(x, y_offset)

    draw_horizontal_line(0, 40 + y_offset)
    draw_time_indicies(2 * task_number - 1)

    task_number_str = str(task_number)
    task_info_str = (
        r"$$\tau_"
        + str(task_number)
        + r": T="
        + str(period)
        + r", C="
        + str(wcet)
        + r"$$"
    )
    task_info = drawpyo.diagram.object_from_library(
        page=PAGE,
        library="general",
        obj_name="text",
        value=task_info_str,
        width=3 * TIME_UNIT,
        height=40,
        position=(-3 * TIME_UNIT, 15 + y_offset),
    )


def split_path(file_path):
    directory, file_name = os.path.split(file_path)
    return directory + os.sep, file_name


def generate_diagram(
    input_file="tasks.csv", output_file="./file.drawio", timeline_length=20
):
    global FILE, PAGE, TIMELINE_LENGTH

    path, file = split_path(output_file)
    TIMELINE_LENGTH = timeline_length
    FILE = drawpyo.File()
    FILE.file_path = path
    FILE.file_name = file
    PAGE = drawpyo.Page(file=FILE)

    fd = open(input_file, "r")
    csv_file = csv.reader(fd)

    for task in csv_file:
        draw_task(
            int(task[0]),
            period=int(task[1]),
            wcet=int(task[4]),
            color=Colors.random_color(),
        )

    FILE.write()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "csv",
        help="CSV with tasks. Each row contains a task: task_number, period, jitter, BCET, WCET.",
    )
    parser.add_argument("drawio_file", help="The generated drawio file.")
    parser.add_argument(
        "timeline_length",
        help="How long should the timeline be? How many time units should be drawn?",
        type=int,
    )
    args = parser.parse_args()

    generate_diagram(args.csv, args.drawio_file, args.timeline_length)
    print(f"Generated drawio file at {args.drawio_file}")
