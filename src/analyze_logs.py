from pathlib import Path
from rich.console import Console

from .log_parser import parse_file_with_timestamps
from .anomaly_detector import aggregate_counts_by_minute, detect_anomalies
from .summarizer import find_log_files, merge_counts, top_n_problems
from .code_linker import link_errors_to_code

console = Console()
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
CODE_DIR = Path(__file__).resolve().parent  # src/

def main():
    if not LOG_DIR.exists():
        console.print(f"[bold red]Log folder not found: {LOG_DIR}[/]")
        return

    # Phase 1 & 2: gather timestamps, detect anomalies (optional)
    all_timestamps = []
    for log_file in find_log_files(LOG_DIR):
        console.print(f"[bold green]Scanning {log_file.name} for problem timestamps…[/]")
        all_timestamps += parse_file_with_timestamps(log_file)

    if not all_timestamps:
        console.print("[green]No problem lines found—nothing to analyze.[/]")
        return

    counts_df = aggregate_counts_by_minute(all_timestamps)
    anomalies, _ = detect_anomalies(counts_df, contamination=0.05)

    # Phase 1 summary: top error messages
    # (If you prefer pure Phase 1, skip timestamps and anomaly code and just build all_counts via parse_file)
    # For demo, we’ll reuse the raw counts mechanism:
    all_counts = {}
    from .log_parser import parse_file
    for log_file in find_log_files(LOG_DIR):
        counts = parse_file(log_file)
        merge_counts(all_counts, counts)

    console.print("\n[bold red]Top Problems Found:[/]")
    top = top_n_problems(all_counts)
    for err, cnt in top:
        console.print(f"[bold yellow]{cnt}[/] → {err[:120]}")

    # Phase 2 anomaly info (optional print)
    console.print("\n[bold blue]Anomalous time windows (spikes) found:[/]")
    if anomalies.empty:
        console.print("  [green]None[/]")
    else:
        for minute, row in anomalies.set_index("minute").iterrows():
            console.print(f" • {minute} → {row['count']} errors")

    # Phase 3: link errors to code
    error_messages = [err for err, _ in top]
    links = link_errors_to_code(error_messages, CODE_DIR)

    console.print("\n[bold blue]Code References for Top Errors:[/]")
    for err, files in links.items():
        console.print(f"\n[bright_magenta]Error:[/] {err}")
        if not files:
            console.print("  [dim]No matches found in code.[/]")
        else:
            for path, lines in files.items():
                console.print(f"  [cyan]{path.relative_to(CODE_DIR)}[/]")
                for snippet in lines[:3]:
                    console.print(f"    • {snippet}")

if __name__ == "__main__":
    main()
