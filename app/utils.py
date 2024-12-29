import psutil
import os

def check_memory_usage():
    process = psutil.Process(os.getpid())
    return {
        'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
        'memory_percent': process.memory_percent()
    }
