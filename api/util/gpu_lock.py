from __future__ import annotations

import threading

GPU_LOCK = threading.Lock()


def gpu_busy() -> bool:
    if GPU_LOCK.acquire(blocking=False):
        GPU_LOCK.release()
        return False
    return True
