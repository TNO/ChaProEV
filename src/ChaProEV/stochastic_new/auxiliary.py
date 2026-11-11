import os

import psutil


def print_memory(label: str) -> None:
    process: psutil.Process = psutil.Process(os.getpid())
    memory_gb: float = process.memory_info().rss / 1024**3
    print(f'{label}: {memory_gb:.2f} GB')
