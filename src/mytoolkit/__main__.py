#!/usr/bin/env python3
# src/mytoolkit/__main__.py

import typer
from mytoolkit import __version__
from mytoolkit.asg_scaler import app as _scale_app
from mytoolkit.discover_asg import app as _discover_app
from mytoolkit.batch_scale_asg import app as _batch_app

app = typer.Typer(
    add_completion=True,  # keep completion
    no_args_is_help=True,  # show help if no args
    help="mytoolkit — AWS ASG helper"
)

# register the three sub-commands under one entrypoint
app.add_typer(_scale_app, name="asg-scale")
app.add_typer(_discover_app, name="asg-find")
app.add_typer(_batch_app, name="asg-batch-scale")


@app.callback(invoke_without_command=True)
def main(
        version: bool = typer.Option(
            False, "--version", "-v", is_eager=True,
            help="Show mytoolkit version and exit"
        ),
        show_completion: str = typer.Option(
            None, "--show-completion", hidden=True,
            help="Output shell completion script"
        ),
        install_completion: str = typer.Option(
            None, "--install-completion", hidden=True,
            help="Install shell completion"
        ),
):
    """
    mytoolkit — AWS ASG helper
    """
    if show_completion:
        typer.echo(app.get_completion(show_completion))
        raise typer.Exit()

    if install_completion:
        app.install_completion(install_completion)
        raise typer.Exit()

    if version:
        typer.echo(f"mytoolkit {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
