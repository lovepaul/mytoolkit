#!/usr/bin/env python3
# src/mytoolkit/batch_scale_asg.py

import os
import json
import boto3
import typer
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from mytoolkit.utils import get_logger, echo_error, echo_info

app = typer.Typer(add_completion=True)
console = Console()


@app.command("batch-scale-asg")
def batch_scale_asg(
    get_template: bool = typer.Option(
        False, "--get-template-json", "-t",
        help="根据 discover-asg 输出生成批量缩放模板"
    ),
    input_json: str = typer.Option(
        None, "--input-json", "-i",
        help="discover-asg 输出文件路径 (支持 Windows/Mac)"
    ),
    region: str = typer.Option(
        None, "--region", "-r",
        help="AWS 区域 (例如 ap-east-1, cn-northwest-1)"
    ),
):
    """
    生成或执行批量 ASG 扩/缩容计划 (JSON 列表形式)。
    模板示例:
      [
        {
          "ec2_name": "nginx",
          "asg_name": "nginx-xx-asg-1",
          "created": "...",
          "current": {"n":2,"d":2,"x":2},
          "target":  {"n":2,"d":2,"x":2}
        },
        ...
      ]
    """
    logger = get_logger("batch-scale-asg")

    # —— 0. 区域选择 —— #
    if region is None:
        console.print("请选择 AWS 区域：")
        console.print("  [1] Asia Pacific (Hong Kong)    ap-east-1")
        console.print("  [2] China (Ningxia)             cn-northwest-1")
        choice = Prompt.ask("输入编号", choices=["1", "2"], default="1")
        region = "ap-east-1" if choice == "1" else "cn-northwest-1"
    logger.info(f"使用区域: {region}")

    session = boto3.session.Session(region_name=region)
    sts = session.client("sts")
    ident = sts.get_caller_identity()
    user_arn = ident.get("Arn")
    asg_cli = session.client("autoscaling")

    # —— 1. 模板生成模式 —— #
    if get_template:
        # 1.a 输入 discover-asg 输出路径
        while not input_json:
            input_json = Prompt.ask("请输入 discover-asg 输出 JSON 路径")
        disc_path = os.path.abspath(os.path.expanduser(input_json))
        console.print(f"[red]discover-asg 输出文件路径:[/red] {disc_path}")
        logger.info(f"Template generation input: {disc_path}")
        if not os.path.isfile(disc_path):
            echo_error(f"文件不存在：{disc_path}")
            raise typer.Exit(1)

        # 1.b 读取 discovered 列表
        with open(disc_path, "r", encoding="utf-8") as f:
            discovered = json.load(f)
        if not isinstance(discovered, list):
            echo_error("discover-asg 输出必须是 JSON 数组")
            raise typer.Exit(1)

        # 1.c 分离有效/无效，处理多候选 ASG 名称
        valid = []
        invalid = []
        for entry in discovered:
            ec2 = entry.get("ec2_name")
            asg_val = entry.get("asg_name")
            # Normalize to list
            if isinstance(asg_val, list):
                candidates = asg_val
            elif isinstance(asg_val, str):
                candidates = [asg_val]
            else:
                candidates = []

            if not candidates:
                invalid.append(ec2)
                continue

            if len(candidates) > 1:
                console.print(f"[cyan]发现 ec2_name '{ec2}' 对应多个 ASG，请选择：[/cyan]")
                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("编号", justify="right")
                table.add_column("ASG 名称", style="green")
                for idx, name in enumerate(candidates, start=1):
                    table.add_row(str(idx), name)
                console.print(table)
                sel = Prompt.ask(
                    "选择 ASG 编号",
                    choices=[str(i) for i in range(1, len(candidates) + 1)]
                )
                chosen = candidates[int(sel) - 1]
            else:
                chosen = candidates[0]

            valid.append((ec2, chosen))

        # 1.d 警告无效项
        if invalid:
            console.print(
                f"[bold red]⚠️ 以下 ec2_name 无对应 ASG，已从模板中过滤：{invalid}[/bold red]"
            )
            logger.info(f"Invalid entries filtered: {invalid}")

        # 1.e 构建模板列表，跳过不存在的 ASG
        template_list = []
        for ec2, asg in valid:
            resp = asg_cli.describe_auto_scaling_groups(AutoScalingGroupNames=[asg])
            groups = resp.get("AutoScalingGroups", [])
            if not groups:
                console.print(f"[yellow]⚠️ ASG '{asg}' 未找到，已跳过[/yellow]")
                logger.warning(f"ASG '{asg}' not found, skipping")
                continue
            detail = groups[0]
            created = detail["CreatedTime"].strftime("%Y-%m-%d %H:%M:%S")
            cd = detail["DesiredCapacity"]
            mn = detail["MinSize"]
            mx = detail["MaxSize"]
            template_list.append({
                "ec2_name": ec2,
                "asg_name": asg,
                "created": created,
                "current": {"n": mn, "d": cd, "x": mx},
                "target":  {"n": mn, "d": cd, "x": mx}
            })

        if not template_list:
            console.print("[bold red]⚠️ 无可用 ASG 模板，已退出[/bold red]")
            raise typer.Exit(1)

        # 1.f 写入模板到当前工作目录
        tpl_path = os.path.join(
            os.getcwd(),
            f"batch_scale_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(tpl_path, "w", encoding="utf-8") as f:
            json.dump(template_list, f, indent=2, ensure_ascii=False)

        echo_info(f"✅ 模板已生成：{tpl_path}")
        logger.info(f"Generated batch scale template at {tpl_path}")
        raise typer.Exit()

    # —— 2. 执行计划模式 —— #
    while not input_json:
        input_json = Prompt.ask("请输入批量缩放计划 JSON 路径")
    plan_path = os.path.abspath(os.path.expanduser(input_json))
    if not os.path.isfile(plan_path):
        echo_error(f"文件不存在：{plan_path}")
        raise typer.Exit(1)
    if os.path.getsize(plan_path) == 0:
        echo_error(f"输入文件为空：{plan_path}")
        raise typer.Exit(1)

    # 2.a 加载计划
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as e:
        echo_error(f"解析 JSON 失败：{e}")
        raise typer.Exit(1)
    if not isinstance(plan, list) or not plan:
        echo_error("JSON 必须是非空数组 (list)")
        raise typer.Exit(1)

    # 2.b 校验计划项格式和逻辑
    seen = set()
    for idx, entry in enumerate(plan, start=1):
        ec2 = entry.get("ec2_name")
        asg = entry.get("asg_name")
        if not ec2 or not isinstance(ec2, str):
            echo_error(f"第 {idx} 项：ec2_name 无效")
            raise typer.Exit(1)
        if not asg or not isinstance(asg, str):
            echo_error(f"第 {idx} 项：asg_name 无效")
            raise typer.Exit(1)
        if asg in seen:
            echo_error(f"第 {idx} 项：asg_name '{asg}' 重复")
            raise typer.Exit(1)
        seen.add(asg)
        for blk_name in ("current", "target"):
            blk = entry.get(blk_name)
            if not isinstance(blk, dict) or not all(k in blk for k in ("n", "d", "x")):
                echo_error(f"第 {idx} 项：'{blk_name}' 必须包含 n, d, x")
                raise typer.Exit(1)
            if not all((blk[k] is None or isinstance(blk[k], int)) for k in blk):
                echo_error(f"第 {idx} 项：'{blk_name}' 值必须为整数或 null")
                raise typer.Exit(1)
        tmin, td, tmax = entry["target"]["n"], entry["target"]["d"], entry["target"]["x"]
        if not (tmin <= td <= tmax):
            echo_error(
                f"第 {idx} 项：目标配置不合法 (n={tmin}, d={td}, x={tmax})，需满足 n ≤ d ≤ x"
            )
            raise typer.Exit(1)

    # 3. 展示 & 确认
    table = Table(title="批量缩放计划预览", header_style="bold magenta")
    table.add_column("No.", justify="right")
    table.add_column("ec2_name", style="cyan")
    table.add_column("asg_name", style="green")
    table.add_column("current[n/d/x]", justify="center")
    table.add_column("target [n/d/x]", justify="center")
    for idx, entry in enumerate(plan, start=1):
        curr = f"{entry['current']['n']}/{entry['current']['d']}/{entry['current']['x']}"
        targ = f"{entry['target']['n']}/{entry['target']['d']}/{entry['target']['x']}"
        table.add_row(str(idx), entry["ec2_name"], entry["asg_name"], curr, targ)
    console.print(table)
    if not Confirm.ask("确认执行以上批量缩放计划？", default=False):
        console.print("[bold red]操作已取消[/bold red]")
        raise typer.Exit(0)

    # 4. 遍历执行，每项单独确认
    for entry in plan:
        ec2 = entry["ec2_name"]
        asg = entry["asg_name"]
        resp = asg_cli.describe_auto_scaling_groups(AutoScalingGroupNames=[asg])
        groups = resp.get("AutoScalingGroups", [])
        if not groups:
            console.print(f"[yellow]⚠️ ASG '{asg}' 未找到，已跳过更新[/yellow]")
            entry["status"] = "skipped"
            continue
        detail = groups[0]
        cd, mn, mx = detail["DesiredCapacity"], detail["MinSize"], detail["MaxSize"]
        td, tmin, tmax = entry["target"]["d"], entry["target"]["n"], entry["target"]["x"]

        if cd == td and mn == tmin and mx == tmax:
            console.print(f"[yellow]ASG {asg}: 当前与目标一致，跳过[/yellow]")
            entry["status"] = "skipped"
            continue

        info = (
            f"[bold]{ec2} → {asg}[/bold]\n"
            f" Current: [green]{mn}/{cd}/{mx}[/green]\n"
            f" Target : [red]{tmin}/{td}/{tmax}[/red]"
        )
        console.print(Panel(info, title="单条确认", border_style="cyan"))
        if not Confirm.ask(f"确认更新 {asg}?", default=False):
            console.print(f"[yellow]已跳过 {asg}[/yellow]")
            entry["status"] = "skipped"
            continue

        with Progress(SpinnerColumn(), TextColumn("{task.description}")) as prog:
            task = prog.add_task(f"更新 {asg}...", total=None)
            asg_cli.update_auto_scaling_group(
                AutoScalingGroupName=asg,
                MinSize=tmin,
                DesiredCapacity=td,
                MaxSize=tmax
            )
            prog.update(task, description="更新完成", completed=1)

        console.print(f"[bold green]✅ {asg} 更新完成[/bold green]")
        entry["status"] = "updated"
        entry["updated_by"] = user_arn
        entry["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 5. 写回结果到 logs 目录
    log_dir = os.path.join(os.getcwd(), "logs", "batch-scale-asg")
    os.makedirs(log_dir, exist_ok=True)
    result_path = os.path.join(
        log_dir,
        f"batch_scale_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    echo_info(f"✅ 批量缩放结果已保存：{result_path}")
    logger.info(f"Batch scale result written to {result_path}")


if __name__ == "__main__":
    app()