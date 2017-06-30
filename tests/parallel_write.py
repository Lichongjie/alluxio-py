#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script starts {nprocess} python processes in parallel, each process writes a local file stream into Alluxio.

By default, each python process has an ID consecutively starting from 0 to
{nprocess}.
For each process, the local file data/5mb.txt is written to Alluxio file
/{dst}/iteration_{iteration_id}/node_{node_id}/process_{ID}.

This script should be run from its parent directory.
"""

from __future__ import print_function
import argparse
from multiprocessing import Process
import os
import time

import syspath
import alluxio
from utils import alluxio_path, mkdir_p


def write(host, port, data, dst, write_type):
    """Write the {src} file in the local filesystem to the {dst} file in Alluxio.

    Args:
        host (str): The Alluxio proxy's hostname.
        port (int): The Alluxio proxy's web port.
        data (str): The file content of the source.
        dst (str): The file to be written to Alluxio.
        write_type (:class:`alluxio.wire.WriteType`): Write type for creating the file.

    Returns:
        The total time (seconds) used to read the local file and stream it to Alluxio.
    """

    start_time = time.time()
    c = alluxio.Client(host, port)
    with c.open(dst, 'w', recursive=True, write_type=write_type) as alluxio_file:
        alluxio_file.write(data)
    return time.time() - start_time


def run_write(args, data, iteration_id, process_id):
    dst = alluxio_path(args.dst, iteration_id, args.node, process_id)
    write_type = alluxio.wire.WriteType(args.write_type)
    write(args.host, args.port, data, dst, write_type)


def print_stats(args, total_time):
    src_bytes = os.stat(args.src).st_size
    average_time = total_time / args.iteration
    average_throughput = src_bytes / average_time

    print('Number of iterations: %d' % args.iteration)
    print('Number of processes per iteration: %d' % args.nprocess)
    print("File size: %d bytes" % src_bytes)
    print('Total time: %f seconds' % total_time)
    print('Average time for each iteration: %f seconds' % average_time)
    print('Average write throughput per python client: %f bytes/second' % average_throughput)


def main(args):
    with open(args.src, 'r') as f:
        data = f.read()

    total_time = 0
    for iteration in range(args.iteration):
        print('Iteration %d ... ' % iteration, end='')
        processes = []
        for process_id in range(args.nprocess):
            p = Process(target=run_write, args=(args, data, iteration, process_id))
            processes.append(p)
        start_time = time.time()
        for p in processes:
            p.start()
        for p in processes:
            p.join()
        elapsed_time = time.time() - start_time
        total_time += elapsed_time
        print('done')
    print_stats(args, total_time)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start multiple python processes to write local file to Alluxio in parallel')
    parser.add_argument('--nprocess', type=int, default=1,
                        help='number of python processes, each process runs write.py')
    parser.add_argument('--host', default='localhost',
                        help='Alluxio proxy server hostname')
    parser.add_argument('--port', type=int, default=39999,
                        help='Alluxio proxy server web port')
    parser.add_argument('--src', default='data/5mb.txt',
                        help='path to the local file source')
    parser.add_argument('--dst', default='/alluxio-py-test',
                        help='path to the root directory for all written file')
    parser.add_argument('--node', required=True,
                        help='a unique identifier of this node')
    parser.add_argument('--iteration', type=int, default=1,
                        help='number of iterations to repeat the concurrent writing')
    parser.add_argument('--write-type', default='MUST_CACHE',
                        help='write type for creating the file, see alluxio.wire.WriteType')
    args = parser.parse_args()

    mkdir_p('logs')

    main(args)
