#!/usr/bin/env python3
"""车主加购场景 CLI：按工具名调用。"""

import argparse
import json
import sys

from run_owner_addon_flow import (
    call_script_tool,
    customer_pool_tool,
    demand_insight_tool,
    non_auto_product_recommend_tool,
    outbound_call_tool,
    outreach_material_tool,
    owner_profile_tool,
    recommendation_reason_tool,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="创展车主加购工具 - 命令行版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    %(prog)s customer_pool_tool --date 2026-03-04 --channel 创展
    %(prog)s owner_profile_tool --customer-id C001
    %(prog)s demand_insight_tool --customer-id C001
    %(prog)s non_auto_product_recommend_tool --customer-id C001 --topk 3
    %(prog)s recommendation_reason_tool --customer-id C001 --product-codes HEALTH_PLUS,ACCIDENT_GUARD
    %(prog)s call_script_tool --customer-id C001 --priority high
    %(prog)s outreach_material_tool --customer-id C001 --scene 家庭保障
    %(prog)s outbound_call_tool --customer-id C001 --agent 创展顾问小安
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    def add_output_option(sub: argparse.ArgumentParser) -> None:
        sub.add_argument(
            "--output",
            "-o",
            choices=["json", "pretty"],
            default="pretty",
            help="输出格式: json 或 pretty (默认: pretty)",
        )

    sub = subparsers.add_parser(
        "customer_pool_tool", help="获取车险老客客户池与优先级名单"
    )
    sub.add_argument("--date", required=True)
    sub.add_argument("--channel", default="创展")
    add_output_option(sub)

    sub = subparsers.add_parser("owner_profile_tool", help="生成客户基础画像")
    sub.add_argument("--customer-id", required=True)
    add_output_option(sub)

    sub = subparsers.add_parser("demand_insight_tool", help="识别保障缺口与潜在需求")
    sub.add_argument("--customer-id", required=True)
    add_output_option(sub)

    sub = subparsers.add_parser(
        "non_auto_product_recommend_tool", help="生成非车险产品推荐组合"
    )
    sub.add_argument("--customer-id", required=True)
    sub.add_argument("--topk", type=int, default=3)
    add_output_option(sub)

    sub = subparsers.add_parser("recommendation_reason_tool", help="生成推荐理由")
    sub.add_argument("--customer-id", required=True)
    sub.add_argument("--product-codes", required=True)
    add_output_option(sub)

    sub = subparsers.add_parser("call_script_tool", help="生成分层切入话术")
    sub.add_argument("--customer-id", required=True)
    sub.add_argument("--priority", choices=["high", "medium", "low"], required=True)
    add_output_option(sub)

    sub = subparsers.add_parser("outreach_material_tool", help="生成可转发触客素材")
    sub.add_argument("--customer-id", required=True)
    sub.add_argument("--scene", default="家庭保障")
    add_output_option(sub)

    sub = subparsers.add_parser("outbound_call_tool", help="执行外呼并回传触达结果")
    sub.add_argument("--customer-id", required=True)
    sub.add_argument("--agent", default="创展顾问小安")
    add_output_option(sub)

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    command_map = {
        "customer_pool_tool": lambda: customer_pool_tool(args.date, args.channel),
        "owner_profile_tool": lambda: owner_profile_tool(args.customer_id),
        "demand_insight_tool": lambda: demand_insight_tool(args.customer_id),
        "non_auto_product_recommend_tool": lambda: non_auto_product_recommend_tool(
            args.customer_id, args.topk
        ),
        "recommendation_reason_tool": lambda: recommendation_reason_tool(
            args.customer_id,
            [x.strip() for x in args.product_codes.split(",") if x.strip()],
        ),
        "call_script_tool": lambda: call_script_tool(args.customer_id, args.priority),
        "outreach_material_tool": lambda: outreach_material_tool(
            args.customer_id, args.scene
        ),
        "outbound_call_tool": lambda: outbound_call_tool(args.customer_id, args.agent),
    }

    func = command_map.get(args.command)
    if not func:
        print(f"未知命令: {args.command}", file=sys.stderr)
        sys.exit(1)

    try:
        result = func()
        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"执行出错: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
