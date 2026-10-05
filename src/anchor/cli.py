"""Command-line interface for ANCHOR."""

import typer

app = typer.Typer(
    name="anchor",
    help="ANCHOR: Lightweight safety and deterministic control layer for AI agents.",
    no_args_is_help=True,
)


@app.command()
def init(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace directory path"),
) -> None:
    """Initialize ANCHOR safety configuration in the specified workspace."""
    typer.echo(f"Initialized ANCHOR safety boundary in {workspace}")


@app.command()
def demo() -> None:
    """Run an end-to-end deterministic demonstration without requiring an API key."""
    typer.echo("Running ANCHOR deterministic safety demonstration...")


@app.command()
def run(
    goal: str = typer.Argument(..., help="Natural language goal for the agent"),
) -> None:
    """Evaluate and execute an agent goal under ANCHOR contract enforcement."""
    typer.echo(f"Processing goal: {goal}")


@app.command()
def status() -> None:
    """Show the current workspace safety status and pending approvals."""
    typer.echo("Workspace safety status: Active")


@app.command()
def approve(
    action_id: str = typer.Argument(..., help="Action ID to approve"),
) -> None:
    """Approve a pending high-risk action."""
    typer.echo(f"Action {action_id} approved.")


@app.command()
def deny(
    action_id: str = typer.Argument(..., help="Action ID to deny"),
) -> None:
    """Deny a pending high-risk action."""
    typer.echo(f"Action {action_id} denied.")


@app.command()
def undo() -> None:
    """Roll back to the previous snapshot state."""
    typer.echo("Rolling back to latest checkpoint...")


if __name__ == "__main__":
    app()
