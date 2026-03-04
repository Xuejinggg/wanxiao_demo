#!/usr/bin/env python3
"""创展车主加购场景：工具实现 + 全流程编排。"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _resolve_customer_csv() -> Path:
    sandbox_path = Path(
        "/home/daytona/skills/chuangzhan-owner-addon-scenario/data/customer_pool.csv"
    )
    if sandbox_path.exists():
        return sandbox_path
    return Path(__file__).resolve().parents[1] / "data" / "customer_pool.csv"


def _load_customer_pool() -> dict[str, dict[str, str]]:
    customer_db: dict[str, dict[str, str]] = {}
    csv_path = _resolve_customer_csv()
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = (row.get("customer_id") or "").strip()
            if cid:
                customer_db[cid] = row
    return customer_db


CUSTOMER_DB = _load_customer_pool()


def _calc_priority(expire_days: int, interaction_days: int) -> str:
    score = max(0, 100 - expire_days) + max(0, 30 - interaction_days)
    if score >= 90:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def customer_pool_tool(date: str, channel: str) -> dict[str, Any]:
    rows = []
    for cid, c in CUSTOMER_DB.items():
        expire_days = int(c.get("auto_policy_expire_days", "999"))
        interaction_days = int(c.get("last_interaction_days", "99"))
        rows.append(
            {
                "date": date,
                "channel": channel,
                "customer_id": cid,
                "customer_name": c.get("name", ""),
                "auto_policy_expire_days": expire_days,
                "last_interaction_days": interaction_days,
                "priority": _calc_priority(expire_days, interaction_days),
                "touch_window": "19:00-21:00",
            }
        )
    return {"status": "success", "tool_name": "customer_pool_tool", "data": rows}


def owner_profile_tool(customer_id: str) -> dict[str, Any]:
    c = CUSTOMER_DB.get(customer_id)
    if c is None:
        return {"status": "error", "message": "customer_not_found", "data": None}
    profile = {
        "customer_id": customer_id,
        "customer_name": c.get("name", ""),
        "city": c.get("city", ""),
        "family_structure": c.get("family_structure", ""),
        "income_band": c.get("income_band", ""),
        "response_preference": "微信图文+电话",
    }
    return {"status": "success", "tool_name": "owner_profile_tool", "profile": profile}


def demand_insight_tool(customer_id: str) -> dict[str, Any]:
    c = CUSTOMER_DB.get(customer_id)
    if c is None:
        return {"status": "error", "message": "customer_not_found", "data": None}
    family = c.get("family_structure", "")
    need_tag = "家庭保障" if "有孩" in family else "健康保障"
    insight = {
        "need_tag": need_tag,
        "gap_score": 82 if need_tag == "家庭保障" else 65,
        "monthly_budget": "500-1200",
        "annual_budget": "6000-14000",
        "next_action": "推荐2-3款可组合产品并电话确认",
    }
    return {"status": "success", "tool_name": "demand_insight_tool", "insight": insight}


def non_auto_product_recommend_tool(customer_id: str, topk: int = 3) -> dict[str, Any]:
    _ = customer_id
    recs = [
        {
            "product_code": "HEALTH_PLUS",
            "product_name": "健康守护",
            "type": "医疗险",
            "coverage": "300万",
            "price_band": "¥699-1299",
            "match_score": 0.91,
        },
        {
            "product_code": "ACCIDENT_GUARD",
            "product_name": "意外安心",
            "type": "意外险",
            "coverage": "100万",
            "price_band": "¥199-399",
            "match_score": 0.86,
        },
        {
            "product_code": "FAMILY_SHIELD",
            "product_name": "家庭护航",
            "type": "家庭综合保障",
            "coverage": "组合方案",
            "price_band": "¥1299-2599",
            "match_score": 0.83,
        },
    ]
    return {
        "status": "success",
        "tool_name": "non_auto_product_recommend_tool",
        "recommendations": recs[: max(1, topk)],
    }


def recommendation_reason_tool(
    customer_id: str, product_codes: list[str]
) -> dict[str, Any]:
    _ = customer_id
    reasons = []
    for code in product_codes:
        reasons.append(
            {
                "product_code": code,
                "reason": f"{code} 与客户家庭责任和预算区间匹配，保障缺口覆盖更完整。",
                "matched_features": ["家庭结构", "预算区间", "保障缺口"],
                "entry_point": "先确认家庭责任，再引出组合保障价值",
            }
        )
    return {
        "status": "success",
        "tool_name": "recommendation_reason_tool",
        "reasons": reasons,
    }


def call_script_tool(customer_id: str, priority: str) -> dict[str, Any]:
    _ = customer_id
    opening = "张先生您好，我是平安创展顾问小安，您车险保障做得不错，我再给您补齐家庭风险保障。"
    if priority == "low":
        opening = "张先生您好，给您同步一条简短保障资讯，方便时我再详细说明。"
    script = {
        "opening": opening,
        "need_question": "您现在更关注家庭成员医疗还是意外风险？",
        "product_entry": "结合您家庭情况，这个组合在预算内能把住院和意外风险一起覆盖。",
        "objection_handle": "先从低门槛方案开始，后续可按需求逐步升级。",
        "closing": "我先把方案卡片发您微信，今晚8点再和您确认10分钟。",
    }
    return {"status": "success", "tool_name": "call_script_tool", "script": script}


def outreach_material_tool(customer_id: str, scene: str) -> dict[str, Any]:
    _ = customer_id
    materials = [
        {
            "title": f"{scene}保障方案1分钟解读",
            "type": "海报",
            "link": "https://mock-insurance.com/materials/owner-addon-poster.png",
            "segment": scene,
            "channel": "微信",
        },
        {
            "title": "家庭保障配置清单",
            "type": "图文",
            "link": "https://mock-insurance.com/materials/owner-addon-article.png",
            "segment": "家庭保障",
            "channel": "微信",
        },
    ]
    return {
        "status": "success",
        "tool_name": "outreach_material_tool",
        "materials": materials,
    }


def outbound_call_tool(customer_id: str, agent: str) -> dict[str, Any]:
    return {
        "status": "success",
        "tool_name": "outbound_call_tool",
        "call_result": {
            "customer_id": customer_id,
            "agent": agent,
            "call_status": "connected",
            "result_tag": "有兴趣，需看方案",
            "appointment_time": datetime.now().strftime("%Y-%m-%d 20:00"),
            "next_action": "发送方案并次日跟进",
        },
    }


def run_flow(customer_id: str, agent: str, date: str = "2026-03-04") -> dict[str, Any]:
    pool = customer_pool_tool(date=date, channel="创展")
    data = pool.get("data") if isinstance(pool, dict) else None
    if not isinstance(data, list):
        return {"status": "error", "message": "invalid_pool_data", "data": None}

    target = None
    for item in data:
        if isinstance(item, dict) and item.get("customer_id") == customer_id:
            target = item
            break
    if not target:
        return {"status": "error", "message": "customer_not_in_pool", "data": None}

    profile_res = owner_profile_tool(customer_id)
    insight_res = demand_insight_tool(customer_id)
    if profile_res.get("status") != "success" or insight_res.get("status") != "success":
        return {"status": "error", "message": "profile_or_insight_failed", "data": None}

    profile = profile_res.get("profile", {})
    insight = insight_res.get("insight", {})
    need_tag = (
        insight.get("need_tag", "家庭保障") if isinstance(insight, dict) else "家庭保障"
    )
    priority = str(target.get("priority", "low"))

    rec = non_auto_product_recommend_tool(
        customer_id, topk=3 if priority == "high" else 2
    )
    rec_list = rec.get("recommendations", []) if isinstance(rec, dict) else []
    codes = [
        str(x.get("product_code", ""))
        for x in rec_list
        if isinstance(x, dict) and x.get("product_code")
    ]
    reasons = recommendation_reason_tool(customer_id, codes)
    script = call_script_tool(customer_id, priority=priority)
    materials = outreach_material_tool(customer_id, scene=str(need_tag))

    if priority == "low":
        call = {
            "status": "success",
            "call_result": {"call_status": "not_called", "next_action": "7天后再触达"},
        }
    elif priority == "medium":
        call = {
            "status": "success",
            "call_result": {"call_status": "scheduled", "next_action": "次日外呼"},
        }
    else:
        call = outbound_call_tool(customer_id, agent)

    call_result = call.get("call_result", {}) if isinstance(call, dict) else {}
    next_plan = (
        call_result.get("next_action", "继续跟进")
        if isinstance(call_result, dict)
        else "继续跟进"
    )

    return {
        "status": "success",
        "tool_name": "run_owner_addon_flow",
        "structuredContent": {
            "customer_layer": priority,
            "customer": target,
            "profile": profile,
            "insight": insight,
            "recommendations": rec.get("recommendations", [])
            if isinstance(rec, dict)
            else [],
            "reasons": reasons.get("reasons", []) if isinstance(reasons, dict) else [],
            "script": script.get("script", {}) if isinstance(script, dict) else {},
            "materials": materials.get("materials", [])
            if isinstance(materials, dict)
            else [],
            "call_result": call_result,
            "next_plan": next_plan,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run owner add-on full flow")
    parser.add_argument("--customer-id", required=True, help="客户ID")
    parser.add_argument("--agent", default="创展顾问小安", help="外呼坐席")
    parser.add_argument("--date", default="2026-03-04", help="业务日期")
    args = parser.parse_args()
    result = run_flow(customer_id=args.customer_id, agent=args.agent, date=args.date)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
