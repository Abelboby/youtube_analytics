import psutil
import os

def check_memory_usage():
    """
    Get memory usage information in a lightweight way
    """
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return {
        'memory_usage_mb': memory_info.rss / 1024 / 1024,  # Convert to MB
        'memory_percent': process.memory_percent(memtype='rss')
    }
