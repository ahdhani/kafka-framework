"""Worker process management."""

import asyncio
import multiprocessing
import os
import signal
import sys

from .logging import print_master_banner, print_worker_banner, setup_logging
from .utils import import_app


async def run_single_app(app_path: str) -> None:
    """Run a single KafkaApp instance."""
    kafka_app = import_app(app_path)

    # Setup signal handling
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def signal_handler():
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        async with kafka_app.lifespan():
            await shutdown_event.wait()
    except asyncio.CancelledError:
        pass


def worker_process(app_path: str, worker_id: int, log_level: str) -> None:
    """Worker process function."""
    setup_logging(log_level, worker_id)
    print_worker_banner(worker_id, os.getpid())

    try:
        asyncio.run(run_single_app(app_path))
    except KeyboardInterrupt:
        pass
    finally:
        print_worker_banner(worker_id, os.getpid(), "STOPPED")


def run_worker(app_path: str, log_level: str = "INFO") -> None:
    """Run a single worker process."""
    setup_logging(log_level)
    asyncio.run(run_single_app(app_path))


def run_multi_worker(app_path: str, workers: int, log_level: str) -> None:
    """Run multiple worker processes."""
    print_master_banner(workers)
    processes = []

    def signal_handler(signum, frame):
        print_master_banner(workers, "SHUTTING DOWN")
        for p in processes:
            if p.is_alive():
                p.terminate()
        for p in processes:
            p.join(timeout=5)
            if p.is_alive():
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        for i in range(workers):
            p = multiprocessing.Process(
                target=worker_process,
                args=(app_path, i + 1, log_level),
                name=f"kafka-worker-{i + 1}",
            )
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
