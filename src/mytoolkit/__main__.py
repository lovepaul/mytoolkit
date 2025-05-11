#!/usr/bin/env python3
# src/mytoolkit/__main__.py

import typer
from mytoolkit import __version__
from mytoolkit.asg_scaler import app as _scale_app
from mytoolkit.discover_asg import app as _discover_app
from mytoolkit.batch_scale_asg import app as _batch_app

app = typer.Typer(
    add_completion=True,  # 打开自动补全
    no_args_is_help=True,  # 无参数时显示帮助
    help="mytoolkit — AWS ASG helper"
)

# 将三个子命令注册到 mytoolkit
app.add_typer(_scale_app, name="asg-scale")
app.add_typer(_discover_app, name="asg-find")
app.add_typer(_batch_app, name="asg-batch-scale")


@app.callback(invoke_without_command=True)
def main(
        version: bool = typer.Option(
            False, "--version", "-v", is_eager=True,
            help="Show mytoolkit version and exit"
        ),
):
    """
    顶级命令入口。--help、--show-completion、--install-completion
    由 Typer 自动处理，这里只手动处理 --version。
    """
    if version:
        typer.echo(f"mytoolkit {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
