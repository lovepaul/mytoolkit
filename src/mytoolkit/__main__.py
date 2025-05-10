# src/mytoolkit/__main__.py
import typer

from .asg_scaler import app as _scale
from .discover_asg import app as _discover
from .batch_scale_asg import app as _batch

app = typer.Typer(help="mytoolkit — AWS ASG helper")

app.add_typer(_scale, name="scale")
app.add_typer(_discover, name="discover")
app.add_typer(_batch, name="batch-scale")

if __name__ == "__main__":
    app()
