#!/usr/bin/env python3
# src/mytoolkit/discover_asg.py

import os
import json
import boto3
import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from mytoolkit.utils import get_logger, echo_error, echo_info

app = typer.Typer(add_completion=False)
console = Console()


@app.command("discover-asg")
def discover_asg(
        get_temp_json: bool = typer.Option(
            False, "--get-temp-json", "-t", help="生成服务关键词 JSON 模板"
        ),
        input_json: str = typer.Option(
            None, "--input-json", "-i", help="输入 JSON 文件路径 (支持 Windows/Mac 路径)"
        ),
        region: str = typer.Option(None, "--region", "-r", help="AWS 区域")
):
    """
    批量根据模糊的 EC2 Name（即服务名）列表发现对应的 ASG 名称，
    输入 JSON 格式: [{"ec2_name": "ng"}, {"ec2_name": "example"}]
    输出 JSON 格式: [{"ec2_name":"ng","asg_name":"nginx-xx-asg"}, ...]
    """
    logger = get_logger("discover-asg")
    session = boto3.session.Session(region_name=region)
    ec2 = session.client("ec2")

    # 1. 生成模板
    if get_temp_json:
        cwd = os.getcwd()
        template_path = os.path.join(cwd, "service_ec2_template.json")
        template = [
            {"ec2_name": "service_keyword1"},
            {"ec2_name": "service_keyword2"},
            {"ec2_name": "example-service"}
        ]
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        echo_info(f"✅ 模板已生成：{template_path}")
        logger.info(f"Generated template at {template_path}")
        raise typer.Exit()

    # 2. 获取并验证输入 JSON 路径
    while not input_json:
        input_json = Prompt.ask("请输入服务关键词 JSON 文件路径")
    input_path = os.path.abspath(os.path.expanduser(input_json))
    if not os.path.isfile(input_path):
        echo_error(f"文件不存在：{input_path}")
        raise typer.Exit(1)
    if os.path.getsize(input_path) == 0:
        echo_error(f"输入文件为空：{input_path}")
        raise typer.Exit(1)

    # 3. 加载并校验 JSON 内容
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception as e:
        echo_error(f"解析 JSON 失败：{e}")
        raise typer.Exit(1)
    if not isinstance(items, list) or not items:
        echo_error("JSON 必须是非空数组")
        raise typer.Exit(1)

    # 4. 校验每项格式
    keywords = []
    for idx, entry in enumerate(items, start=1):
        if (
                isinstance(entry, dict)
                and "ec2_name" in entry
                and isinstance(entry["ec2_name"], str)
                and entry["ec2_name"].strip()
        ):
            keywords.append(entry["ec2_name"].strip())
        else:
            echo_error(f"第 {idx} 项无效（需为 {{'ec2_name': '...'}}）")
            raise typer.Exit(1)

    # 5. 批量搜索 & 用户选择
    mapping = []
    for kw in keywords:
        with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
            task = progress.add_task(f"查询“{kw}”运行中实例...", total=None)
            resp = ec2.describe_instances(
                Filters=[
                    {"Name": "tag:Name", "Values": [f"*{kw}*"]},
                    {"Name": "instance-state-name", "Values": ["running"]}
                ]
            )
            progress.update(task, description="查询完成", completed=1)

        names = [
            tag["Value"]
            for r in resp.get("Reservations", [])
            for ins in r.get("Instances", [])
            for tag in ins.get("Tags", [])
            if tag["Key"] == "Name"
        ]
        candidates = sorted(set(names))

        if not candidates:
            console.print(f"[yellow]⚠️ “{kw}” 未找到匹配的实例[/yellow]")
            mapping.append({"ec2_name": kw, "asg_name": None})
            logger.info(f"{kw} → None")
            continue

        if len(candidates) > 1:
            table = Table(title=f"关键词 “{kw}” 匹配到多个 ASG", header_style="bold cyan")
            table.add_column("编号", justify="right")
            table.add_column("ASG 名称", style="cyan")
            for i, name in enumerate(candidates, start=1):
                table.add_row(str(i), name)
            console.print(table)
            choice = Prompt.ask(
                "请选择对应的 ASG 编号",
                choices=[str(i) for i in range(1, len(candidates) + 1)]
            )
            sel = int(choice)
            selected = candidates[sel - 1]
        else:
            selected = candidates[0]
            console.print(f"[cyan]“{kw}” → [green]{selected}[/green]")

        mapping.append({"ec2_name": kw, "asg_name": selected})
        logger.info(f"{kw} → {selected}")

    # 6. 输出到默认文件
    out_path = os.path.abspath(os.path.join(os.getcwd(), "discovered_asgs.json"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    echo_info(f"✅ 发现结果已导出至：{out_path}")
    logger.info(f"Exported mapping to {out_path}")


if __name__ == "__main__":
    app()
