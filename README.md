# Schedule-Abstraction Graph in Python

Schedule-abstraction graph (SAG) is a reachability-based response-time analysis for real-time systems.

This is the unofficial implementation of the SAG in Python. This is still WIP (Work-in-Progress). The implemented SAG follows the following paper:
- M. Nasri, G. Nelissen, and B. Brandenburg, “[Response-Time Analysis of Limited-Preemptive Parallel DAG Tasks under Global Scheduling](https://drops.dagstuhl.de/storage/00lipics/lipics-vol133-ecrts2019/LIPIcs.ECRTS.2019.21/LIPIcs.ECRTS.2019.21.pdf)”, Proceedings of the 31st Euromicro Conference on Real-Time Systems (ECRTS 2019), pp. 21:1–21:23, July 2019.

You can visit the official repository [here](https://github.com/SAG-org/schedule_abstraction-main).

### Run example
1. Clone the repository and run the `sagpy.py` script on a `csv` file that contains a set of jobs. A job is a tuple: `(name, r_min, r_max, C_min, C_max, p)`. The SAG for regular JLFP WC schedulers is run by default. Use the `--ROS` flag to run the SAG for the ROS2 executor with (by default) 2 threads. The algorithm prints to console the best response times and worst response times for the given jobs, and makes a `png` image with the constructed SAG so you can see exactly the state-transition system.
```
python3 -m src.sagpy.sagpy examples/input_examples/job_sets/ex_meeting.csv --algorithm ros
```

Output files are by default generated in the `~/USER/.sagpy` folder.
