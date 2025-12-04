"""hhg v2 - Semantic code search.

If you want grep, use rg. If you want semantic understanding, use hhg.
"""

import json
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__

# Consoles
console = Console()
err_console = Console(stderr=True)

# Exit codes
EXIT_MATCH = 0
EXIT_NO_MATCH = 1
EXIT_ERROR = 2

# Index directory
INDEX_DIR = ".hhg"

app = typer.Typer(
    name="hhg",
    help="Semantic code search",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)


def get_index_path(root: Path) -> Path:
    """Get the index directory path."""
    return root.resolve() / INDEX_DIR


def index_exists(root: Path) -> bool:
    """Check if index exists for this directory."""
    index_path = get_index_path(root)
    return (index_path / "manifest.json").exists()


def build_index(root: Path, quiet: bool = False) -> None:
    """Build semantic index for directory."""
    from .scanner import scan
    from .semantic import SemanticIndex

    root = root.resolve()

    if not quiet:
        err_console.print(f"[dim]Scanning {root}...[/]")

    # Scan for files
    t0 = time.perf_counter()
    files = scan(str(root), ".", include_hidden=False)
    scan_time = time.perf_counter() - t0

    if not files:
        err_console.print("[yellow]No files found to index[/]")
        return

    if not quiet:
        err_console.print(f"[dim]Found {len(files)} files ({scan_time:.1f}s)[/]")
        err_console.print("[dim]Building index...[/]")

    # Build index
    t0 = time.perf_counter()
    index = SemanticIndex(root)

    def on_progress(current: int, total: int, msg: str) -> None:
        if not quiet:
            err_console.print(f"\r[dim]{msg} ({current}/{total})[/]", end="")

    stats = index.index(files, on_progress=on_progress)
    index_time = time.perf_counter() - t0

    if not quiet:
        err_console.print()  # Newline after progress
        err_console.print(
            f"[green]✓[/] Indexed {stats['blocks']} blocks "
            f"from {stats['files']} files ({index_time:.1f}s)"
        )
        if stats["skipped"]:
            err_console.print(f"[dim]  Skipped {stats['skipped']} unchanged files[/]")


def semantic_search(
    query: str,
    root: Path,
    n: int = 10,
    threshold: float = 0.0,
) -> list[dict]:
    """Run semantic search."""
    from .semantic import SemanticIndex

    index = SemanticIndex(root.resolve())
    results = index.search(query, k=n)

    # Filter by threshold if specified
    if threshold > 0:
        results = [r for r in results if r.get("score", 0) >= threshold]

    return results


def grep_search(pattern: str, root: Path, regex: bool = False) -> list[dict]:
    """Fast grep search (escape hatch)."""
    from .extractor import ContextExtractor
    from .scanner import scan

    # Scan for matches
    files = scan(str(root), pattern, include_hidden=False)

    # Extract context from matches
    extractor = ContextExtractor()
    results = []

    for file_path, content in files.items():
        blocks = extractor.extract(file_path, pattern, content)
        for block in blocks:
            results.append(
                {
                    "file": file_path,
                    "line": block["start_line"],
                    "end_line": block["end_line"],
                    "name": block["name"],
                    "type": block["type"],
                    "content": block["content"],
                    "score": 1.0,  # No ranking for grep
                }
            )

    return results


