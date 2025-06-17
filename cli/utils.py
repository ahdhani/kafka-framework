"""Utility functions for the CLI."""

import importlib
import sys
from pathlib import Path
from typing import Any


def import_app(app_path: str) -> Any:
    """Import a KafkaApp instance from a module path."""
    if ":" not in app_path:
        raise ValueError("app_path must be in format 'module.path:app_variable'")

    module_path, app_name = app_path.split(":", 1)

    # Add current directory to Python path
    current_dir = str(Path.cwd())
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    try:
        module = importlib.import_module(module_path)
        kafka_app = getattr(module, app_name)

        # Basic validation
        if not hasattr(kafka_app, "lifespan"):
            raise ValueError(f"Object at {app_path} doesn't have a lifespan method")

        return kafka_app

    except ImportError as e:
        raise ImportError(f"Failed to import module '{module_path}': {e}") from e
    except AttributeError as e:
        raise AttributeError(f"App '{app_name}' not found in module '{module_path}'") from e
