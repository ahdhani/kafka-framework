"""Main CLI application and commands."""

import asyncio
from typing import Annotated

import typer

from .workers import run_multi_worker, run_worker

app = typer.Typer(
    name="kafka-cli",
    help="Run KafkaApp applications with multi-worker support",
    add_completion=False,
)


@app.command()
def run(
    app_path: Annotated[
        str,
        typer.Argument(
            help="Application path in format 'module.path:app_variable'", metavar="APP_PATH"
        ),
    ],
    workers: Annotated[
        int, typer.Option("--workers", "-w", min=1, help="Number of worker processes")
    ] = 1,
    log_level: Annotated[
        str, typer.Option("--log-level", "-l", case_sensitive=False, help="Log level")
    ] = "INFO",
) -> None:
    """Run a KafkaApp application."""
    try:
        if workers == 1:
            asyncio.run(run_worker(app_path, log_level))
        else:
            run_multi_worker(app_path, workers, log_level)
    except KeyboardInterrupt as e:
        typer.echo("Interrupted by user")
        raise typer.Exit(0) from e
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", "-V", help="Show version and exit")] = False,
) -> None:
    """KafkaApp CLI - Run Kafka applications with multi-worker support."""
    if version:
        typer.echo("kafka-cli version 1.0.0")
        raise typer.Exit(0)

    if ctx.invoked_subcommand is None:
        typer.echo("Error: Missing command", err=True)
        typer.echo("Try 'kafka-cli --help' for help.")
        raise typer.Exit(1)
