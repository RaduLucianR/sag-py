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


def draw_release_jitter_arrow(x: int, y: int, x_release: int, arrow_length=40):
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
    arrow_style = "endArrow=classic;html=1;rounded=0;dashed=1;"
    dotted_line_style = (
        "endArrow=none;dashed=1;html=1;dashPattern=1 3;strokeWidth=2;rounded=0;"
    )

    head.apply_style_string(dummy_style)
    tail.apply_style_string(dummy_style)
    arrow = drawpyo.diagram.Edge(
        page=PAGE,
        source=tail,
        target=head,
    )
    arrow.apply_style_string(arrow_style)

    head_dotted_line = drawpyo.diagram.object_from_library(
        page=PAGE,
        library="general",
        obj_name="rectangle",
        value="",
        width=0,
        height=0,
        position=(x_release, y + arrow_length / 2),
    )
    tail_dotted_line = drawpyo.diagram.object_from_library(
        page=PAGE,
        library="general",
        obj_name="rectangle",
        value="",
        width=0,
        height=0,
        position=(x, y + arrow_length / 2),
    )
    dotted_line = drawpyo.diagram.Edge(
        page=PAGE,
        source=head_dotted_line,
        target=tail_dotted_line,
    )
    dotted_line.apply_style_string(dotted_line_style)


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


def draw_task(
    task_number: int,
    period: int,
    jitter: int,
    bcet: int,
    wcet: int,
    color: str,
    nrof_jobs: int,
):
    job_height = 20
    job_style = f"rounded=0;whiteSpace=wrap;html=1;fillColor={color};strokeColor=#6c8ebf;strokeWidth=0;"
    y_offset = (task_number - 1) * (TIME_UNIT * 2)
    width = TIME_UNIT * wcet

    for i in range(nrof_jobs + 1):
        x = TIME_UNIT * (period * i)
        x_jitter = x + TIME_UNIT * jitter

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

        if x < x_jitter:
            draw_release_jitter_arrow(x_jitter, y_offset, x)

    draw_horizontal_line(0, 40 + y_offset)
    draw_time_indicies(2 * task_number - 1)

    task_number_str = str(task_number)
    task_info_str = (
        r"$$\tau_"
        + str(task_number)
        + r": T="
        + str(period)
        + r", C=["
        + str(bcet)
        + r","
        + str(wcet)
        + r"]$$"
    )
    task_info = drawpyo.diagram.object_from_library(
        page=PAGE,
        library="general",
        obj_name="text",
        value=task_info_str,
        width=3 * TIME_UNIT,
        height=40,
        position=(-4 * TIME_UNIT, 15 + y_offset),
    )


def split_path(file_path):
    directory, file_name = os.path.split(file_path)
    return directory + os.sep, file_name


def generate_diagram(
    input_file="tasks.csv",
    output_file="./file.drawio",
    timeline_length=5,
):
    global FILE, PAGE, TIMELINE_LENGTH

    is_task_csv = True
    path, file = split_path(output_file)
    FILE = drawpyo.File()
    FILE.file_path = path
    FILE.file_name = file
    PAGE = drawpyo.Page(file=FILE)

    fd = open(input_file, "r")
    csv_file = csv.reader(fd)

    if len(next(csv_file)) == 6:
        is_task_csv = False
    fd.seek(0)

    if is_task_csv == True:
        # Set the TIMELINE_LENGTH to the latest finish time of any job and pad it with one more unit
        max_time_idx = 0
        for t in csv_file:
            period = int(t[1])
            wcet = int(t[4])
            nrof_jobs = timeline_length // period
            max_time_idx = max(period * nrof_jobs + wcet, max_time_idx)
        TIMELINE_LENGTH = max_time_idx + 1
        fd.seek(0)

        fd = open(input_file, "r")
        csv_file = csv.reader(fd)

        for task in csv_file:
            nrof_jobs = timeline_length // int(task[1])
            draw_task(
                int(task[0]),
                period=int(task[1]),
                jitter=int(task[2]),
                bcet=int(task[3]),
                wcet=int(task[4]),
                color=Colors.random_color(),
                nrof_jobs=nrof_jobs,
            )
        fd.close()
    else:
        tasks = dict()

        # Set the TIMELINE_LENGTH to the latest finish time of any job and pad it with one more unit
        max_time_idx = 0
        for j in csv_file:
            r_min = int(j[1])
            C_max = int(j[4])
            max_time_idx = max(r_min + C_max, max_time_idx)
        TIMELINE_LENGTH = max_time_idx + 1
        fd.seek(0)

        for job in csv_file:
            name = job[0]  # Jx_y i.e. yth job of xth task
            task = int(name[1])
            job_nr = int(name[3])
            r_min = int(job[1])
            r_max = int(job[2])
            C_min = int(job[3])
            C_max = int(job[4])
            jitter = r_max - r_min
            draw_task_check = False

            if task not in tasks.keys():
                tasks[task] = Colors.random_color()
                draw_task_check = True

            x = TIME_UNIT * r_min
            x_jitter = x + TIME_UNIT * jitter
            width = TIME_UNIT * C_max
            job_height = 20
            y_offset = (task - 1) * (TIME_UNIT * 2)
            job_style = f"rounded=0;whiteSpace=wrap;html=1;fillColor={tasks[task]};strokeColor=#6c8ebf;strokeWidth=0;"

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

            if x < x_jitter:
                draw_release_jitter_arrow(x_jitter, y_offset, x)

            if draw_task_check == True:
                draw_task(task, 0, jitter, C_min, C_max, "", -1)

        fd.close()

    FILE.write()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "csv",
        help="CSV with tasks. Each row contains a task: task_number, period, jitter, BCET, WCET.",
    )
    parser.add_argument("drawio_file", help="The generated drawio file.")
    parser.add_argument(
        "-l",
        "--latest_job_release_time",
        help="What time is released the last job that you want drawn?",
        type=int,
        default=5,
    )
    args = parser.parse_args()

    generate_diagram(args.csv, args.drawio_file, args.latest_job_release_time)
    print(f"Generated drawio file at {args.drawio_file}")
