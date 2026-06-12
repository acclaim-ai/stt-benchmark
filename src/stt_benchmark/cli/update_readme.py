"""CLI command for upserting service rows into the README results table.

The README "Results Summary" table is the single source of truth for the
published benchmark numbers and the Pareto plots. This command reads a service's
metrics from your local benchmark database and writes *just that row* into the
table, leaving every other row untouched — so multiple contributors can each add
their own result without clobbering anyone else's.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from stt_benchmark.config import get_config
from stt_benchmark.models import ServiceName
from stt_benchmark.reporting.readme_table import upsert_readme_rows
from stt_benchmark.services import STT_SERVICES, parse_services_arg
from stt_benchmark.storage.database import Database

app = typer.Typer()
console = Console()


def _repo_readme() -> Path:
    """Repo-root README.md (src/stt_benchmark/cli/update_readme.py -> parents[3])."""
    return Path(__file__).resolve().parents[3] / "README.md"


@app.callback(invoke_without_command=True)
def update_readme(
    services: str = typer.Option(
        ...,
        "--services",
        "-s",
        help="Comma-separated service keys to add/update (e.g. deepgram,nvidia)",
    ),
    readme: Path = typer.Option(
        None,
        "--readme",
        help="Path to README.md (default: repo README.md)",
    ),
    test: bool = typer.Option(
        False,
        "--test",
        "-t",
        help="Use test database (test_results.db) instead of main database",
    ),
):
    """Insert or update one row per service in the README results table.

    Reads the named services' metrics from your local benchmark database and
    upserts just those rows between the RESULTS_TABLE markers in README.md,
    leaving every other row byte-identical. Regenerate the plots afterwards with
    ``uv run python scripts/pareto-frontier-plot.py`` (which reads the README).

    The services must already be benchmarked and scored locally
    (``stt-benchmark run`` then ``stt-benchmark wer``).
    """
    console.print("\n[bold blue]STT Benchmark - Update README table[/bold blue]\n")

    try:
        service_list = parse_services_arg(services)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    readme_path = readme or _repo_readme()
    if not readme_path.exists():
        console.print(f"[red]README not found: {readme_path}[/red]")
        raise typer.Exit(1)

    db_path = None
    if test:
        db_path = get_config().data_dir / "test_results.db"
        console.print("[yellow]Using test database[/yellow]\n")

    rows, missing = asyncio.run(_fetch_rows(service_list, db_path))

    for key in missing:
        console.print(
            f"[yellow]No benchmark/WER results for '{key}' — run "
            f"'stt-benchmark run -s {key}' and 'stt-benchmark wer -s {key}' first. "
            f"Skipping.[/yellow]"
        )

    if not rows:
        console.print("\n[yellow]Nothing to update.[/yellow]")
        raise typer.Exit(1)

    written = upsert_readme_rows(readme_path, rows)
    console.print(f"\n[green]Updated {len(written)} row(s) in {readme_path}:[/green]")
    for label in written:
        console.print(f"  • {label}")
    console.print(
        "\n[dim]Now regenerate the plots from the README:[/dim] "
        "uv run python scripts/pareto-frontier-plot.py"
    )


async def _fetch_rows(
    service_list: list[ServiceName], db_path: Path | None
) -> tuple[list[tuple], list[str]]:
    """Fetch ``(definition, metrics)`` rows for services that have local results.

    Mirrors the DB → metrics conversion the plot script used to do: TTFB stats
    and the WER summary, converted to ms / %. Returns ``(rows, missing)`` where
    ``missing`` lists requested service keys with no benchmark/WER results yet.
    """
    db = Database(db_path=db_path)
    await db.initialize()
    try:
        model_by_service = {
            name.value: model for name, model in await db.get_services_with_results()
        }

        rows: list[tuple] = []
        found: set[str] = set()
        for service in service_list:
            key = service.value
            if key not in model_by_service:
                continue
            model_name = model_by_service[key]
            stats = await db.get_service_transcript_stats(service, model_name)
            summary = await db.get_service_summary(service, model_name)
            if not stats or not summary:
                continue

            sample_count = summary["sample_count"]
            perfect_pct = summary["perfect_count"] / sample_count * 100 if sample_count else 0.0
            metrics = {
                "ttfb_median": stats["ttfb_median"] * 1000,  # s -> ms
                "ttfb_p95": stats["ttfb_p95"] * 1000,
                "ttfb_p99": stats["ttfb_p99"] * 1000,
                "pooled_wer": summary["pooled_wer"] * 100,  # fraction -> %
                "success_rate": stats["success_rate"] * 100,
                "perfect_pct": perfect_pct,
                "wer_mean": summary["wer_mean"] * 100,
            }
            rows.append((STT_SERVICES[key], metrics))
            found.add(key)
    finally:
        await db.close()

    missing = [s.value for s in service_list if s.value not in found]
    return rows, missing
