# src/mytoolkit/__main__.py

import typer
from mytoolkit import __version__
from mytoolkit.asg_scaler import app as _scale_app
from mytoolkit.discover_asg import app as _discover_app
from mytoolkit.batch_scale_asg import app as _batch_app

app = typer.Typer(
    no_args_is_help=True,
    help="mytoolkit — AWS ASG helper"
)

app.add_typer(_scale_app, name="asg-scale")
app.add_typer(_discover_app, name="asg-find")
app.add_typer(_batch_app, name="asg-batch-scale")

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit"
    ),
):
    if version:
        typer.echo(f"mytoolkit {__version__}")
        raise typer.Exit()

if __name__ == "__main__":
    app()