def print_results(
    results: list[dict],
    json_output: bool = False,
    compact: bool = False,
    show_content: bool = True,
    root: Path = None,
) -> None:
    """Print search results."""
    if json_output:
        if compact:
            output = [{k: v for k, v in r.items() if k != "content"} for r in results]
        else:
            output = results
        print(json.dumps(output, indent=2))
        return

    for r in results:
        # Shorten file path if possible
        file_path = r["file"]
        if root:
            try:
                file_path = str(Path(file_path).relative_to(root))
            except ValueError:
                pass

        # Header line
        score = r.get("score", 0)
        score_str = f"({score:.2f})" if score else ""
        type_str = f"[dim]{r.get('type', '')}[/]"
        name_str = r.get("name", "")
        line = r.get("line") or r.get("start_line", 0)

        console.print(
            f"[cyan]{file_path}[/]:[yellow]{line}[/] "
            f"{type_str} [bold]{name_str}[/] [dim]{score_str}[/]"
        )

        # Content preview (first 3 non-empty lines)
        if show_content and r.get("content"):
            content_lines = [ln for ln in r["content"].split("\n") if ln.strip()][:3]
            for content_line in content_lines:
                # Truncate long lines
                if len(content_line) > 80:
                    content_line = content_line[:77] + "..."
                console.print(f"  [dim]{content_line}[/]")
            console.print()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    query: str = typer.Argument(None, help="Search query"),
    path: Path = typer.Argument(Path("."), help="Directory to search"),
    # Output
    n: int = typer.Option(10, "-n", help="Number of results"),
    threshold: float = typer.Option(0.0, "-t", "--threshold", help="Minimum score (0-1)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON output"),
    compact: bool = typer.Option(False, "-c", "--compact", help="No content in output"),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Suppress progress"),
    # Escape hatches
    exact: bool = typer.Option(False, "-e", "--exact", help="Exact string match (grep)"),
    regex: bool = typer.Option(False, "-r", "--regex", help="Regex match"),
    # Index control
    no_index: bool = typer.Option(False, "--no-index", help="Skip auto-index (fail if missing)"),
    # Meta
    version: bool = typer.Option(False, "-v", "--version", help="Show version"),
):
    """Semantic code search.

    Examples:
        hhg "authentication flow" ./src    # Semantic search
        hhg -e "TODO" ./src                # Exact match (grep)
        hhg -r "TODO.*fix" ./src           # Regex match
    """
    if ctx.invoked_subcommand is not None:
        return

    if version:
        console.print(f"hhg {__version__}")
        raise typer.Exit()

    if not query:
        console.print(
            Panel(
                "[bold]hhg[/] - Semantic code search\n\n"
                "Usage:\n"
                "  hhg <query> [path]       Semantic search\n"
                "  hhg -e <pattern> [path]  Exact match (grep)\n"
                "  hhg -r <pattern> [path]  Regex match\n"
                "  hhg status [path]        Index status\n"
                "  hhg rebuild [path]       Rebuild index\n"
                "  hhg clean [path]         Delete index",
                border_style="dim",
            )
        )
        raise typer.Exit()

    # Validate path
    path = path.resolve()
    if not path.exists():
        err_console.print(f"[red]Error:[/] Path does not exist: {path}")
        raise typer.Exit(EXIT_ERROR)

    # Escape hatches: grep mode
    if exact or regex:
        if not quiet:
            mode = "regex" if regex else "exact"
            err_console.print(f"[dim]Searching ({mode})...[/]")

        t0 = time.perf_counter()
        results = grep_search(query, path, regex=regex)
        search_time = time.perf_counter() - t0

        if not results:
            if not json_output:
                err_console.print("[dim]No matches found[/]")
            raise typer.Exit(EXIT_NO_MATCH)

        results = results[:n]
        print_results(results, json_output, compact, root=path)

        if not quiet and not json_output:
            err_console.print(f"[dim]{len(results)} results ({search_time:.2f}s)[/]")

        raise typer.Exit(EXIT_MATCH)

    # Default: semantic search
    # Check omendb is available
    from .semantic import HAS_OMENDB

    if not HAS_OMENDB:
        err_console.print("[red]Error:[/] omendb not installed (required for semantic search)")
        err_console.print("Install with: pip install 'hygrep[semantic]'")
        err_console.print("\n[dim]Tip: Use -e for exact match without semantic search[/]")
        raise typer.Exit(EXIT_ERROR)

    # Check if index exists, build if not
    if not index_exists(path):
        if no_index:
            err_console.print("[red]Error:[/] No index found (use without --no-index to build)")
            raise typer.Exit(EXIT_ERROR)
        if not quiet:
            err_console.print("[yellow]No index found. Building...[/]")
        build_index(path, quiet=quiet)
        if not quiet:
            err_console.print()
    elif not no_index:
        # Check for stale index and auto-update
        from .scanner import scan
        from .semantic import SemanticIndex

        files = scan(str(path), ".", include_hidden=False)
        index = SemanticIndex(path)
        stale_count = index.needs_update(files)

        if stale_count > 0:
            if not quiet:
                err_console.print(f"[dim]Updating index ({stale_count} files changed)...[/]")
            stats = index.update(files)
            if not quiet and stats.get("blocks", 0) > 0:
                err_console.print(f"[dim]  Updated {stats['blocks']} blocks[/]")

    # Run semantic search
    if not quiet:
        err_console.print(f"[dim]Searching for: {query}[/]")

    t0 = time.perf_counter()
    results = semantic_search(query, path, n=n, threshold=threshold)
    search_time = time.perf_counter() - t0

    if not results:
        if not json_output:
            err_console.print("[dim]No results found[/]")
        raise typer.Exit(EXIT_NO_MATCH)

    print_results(results, json_output, compact, root=path)

    if not quiet and not json_output:
        err_console.print(f"[dim]{len(results)} results ({search_time:.2f}s)[/]")

    raise typer.Exit(EXIT_MATCH)


@app.command()
def status(path: Path = typer.Argument(Path("."), help="Directory")):
    """Show index status."""
    from .semantic import HAS_OMENDB, SemanticIndex

    if not HAS_OMENDB:
        err_console.print("[red]Error:[/] omendb not installed")
        err_console.print("Install with: pip install 'hygrep[semantic]'")
        raise typer.Exit(EXIT_ERROR)

    path = path.resolve()
    index_path = get_index_path(path)

    if not index_exists(path):
        err_console.print(f"[yellow]No index[/] at {index_path}")
        raise typer.Exit()

    index = SemanticIndex(path)
    count = index.count()
    console.print(f"[green]✓[/] Index: {count} vectors")
    console.print(f"  Location: {index_path}")


@app.command()
def rebuild(
    path: Path = typer.Argument(Path("."), help="Directory"),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Suppress progress"),
):
    """Rebuild index from scratch."""
    from .semantic import HAS_OMENDB, SemanticIndex

    if not HAS_OMENDB:
        err_console.print("[red]Error:[/] omendb not installed")
        raise typer.Exit(EXIT_ERROR)

    path = path.resolve()

    # Clear existing
    if index_exists(path):
        index = SemanticIndex(path)
        index.clear()
        if not quiet:
            err_console.print("[dim]Cleared existing index[/]")

    # Build fresh
    build_index(path, quiet=quiet)


@app.command()
def clean(path: Path = typer.Argument(Path("."), help="Directory")):
    """Delete index."""
    from .semantic import HAS_OMENDB, SemanticIndex

    if not HAS_OMENDB:
        err_console.print("[red]Error:[/] omendb not installed")
        raise typer.Exit(EXIT_ERROR)

    path = path.resolve()

    if not index_exists(path):
        err_console.print("[dim]No index to delete[/]")
        raise typer.Exit()

    index = SemanticIndex(path)
    index.clear()
    console.print("[green]✓[/] Index deleted")


def run():
    """Entry point."""
    app()


if __name__ == "__main__":
    run()
