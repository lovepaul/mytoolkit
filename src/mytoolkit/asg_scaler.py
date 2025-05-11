#!/usr/bin/env python3
# src/mytoolkit/asg_scaler.py

import boto3
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from mytoolkit.utils import get_logger

app = typer.Typer(add_completion=True)
console = Console()

@app.command("scale-asg")
def scale_asg(
    region: str = typer.Option(None, "--region", "-r", help="AWS 区域 (例如 ap-east-1, cn-northwest-1)")
):
    """
    交互式调整 Auto Scaling Group 容量，使用 Rich 丰富终端界面和进度条。
    区域默认为 ap-east-1 或 cn-northwest-1，可通过 --region 覆盖。
    """
    logger = get_logger("scale-asg")

    # 区域选择
    if region is None:
        console.print("请选择 AWS 区域：")
        console.print("  [1] Asia Pacific (Hong Kong)        ap-east-1")
        console.print("  [2] China (Ningxia)                 cn-northwest-1")
        choice = Prompt.ask("输入编号", choices=["1", "2"], default="1")
        region = "ap-east-1" if choice == "1" else "cn-northwest-1"
    logger.info(f"使用区域: {region}")

    # 初始化 AWS 客户端
    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
        task = progress.add_task("初始化 AWS 客户端...", total=None)
        session = boto3.session.Session(region_name=region)
        sts, ec2 = session.client("sts"), session.client("ec2")
        asg_cli, iam = session.client("autoscaling"), session.client("iam")
        progress.update(task, description="AWS 客户端初始化完成", completed=1)

    ident = sts.get_caller_identity()
    account = ident["Account"]
    try:
        alias = iam.list_account_aliases()["AccountAliases"][0]
    except Exception:
        alias = None
    used_region = session.region_name or boto3.client("ec2").meta.region_name
    env_text = f"[bold]Account:[/bold] {alias or account}\n[bold]Region :[/bold] {used_region}"
    console.print(Panel(env_text, title="AWS 环境", border_style="cyan"))
    if not Confirm.ask("确认在上述环境中执行？", default=False):
        raise typer.Exit()

    # 主循环：可多次更新
    while True:
        svc = Prompt.ask("请输入服务关键词 (实例 Name 标签)")
        logger.info(f"服务关键词: {svc}")

        # 查询 EC2
        with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
            task = progress.add_task("查询 EC2 实例...", total=None)
            resp = ec2.describe_instances(
                Filters=[
                    {"Name": "tag:Name", "Values": [f"*{svc}*"]},
                    {"Name": "instance-state-name", "Values": ["running"]}
                ]
            )
            progress.update(task, description="EC2 实例查询完成", completed=1)

        instance_names = [
            t["Value"]
            for r in resp.get("Reservations", [])
            for ins in r.get("Instances", [])
            for t in ins.get("Tags", [])
            if t["Key"] == "Name"
        ]
        if not instance_names:
            console.print(f"[bold red]未找到与 “{svc}” 相关的运行中实例。[/bold red]")
            if not Confirm.ask("是否继续处理其他服务？", default=True):
                break
            else:
                continue

        # 展示 ASG 列表
        counts = {name: instance_names.count(name) for name in set(instance_names)}
        table = Table(title="搜索到的 ASG 列表", header_style="bold cyan")
        table.add_column("编号", style="bold", justify="right")
        table.add_column("ASG 名称", style="cyan")
        table.add_column("实例数", style="magenta", justify="right")
        for idx, (name, cnt) in enumerate(counts.items(), start=1):
            table.add_row(str(idx), name, str(cnt))
        console.print(table)

        choice = Prompt.ask("请选择要操作的编号", choices=[str(i) for i in range(1, len(counts) + 1)])
        chosen = list(counts.keys())[int(choice) - 1]

        # 查询 ASG 配置
        with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
            task = progress.add_task(f"查询 ASG [{chosen}] 配置...", total=None)
            detail = asg_cli.describe_auto_scaling_groups(
                AutoScalingGroupNames=[chosen]
            )["AutoScalingGroups"][0]
            progress.update(task, description="ASG 配置查询完成", completed=1)

        current = {
            "Name":    chosen,
            "Created": detail["CreatedTime"].strftime("%Y-%m-%d %H:%M:%S"),
            "Desired": detail["DesiredCapacity"],
            "Min":     detail["MinSize"],
            "Max":     detail["MaxSize"],
        }
        conf_text = "\n".join(
            f"[bold]{k}:[/bold] {v}" if k in ("Name", "Created")
            else f"[green]{k}:[/green] {v}" for k, v in current.items()
        )
        console.print(Panel(conf_text, title="当前 ASG 配置", border_style="green"))

        # 输入新配置
        while True:
            new_des = int(Prompt.ask("新 Desired", default=str(current["Desired"])))
            new_min = int(Prompt.ask("新 Min    ", default=str(current["Min"])))
            new_max = int(Prompt.ask("新 Max    ", default=str(current["Max"])))
            if new_min <= new_des <= new_max:
                break
            console.print("[bold red]错误：需满足 Min ≤ Desired ≤ Max。[/bold red]")
            if not Confirm.ask("重试？", default=True):
                break

        # 预览
        preview = Table(title="变更预览", header_style="bold magenta")
        preview.add_column("字段", style="cyan")
        preview.add_column("旧值", justify="right")
        preview.add_column("新值", justify="right")
        preview.add_row("Desired", str(current["Desired"]), str(new_des))
        preview.add_row("Min",     str(current["Min"]),     str(new_min))
        preview.add_row("Max",     str(current["Max"]),     str(new_max))
        console.print(preview)

        if Confirm.ask("确认执行更新？", default=False):
            with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
                task = progress.add_task(f"更新 ASG [{chosen}]...", total=None)
                asg_cli.update_auto_scaling_group(
                    AutoScalingGroupName=chosen,
                    MinSize=new_min,
                    DesiredCapacity=new_des,
                    MaxSize=new_max,
                )
                progress.update(task, description="更新完成", completed=1)
            console.print(f"[bold green]✅ 已更新 ASG {chosen}[/bold green]")

        # 是否继续
        if not Confirm.ask("是否继续更新其他服务？", default=True):
            break

if __name__ == "__main__":
    app()