"""TrustLayer CLI — trust every AI output from your terminal."""

import typer
import httpx
import json
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from typing import Optional

app = typer.Typer(
    name="trustlayer",
    help="TrustLayer — the universal AI trust layer. You bring the AI, we bring the trust.",
    rich_markup_mode="rich",
)

console = Console()

API_BASE = "http://localhost:8000"


def api(path: str, method: str = "GET", data: dict = None) -> dict:
    try:
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            if method == "POST":
                r = client.post(path, json=data)
            else:
                r = client.get(path)
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        console.print("[red]Cannot connect to TrustLayer server. Run: trustlayer server[/red]")
        raise typer.Exit(1)


@app.command()
def server():
    """Start the TrustLayer API server."""
    import uvicorn
    console.print(Panel("[bold green]TrustLayer Server[/bold green]\nStarting on http://localhost:8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


@app.command()
def verify(
    text: Optional[str] = typer.Argument(None, help="Text to verify (or '-' to read from stdin)"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
):
    """Verify AI-generated content and get a trust score."""
    # Read from stdin if text is None or "-", or if stdin is piped
    if text is None or text == "-":
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        elif text == "-":
            console.print("Enter text to verify (Ctrl+D when done):")
            text = sys.stdin.read().strip()
        else:
            console.print("[red]Error: No text provided and stdin is not piped[/red]")
            raise typer.Exit(1)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task("Analyzing content...", total=None)
        result = api("/api/verify", "POST", {"content": text})

    score = result["trust_score"]

    if json_output:
        # Output JSON format for piping to tools like jq
        json_result = {
            "score": score,
            "level": result.get("trust_label", "unknown"),
            "issues": result.get("issues", []),
            "verified": score >= 70,
            "summary": result.get("summary", "")
        }
        console.print(json.dumps(json_result))
    else:
        # Pretty-print format
        color = "green" if score >= 85 else "yellow" if score >= 60 else "red"
        label = result["trust_label"].upper()

        console.print(Panel(
            f"[bold {color}]Trust Score: {score}/100 ({label})[/bold {color}]\n\n{result['summary']}",
            title="[bold]TrustLayer Verification[/bold]",
            border_style=color,
        ))

        if result["issues"]:
            console.print("\n[bold yellow]Issues found:[/bold yellow]")
            for issue in result["issues"]:
                console.print(f"  • {issue}")

    # Exit code: 0 if trust >= 70, 1 if < 70 (for scripting)
    exit_code = 0 if score >= 70 else 1
    raise typer.Exit(exit_code)


@app.command()
def ask(
    prompt: str = typer.Argument(help="Your question or task"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="AI provider to use"),
    model: str = typer.Option("llama3.2", "--model", "-m", help="Model to use"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip trust verification"),
):
    """Ask any connected AI and get a verified response."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task(f"Asking {provider}/{model}...", total=None)
        result = api("/api/connectors/complete", "POST", {
            "provider": provider, "model": model, "prompt": prompt
        })

    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        raise typer.Exit(1)

    console.print(Panel(result["content"], title=f"[bold]{provider}/{model}[/bold]", border_style="blue"))
    console.print(f"[dim]Tokens: {result['tokens_in']}↑ {result['tokens_out']}↓ | Cost: ${result['cost_usd']:.4f} | Latency: {result['latency_ms']}ms[/dim]")

    if not no_verify:
        verify_result = api("/api/verify", "POST", {"content": result["content"], "context": prompt})
        score = verify_result["trust_score"]
        color = "green" if score >= 85 else "yellow" if score >= 60 else "red"
        console.print(f"\n[{color}]Trust Score: {score}/100[/{color}]", end="")
        if verify_result["issues"]:
            console.print(f" — {len(verify_result['issues'])} concern(s)")
        else:
            console.print(" — No concerns")


@app.command()
def compare(
    prompt: str = typer.Argument(help="Prompt to test across models"),
):
    """Compare the same prompt across multiple AI models."""
    providers = api("/api/connectors/")
    available = [p for p in providers if p["available"] and p["models"]]

    if not available:
        console.print("[yellow]No AI providers available. Check your config.[/yellow]")
        raise typer.Exit(1)

    # Build comparison targets
    targets = []
    for p in available[:3]:
        targets.append({"provider": p["name"], "model": p["models"][0]})

    console.print(f"[dim]Comparing across {len(targets)} model(s)...[/dim]")
    result = api("/api/compare", "POST", {"prompt": prompt, "providers": targets})

    table = Table(title="Model Comparison", show_header=True, header_style="bold")
    table.add_column("Provider/Model", style="cyan")
    table.add_column("Trust", justify="center")
    table.add_column("Latency", justify="right")
    table.add_column("Cost", justify="right")

    for r in result.get("ranked", []):
        score = r["trust_score"]
        color = "green" if score >= 85 else "yellow" if score >= 60 else "red"
        table.add_row(
            f"{r['provider']}/{r['model']}",
            f"[{color}]{score}[/{color}]",
            f"{r['latency_ms']}ms",
            f"${r['cost_usd']:.4f}",
        )

    console.print(table)
    if result.get("winner"):
        w = result["winner"]
        console.print(f"\n[green]Winner: {w['provider']}/{w['model']} ({w['trust_score']}/100 trust)[/green]")


@app.command()
def costs():
    """Show your AI spending dashboard."""
    result = api("/api/costs/summary")

    color = "red" if result["alert"] else "green"
    console.print(Panel(
        f"[bold]${result['total_usd']:.2f}[/bold] spent this {result['month']}\n"
        f"Budget: ${result['budget_usd']:.2f} ({result['budget_pct']}% used)",
        title="[bold]Cost Dashboard[/bold]",
        border_style=color,
    ))

    if result["alert_message"]:
        console.print(f"\n[red]⚠ {result['alert_message']}[/red]")

    if result["by_provider"]:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Provider")
        table.add_column("Cost", justify="right")
        for row in result["by_provider"]:
            table.add_row(row["provider"], f"${row['cost_usd']:.4f}")
        console.print(table)


@app.command()
def detect():
    """Detect all AI tools available on this machine."""
    result = api("/api/connectors/detect")
    console.print("\n[bold]Detected AI Tools:[/bold]")
    for name, found in result.items():
        status = "[green]✓[/green]" if found else "[dim]✗[/dim]"
        console.print(f"  {status} {name}")


@app.command()
def status():
    """Show TrustLayer status."""
    try:
        result = api("/")
        insights = api("/api/learn/insights")
        console.print(Panel(
            f"[green]TrustLayer v{result['version']} is running[/green]\n\n"
            f"Sessions tracked: {insights['total_interactions']}\n"
            f"Personalization: {insights['personalization_level']}%\n\n"
            f"{insights['message']}",
            title="[bold]TrustLayer Status[/bold]",
            border_style="green",
        ))
    except Exception:
        console.print("[red]TrustLayer is not running. Start with: trustlayer server[/red]")


@app.command()
def learn(
    get: Optional[str] = typer.Option(None, "--get", "-g", help="Get a profile preference value"),
    set: Optional[str] = typer.Option(None, "--set", "-s", help="Set a profile preference (format: key=value)"),
):
    """Show and manage your personal profile preferences."""
    try:
        if get:
            profile = api("/api/learn/profile")
            if get in profile:
                console.print(f"[bold]{get}:[/bold] {profile[get]}")
            else:
                console.print(f"[yellow]'{get}' not found in profile[/yellow]")
        elif set:
            if "=" not in set:
                console.print("[red]Invalid format. Use: --set key=value[/red]")
                raise typer.Exit(1)
            key, value = set.split("=", 1)
            result = api("/api/learn/profile", "PUT", {"key": key, "value": value})
            console.print(f"[green]✓[/green] Saved [bold]{key}[/bold] = {value}")
        else:
            # Show full profile
            profile = api("/api/learn/profile")
            if profile:
                console.print(Panel(
                    "\n".join(f"[cyan]{k}:[/cyan] {v}" for k, v in profile.items()),
                    title="[bold]Your Profile[/bold]",
                    border_style="blue",
                ))
            else:
                console.print("[yellow]Your profile is empty. Set preferences with: trustlayer learn --set key=value[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Knowledge subcommand group
knowledge_app = typer.Typer(help="Manage and search knowledge base")
app.add_typer(knowledge_app, name="knowledge")


@knowledge_app.command("list")
def knowledge_list():
    """List all available knowledge items in the knowledge base."""
    try:
        result = api("/api/knowledge/")

        if result.get("items"):
            table = Table(title="Knowledge Base", show_header=True, header_style="bold cyan")
            table.add_column("ID", style="cyan")
            table.add_column("Title")
            table.add_column("Type", justify="center")
            table.add_column("Added", justify="right", style="dim")

            for item in result["items"]:
                table.add_row(
                    item.get("id", "—"),
                    item.get("title", "Untitled"),
                    item.get("type", "document"),
                    item.get("created_at", "—"),
                )

            console.print(table)
            console.print(f"\n[dim]Search knowledge with: trustlayer knowledge search <query>[/dim]")
            console.print(f"[dim]Upload documents with: trustlayer knowledge upload <file>[/dim]")
        else:
            console.print("[yellow]No knowledge items available. Upload a document to get started.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@knowledge_app.command("search")
def knowledge_search(
    query: str = typer.Argument(help="Search query"),
):
    """Search the knowledge base for relevant information."""
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
            p.add_task(f"Searching knowledge base...", total=None)
            result = api("/api/knowledge/search", "POST", {"query": query})

        if result.get("results"):
            table = Table(title=f"Search Results for '{query}'", show_header=True, header_style="bold cyan")
            table.add_column("Title", style="cyan")
            table.add_column("Relevance", justify="right")
            table.add_column("Source", justify="left", style="dim")

            for item in result["results"]:
                relevance = item.get("relevance_score", 0)
                score_color = "green" if relevance >= 0.8 else "yellow" if relevance >= 0.6 else "red"
                table.add_row(
                    item.get("title", "Untitled"),
                    f"[{score_color}]{relevance:.0%}[/{score_color}]",
                    item.get("source", "unknown"),
                )

            console.print(table)
            console.print(f"\n[dim]Results: {len(result['results'])} item(s) found[/dim]")
        else:
            console.print("[yellow]No matching knowledge items found.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@knowledge_app.command("ask")
def knowledge_ask(
    question: Optional[str] = typer.Argument(None, help="Question to ask"),
):
    """Ask a question about the knowledge base."""
    # Read from stdin if question is None or "-", or if stdin is piped
    if question is None or question == "-":
        if not sys.stdin.isatty():
            question = sys.stdin.read().strip()
        elif question == "-":
            console.print("Enter your question (Ctrl+D when done):")
            question = sys.stdin.read().strip()
        else:
            console.print("[red]Error: No question provided and stdin is not piped[/red]")
            raise typer.Exit(1)

    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
            p.add_task("Searching knowledge base...", total=None)
            result = api("/api/knowledge/ask", "POST", {"question": question})

        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            raise typer.Exit(1)

        console.print(Panel(
            result.get("answer", "No answer found"),
            title="[bold]Knowledge Base Answer[/bold]",
            border_style="blue",
        ))

        # Show sources if available
        sources = result.get("sources", [])
        if sources:
            console.print("\n[bold cyan]Sources:[/bold cyan]")
            for source in sources:
                console.print(f"  • {source}")
        else:
            console.print("\n[dim]No sources referenced[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@knowledge_app.command("upload")
def knowledge_upload(
    file_path: str = typer.Argument(help="Path to the file to upload"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Optional title for the knowledge item"),
):
    """Upload a document to the knowledge base."""
    import os

    file_path_expanded = os.path.expanduser(file_path)

    if not os.path.exists(file_path_expanded):
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)

    if not os.path.isfile(file_path_expanded):
        console.print(f"[red]Path is not a file: {file_path}[/red]")
        raise typer.Exit(1)

    try:
        # Read file content
        with open(file_path_expanded, "r", encoding="utf-8") as f:
            content = f.read()

        file_name = os.path.basename(file_path_expanded)
        item_title = title or file_name

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
            p.add_task(f"Uploading {file_name}...", total=None)
            result = api("/api/knowledge/upload", "POST", {
                "title": item_title,
                "content": content,
                "filename": file_name,
            })

        if result.get("id"):
            console.print(Panel(
                f"[green]✓ Knowledge item created[/green]\n\n"
                f"ID: [bold]{result['id']}[/bold]\n"
                f"Title: {result.get('title', item_title)}\n"
                f"Size: {len(content):,} characters",
                title="[bold]Upload Complete[/bold]",
                border_style="green",
            ))
        else:
            console.print("[red]Upload failed[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
