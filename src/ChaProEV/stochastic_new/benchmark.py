import os
import threading
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import psutil

P = ParamSpec('P')
R = TypeVar('R')


def benchmark(
    function: Callable[P, R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    process = psutil.Process(os.getpid())

    ram_before_bytes = process.memory_info().rss
    peak_ram_bytes = ram_before_bytes

    running = True

    def sample_memory() -> None:
        nonlocal peak_ram_bytes

        while running:
            ram_bytes = process.memory_info().rss
            peak_ram_bytes = max(peak_ram_bytes, ram_bytes)
            time.sleep(0.05)

    memory_thread = threading.Thread(target=sample_memory)
    memory_thread.start()

    cpu_start = time.process_time()
    wall_start = time.perf_counter()

    try:
        result = function(*args, **kwargs)
    finally:
        cpu_time = time.process_time() - cpu_start
        wall_time = time.perf_counter() - wall_start

        running = False
        memory_thread.join()

    ram_before_mb = ram_before_bytes / 1024**2
    peak_ram_mb = peak_ram_bytes / 1024**2
    peak_increase_mb = peak_ram_mb - ram_before_mb

    print(f'CPU time:        {cpu_time:.2f} s')
    print(f'Wall time:       {wall_time:.2f} s')
    print(f'RAM before:      {ram_before_mb:.1f} MB')
    print(f'Peak RAM:        {peak_ram_mb:.1f} MB')
    print(f'Peak RAM increase: {peak_increase_mb:.1f} MB')

    return result
