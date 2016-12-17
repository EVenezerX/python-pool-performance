#!/usr/bin/env python3

from __future__ import print_function
from collections.abc import Mapping, Sequence
from collections import OrderedDict
from types import FunctionType
from tabulate import tabulate
from tqdm import tqdm
import textwrap
import numpy

import utils
from pools.eventlet import EventletPool
from pools.gevent import GeventPool
from pools.multiprocessing import MultiprocessingProcessPool, \
                                  MultiprocessingThreadPool
from pools.standard_library import StandardProcessPool, StandardThreadPool


def run_test(work_type: FunctionType, job_sets: Sequence, trials: int,
             pool_class: type, worker_count: int) -> Mapping:
    pool = pool_class(worker_count)
    if work_type == 'compute':
        test_func = pool.run_compute_test
    elif work_type == 'network':
        test_func = pool.run_network_test
    else:
        raise Exception("Invalid work type: {}".format(work_type))
    results = map(
        lambda jobs: test_func(jobs, trials, show_progress=True),
        tqdm(job_sets, desc=pool_class.__name__),
    )
    summarized_results = list(map(summarize_test, results))
    pool.destroy_pool()
    return summarized_results


def summarize_test(test_output: Mapping) -> Mapping:
    return {
        'jobs': test_output['jobs'],
        'time': numpy.mean(test_output['time']),
        'blocks': numpy.mean(test_output['blocks']),
    }


if __name__ == '__main__':
    import multiprocessing
    # Set up Multiprocessing start method
    # Some start methods depend on a clean process to fork from
    multiprocessing.set_start_method('spawn')
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--work-type', '-w', default='compute',
                        choices=['compute', 'network'],
                        help='The kind of work to perform in each pool')
    parser.add_argument('--max-work', '-m', type=int, default=4,
                        help='The power of 2 for number of jobs to execute. '
                             'For example, a choice of 4 will yield a maximum '
                             'of 2^4 jobs to run.')
    parser.add_argument('--trials', '-r', type=int, default=1,
                        help='The total number of times to run a test with '
                             'the same parameters')
    parser.add_argument('--samples', '-s', type=int, default=10,
                        help='The total number of samples to compute. '
                             'For example, 4 samples with max-work of 4 will '
                             'run each pool with 4, 8, 12, and then 16 jobs.')
    parser.add_argument('--concurrent-threads', '-t', type=int, default=50,
                        help='The number of concurrent threads to use in '
                             'each thread pool.')
    parser.add_argument('--concurrent-processes', '-p', type=int,
                        default=multiprocessing.cpu_count() * 2 + 1,
                        help='The number of concurrent processes to use in '
                             'each process pool. The default is (number of'
                             'processors * 2) + 1.')
    parser.add_argument('--no-graph', action='store_true', default=False,
                        help='Disable showing the graph of the results at the '
                             'end of execution.')
    args = parser.parse_args()

    if args.samples < 1:
        parser.error("Samples must be a positive integer")
    if args.trials < 1:
        parser.error("Trials must be a positive integer")

    pool_types = [
        (EventletPool, args.concurrent_threads),
        (GeventPool, args.concurrent_threads),
        (MultiprocessingProcessPool, args.concurrent_processes),
        (MultiprocessingThreadPool, args.concurrent_threads),
        (StandardProcessPool, args.concurrent_processes),
        (StandardThreadPool, args.concurrent_threads),
    ]

    max_jobs = 2 ** args.max_work
    trials = args.trials
    samples = args.samples
    job_step = int(max_jobs / samples)
    if job_step == 0:
        job_step = 1
    job_sets = range(0, max_jobs + 1, job_step)

    print(textwrap.dedent(
        """\
        Pool performance analysis configuration:

        maximum work:         2^{max_work} = {jobs} jobs
        concurrent processes: {concurrent_processes}
        concurrent threads:   {concurrent_threads}
        number of samples:    {samples}
        trials:               {trials}
        """.format(jobs=max_jobs, **vars(args))
    ))

    all_results = list(tqdm(
        map(
            lambda pool_class_tuple: run_test(
                args.work_type,
                job_sets,
                trials,
                *pool_class_tuple
            ),
            pool_types
        ),
        desc='Pool Analysis',
        total=len(pool_types),
    ))

    print("\n\n")

    all_results_dict = zip(
        map(lambda cls_tuple: cls_tuple[0].__name__, pool_types),
        all_results
    )
    # Sort iteration order of mapping
    all_results_dict = OrderedDict(sorted(all_results_dict))
    for class_name, result in all_results_dict.items():
        table = tabulate(result, headers='keys',
                         tablefmt='pipe')
        print("{}:\n{}\n\n".format(class_name, table))

    if args.no_graph is True:
        exit(0)

    from matplotlib import pyplot as plt

    plt.subplot(2, 1, 1)
    utils.plot_tuple_array(all_results_dict, 'jobs', 'time',
                           custom_y_label='completion time (s)')
    plt.title("run time vs job count")

    plt.subplot(2, 1, 2)
    utils.plot_tuple_array(all_results_dict, 'jobs', 'blocks',
                           custom_y_label='memory allocated (blocks)',
                           y_mapping=utils.lower_bound_immediate)
    plt.title("memory allocated vs job count")

    plt.tight_layout()
    plt.show()
