"""Logging configuration with color-coded worker support."""

import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# Custom theme for worker colors
WORKER_THEME = Theme(
    {
        # Worker 1-8 get distinct colors
        "worker1": "bold cyan",
        "worker2": "bold green",
        "worker3": "bold yellow",
        "worker4": "bold magenta",
        "worker5": "bold blue",
        "worker6": "bold red",
        "worker7": "bold cyan",
        "worker8": "bold green",
        # Fallback for workers > 8
        "worker.default": "bold white",
        # Log level styles
        "logging.level.debug": "cyan",
        "logging.level.info": "green",
        "logging.level.warning": "yellow",
        "logging.level.error": "red",
        "logging.level.critical": "bold red",
    }
)

# Global console instance with our theme
console = Console(theme=WORKER_THEME)


class WorkerLogHandler(RichHandler):
    """Custom log handler that adds worker context to log messages with color coding per worker."""

    def __init__(self, worker_id: int = 0, **kwargs):
        super().__init__(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            show_time=False,
            **kwargs,
        )
        self.worker_id = worker_id
        self.worker_style = get_worker_style(worker_id)

    def emit(self, record):
        # Only add color if not already present and not the main process
        if self.worker_id > 0 and not getattr(record, "_worker_prefix_added", False):
            # Prefix each log with a colored worker marker and worker id
            prefix = f"[{self.worker_style}]● W{self.worker_id:02d}[/] "
            record.msg = f"{prefix}{record.msg}"
            record._worker_prefix_added = True
        super().emit(record)


def setup_logging(level: str = "INFO", worker_id: int = 0) -> None:
    """
    Configure logging with worker-specific formatting.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        worker_id: Worker ID for color coding (0 for main process)
    """
    # Clear existing handlers
    root_logger = logging.getLogger()
    # for handler in root_logger.handlers[:]:
    #     root_logger.removeHandler(handler)

    # Set up the worker-specific handler
    handler = WorkerLogHandler(worker_id=worker_id)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger.setLevel(level.upper())
    root_logger.addHandler(handler)


def get_worker_style(worker_id: int) -> str:
    """Get the style for a worker ID."""
    return f"worker{worker_id}" if 1 <= worker_id <= 8 else "worker.default"


def print_worker_banner(worker_id: int, pid: int, status: str = "STARTED") -> None:
    """Print a worker status banner with colored output.

    Args:
        worker_id: Worker ID number
        pid: Process ID
        status: Status message (e.g., "STARTED", "STOPPED")
    """
    style = get_worker_style(worker_id)
    banner = Text.assemble(
        (f" WORKER {worker_id} {status} ", f"reverse {style}"), " ", (f"PID: {pid}", "dim")
    )
    console.print(Panel(banner, style=style, padding=(0, 1)))


def print_master_banner(workers: int, status: str = "STARTING") -> None:
    """Print a master process banner.

    Args:
        workers: Number of workers
        status: Status message (e.g., "STARTING", "SHUTTING DOWN")
    """
    banner = Text.assemble(
        (f" {status} KAFKA WORKERS ({workers}x) ", "bold white on blue"),
        "\n",
        ("Press Ctrl+C to stop all workers", "dim"),
    )
    console.print(Panel(banner, border_style="blue", padding=(0, 1)))


def print_worker_status(worker_id: int, pid: int) -> None:
    """Print worker status in a panel.

    Args:
        worker_id: Worker ID number
        pid: Process ID
    """
    style = get_worker_style(worker_id)
    status = Text.assemble((f"● Worker {worker_id} ", style), (f"(PID: {pid})", "dim"))
    console.print(Panel(status, border_style=style, padding=(0, 1)))
