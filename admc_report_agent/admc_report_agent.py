#!/usr/bin/env python3
"""
ADMC Report Agent — Main CLI entry point.

Orchestrates data ingestion, AI insight generation, and PPTX report building
for Active DMC client communications reports.
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel


console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="ADMC Report Agent — Generate branded communications reports.",
    )
    parser.add_argument(
        "--client",
        required=True,
        help="Client name (e.g. 'Denodo', 'KnowBe4').",
    )
    parser.add_argument(
        "--period",
        required=True,
        help="Reporting period (e.g. 'Q1 2026', 'January 2026').",
    )
    parser.add_argument(
        "--tracker",
        default=None,
        help="Path to the client tracker .xlsx file.",
    )
    parser.add_argument(
        "--asana-token",
        default=None,
        help="Asana Personal Access Token (overrides env var).",
    )
    parser.add_argument(
        "--no-asana",
        action="store_true",
        default=False,
        help="Skip Asana data fetching.",
    )
    parser.add_argument(
        "--context",
        default=None,
        help="Additional context string to pass to the AI engine.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the generated .pptx file.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    console.print(
        Panel(
            f"[bold]ADMC Report Agent[/bold]\n"
            f"Client: [cyan]{args.client}[/cyan]  |  Period: [cyan]{args.period}[/cyan]",
            border_style="bright_cyan",
        )
    )

    # ── Step 1: Load environment variables ──────────────────────────────
    console.print("\n[bold]Step 1:[/bold] Loading environment variables...")
    load_dotenv()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    asana_token = args.asana_token or os.getenv("ASANA_PAT")

    if not anthropic_key:
        console.print(
            "[yellow]WARNING:[/yellow] ANTHROPIC_API_KEY not found. "
            "AI insight generation will be skipped."
        )

    # ── Step 2: Parse tracker data ──────────────────────────────────────
    tracker_data = {}
    if args.tracker:
        console.print(f"\n[bold]Step 2:[/bold] Parsing tracker: [cyan]{args.tracker}[/cyan]")
        try:
            from data_sources.tracker_parser import parse_tracker

            tracker_data = parse_tracker(args.tracker)
            console.print(
                f"  [green]OK[/green] — {tracker_data.get('total_placements', 0)} placements loaded."
            )
        except Exception as exc:
            console.print(f"  [red]ERROR[/red] parsing tracker: {exc}")
            tracker_data = {"error": str(exc), "total_placements": 0, "rows": []}
    else:
        console.print("\n[bold]Step 2:[/bold] No tracker file provided — skipping.")

    # ── Step 3: Fetch Asana data ────────────────────────────────────────
    asana_data = {}
    if args.no_asana:
        console.print("\n[bold]Step 3:[/bold] Asana fetch skipped (--no-asana).")
    elif not asana_token:
        console.print(
            "\n[bold]Step 3:[/bold] [yellow]No Asana token available[/yellow] — skipping."
        )
    else:
        console.print(f"\n[bold]Step 3:[/bold] Fetching Asana data for [cyan]{args.client}[/cyan]...")
        try:
            from data_sources.asana_fetcher import fetch_asana_data

            asana_data = fetch_asana_data(args.client, asana_token)
            task_count = asana_data.get("total_tasks", 0)
            console.print(f"  [green]OK[/green] — {task_count} tasks fetched.")
        except Exception as exc:
            console.print(f"  [red]ERROR[/red] fetching Asana data: {exc}")
            asana_data = {"error": str(exc), "tasks": [], "deliverables": []}

    # ── Step 4: Deduplicate combined data ───────────────────────────────
    console.print("\n[bold]Step 4:[/bold] Deduplicating combined data...")
    merged_data = {
        "tracker": tracker_data,
        "asana": asana_data,
        "client": args.client,
        "period": args.period,
    }

    try:
        from data_sources.deduplicator import deduplicate

        # Combine tasks from asana with any additional sources
        all_tasks = asana_data.get("tasks", [])
        deliverables = deduplicate(all_tasks) if all_tasks else asana_data.get("deliverables", [])
        merged_data["deliverables"] = deliverables
        console.print(f"  [green]OK[/green] — {len(deliverables)} unique deliverables identified.")
    except Exception as exc:
        console.print(f"  [red]ERROR[/red] during deduplication: {exc}")
        merged_data["deliverables"] = asana_data.get("deliverables", [])

    # Attach additional context if provided
    if args.context:
        merged_data["additional_context"] = args.context

    # ── Step 5: Generate AI insights ────────────────────────────────────
    insights = {}
    if anthropic_key:
        console.print("\n[bold]Step 5:[/bold] Generating AI insights via Claude API...")

        try:
            from ai_engine.insight_generator import generate_all_insights

            def progress_callback(section_name, index, total):
                console.print(
                    f"  [{index + 1}/{total}] Generating insights for: "
                    f"[cyan]{section_name}[/cyan]"
                )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task_id = progress.add_task("Insight generation", total=9)

                def rich_callback(section_name, index, total):
                    progress.update(task_id, completed=index + 1, description=f"Generating: {section_name}")

                insights = generate_all_insights(
                    client=args.client,
                    period=args.period,
                    tracker_data=tracker_data,
                    deliverables_data=merged_data.get("deliverables", []),
                    api_key=anthropic_key,
                    progress_callback=rich_callback,
                )

            # Count successes and failures
            successes = sum(1 for v in insights.values() if "error" not in v)
            failures = len(insights) - successes
            console.print(
                f"  [green]OK[/green] — {successes} sections generated"
                + (f", [yellow]{failures} failed[/yellow]" if failures else "")
                + "."
            )
        except Exception as exc:
            console.print(f"  [red]ERROR[/red] during insight generation: {exc}")
            insights = {}
    else:
        console.print(
            "\n[bold]Step 5:[/bold] [yellow]Skipping AI insights[/yellow] — no API key."
        )

    # ── Step 6: Build PPTX report ───────────────────────────────────────
    console.print(f"\n[bold]Step 6:[/bold] Building PPTX report...")
    output_path = args.output

    try:
        from report_builder.slide_factory import build_report

        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        result_path = build_report(
            client=args.client,
            period=args.period,
            tracker_data=tracker_data,
            deliverables=merged_data.get("deliverables", []),
            insights=insights,
            output_path=output_path,
        )

        if result_path:
            console.print(
                Panel(
                    f"[bold green]Report generated successfully![/bold green]\n"
                    f"Output: [cyan]{result_path}[/cyan]",
                    border_style="green",
                )
            )
        else:
            console.print(
                "[yellow]WARNING:[/yellow] build_report returned None — "
                "slide_factory may not be fully implemented yet."
            )
    except Exception as exc:
        console.print(f"  [red]ERROR[/red] building report: {exc}")
        console.print(
            "[yellow]The report could not be generated. "
            "Check that slide_factory.py is fully implemented.[/yellow]"
        )
        sys.exit(1)

    console.print("\n[bold]Done.[/bold]")


if __name__ == "__main__":
    main()
