import os

import psutil
from rich import print


def print_memory(label: str) -> None:
    '''
    Print the current process memory usage in GB.

    The label identifies the point in the model run at which memory usage is
    measured. Intended as a diagnostic tool for comparing memory consumption
    between model configurations.
    '''
    process: psutil.Process = psutil.Process(os.getpid())
    memory_gb: float = process.memory_info().rss / 1024**3
    print(f'{label}: {memory_gb:.2f} GB')
