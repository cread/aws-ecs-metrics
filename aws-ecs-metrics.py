#!/usr/bin/env python

import docker
import json
import logging
import sys

from collections import defaultdict
from pprint import pformat
from time import sleep

import boto3

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


class Collector:

    def __init__(self):
        self.containers = docker.from_env().containers
        self.container_history = defaultdict(dict)


    def collect(self):
        containers = self.containers.list()

        # Prune out old history for stopped containers
        for stopped in [s for s in self.container_history if s not in [c.id for c in containers]]:
            self.container_history.pop(stopped)

        # Walk the container list and get stats for each
        for container in containers:
            logging.info("Container: {}".format(container.name))

            # We got the container list a few lines ago, that container may be dead by now...
            try:
                stats = container.stats(decode=True, stream=False)

                # Setup new containers if we've not seen them yet...
                if not container.id in self.container_history:
                    self.container_history[container.id]['name'] = container.name

            except (json.decoder.JSONDecodeError, docker.errors.NotFound):
                continue

            self.calcCpuPercent(container.id, stats)
            self.calcMem(container.id, stats)

        return self.container_history


    def calcCpuPercent(self, container_id, stats):
        """
        Ported from https://github.com/docker/docker-ce/blob/e947e4d4f1a55589a3eb4f049f51ddeddaf8c2da/components/cli/cli/command/container/stats_helpers.go#L168
        """
        cpuPercent = 0.0
        prevCpu = self.container_history[container_id].get('prevCpu', 0.0)
        prevSys = self.container_history[container_id].get('prevSys', 0.0)

        self.container_history[container_id]['prevCpu'] = stats['cpu_stats']['cpu_usage']['total_usage']
        self.container_history[container_id]['prevSys'] = stats['cpu_stats']['system_cpu_usage']

        cpuDelta = stats['cpu_stats']['cpu_usage']['total_usage'] - prevCpu
        sysDelta = stats['cpu_stats']['system_cpu_usage'] - prevSys
        onlineCpus = stats['cpu_stats']['online_cpus']

        if onlineCpus == 0.0:
            onlineCpus = float(len(stats['cpu_stats']['cpu_usage']['percpu_usage']))

        if sysDelta > 0.0 and cpuDelta > 0.0:
            cpuPercent = (cpuDelta / sysDelta) * onlineCpus * 100.0

        self.container_history[container_id]['cpuPercent'] = cpuPercent


    def calcMem(self, container_id, stats):
        """
        Ported from https://github.com/docker/docker-ce/blob/e947e4d4f1a55589a3eb4f049f51ddeddaf8c2da/components/cli/cli/command/container/stats_helpers.go#L228
        """
        usedNoCache = stats['memory_stats']['usage'] - stats['memory_stats']['stats']['cache']
        memPercent = usedNoCache / stats['memory_stats']['limit'] if stats['memory_stats']['limit'] != 0 else 0

        self.container_history[container_id]['memUsedNoCache'] = usedNoCache
        self.container_history[container_id]['memPercent'] = memPercent


def main(args):
    c = Collector()

    while True:
        sleep(5)
        logging.info(pformat(c.collect(), indent=4))


if __name__ == "__main__":
    sys.exit(main(sys.argv))

