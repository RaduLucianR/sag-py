# Schedule-Abstraction Graph in Python

Schedule-abstraction graph (SAG) is a reachability-based response-time analysis for real-time systems.

This is the unofficial implementation of the SAG in Python. You can visit the official repository [here](https://github.com/SAG-org/schedule_abstraction-main). This is still WIP (Work-in-Progress) - you can run the anaysis but it doesn't scale because path merging is not implemented yet. The implemented SAG follows the following paper:
- M. Nasri, G. Nelissen, and B. Brandenburg, “[Response-Time Analysis of Limited-Preemptive Parallel DAG Tasks under Global Scheduling](https://drops.dagstuhl.de/storage/00lipics/lipics-vol133-ecrts2019/LIPIcs.ECRTS.2019.21/LIPIcs.ECRTS.2019.21.pdf)”, Proceedings of the 31st Euromicro Conference on Real-Time Systems (ECRTS 2019), pp. 21:1–21:23, July 2019.

### For Users
1. Install the package with:
```
pip install sagpy
```

2. Use the `sagpy` Command-Line Interface (CLI) to run the SAG analysis on a set of jobs from a csv file. You must select what SAG algorithm to use. For now there are only 2: `ecrts2019` (the one presented in the paper above) and `ros` (based on ecrts2019, but adapted to analyze ROS2's executor):
```
sagpy overlapping_release_intervals.csv --algorithm ecrts2019
```

3. Output files are by default generated in the `~/USER/.sagpy` folder. 

By default the script generates a csv 
containing the Best Response times (BR) and the Worst Response times (WR) for all given jobs. Moreover, a png with
the visual representation of the SAG is generated as well. Optionally, you can add `--drawio` to generate a drawio
file with a job release plot, so you can better visualize the interference between jobs. Also optionally, the SAG
can be serialized with `pickle` and saved for later use, e.g. making ground truths for testing.

### For Developers
1. Clone the repository.
```
git clone https://github.com/RaduLucianR/sag-py.git
```
2. Change directory in the root folder of the repository.
```
cd sag-py
```
3. Install the package locally. This allows you to run the scripts like they'd be run by the OS. Even if you make changes in the scripts, these
changes will be taken into account when Python runs the script again after install.
```
pip install -e . --break-system-package
```

4. Run the CLI script `sagpy` on a `csv` file that contains a set of jobs:
```
python3 -m src.sagpy.sagpy examples/input_examples/job_sets/overlapping_release_intervals.csv --algorithm ecrts2019
```
5. Output files are by default generated in the `~/USER/.sagpy` folder. 
6. Run the tests running `pytest` from the root directiory:
```
pytest
```