---
name: chuangzhan-owner-addon-scenario
description: 创展车主加购（非车险）经营技能。用于已购车险客户的日常经营，先筛选重点跟进客户，再完成客户画像、需求洞察、产品推荐、推荐理由、切入话术、触客素材与外呼动作。当用户的问题核心是“今天该跟进哪些车主、推荐什么非车险产品、如何触达”时使用。
---

# chuangzhan-owner-addon-scenario（车主加购 + 工具编排）

本 Skill 用于执行创展渠道车主加购流程：从车险老客客户池中筛选重点客户，结合客户画像识别潜在需求，再输出非车险产品推荐、推荐理由与触达动作，最终生成可执行的外呼结果和下一步计划。

## 工作流

1. 从客户池中读取已购车险客户，筛选重点跟进名单。
2. 调用 `owner_profile_tool` 与 `demand_insight_tool` 生成画像和需求洞察。
3. 调用 `non_auto_product_recommend_tool` 与 `recommendation_reason_tool` 生成推荐方案与理由。
4. 调用 `call_script_tool` 与 `outreach_material_tool` 生成切入话术与触客素材。
5. 对高优先级客户调用 `outbound_call_tool` 外呼，并返回结构化结果。

## 销售指导手册（执行规则）

### 重点客户筛选

- 基于车险到期天数、最近互动天数，计算跟进优先级（high/medium/low）。

### 推荐分流

- **high**：调用 `non_auto_product_recommend_tool` + `recommendation_reason_tool` + `call_script_tool` + `outbound_call_tool`。
- **medium**：调用 `non_auto_product_recommend_tool` + `recommendation_reason_tool` + `call_script_tool`（外呼改为预约）。
- **low**：调用 `call_script_tool` + `outreach_material_tool` 做轻触达。

## 绑定mcp工具

- 编排脚本：`scripts/run_owner_addon_flow.py`
- 涉及 MCP 工具：
  - `customer_pool_tool`（获取车险老客客户池与优先级名单）
  - `owner_profile_tool`（生成客户基础画像）
  - `demand_insight_tool`（识别保障缺口与潜在需求）
  - `non_auto_product_recommend_tool`（生成非车险产品推荐组合）
  - `recommendation_reason_tool`（生成推荐理由）
  - `call_script_tool`（生成分层切入话术）
  - `outreach_material_tool`（生成可转发触客素材）
  - `outbound_call_tool`（执行外呼并回传触达结果）

### Basic Usage (沙箱环境)

沙箱环境中 skills 目录位于 `/home/daytona/skills/`，执行脚本时请务必使用该路径：

```bash
# 获取客户池
python /home/daytona/skills/chuangzhan-owner-addon-scenario/scripts/owner_addon_cli.py customer_pool_tool --date "2026-03-04" --channel "创展"

# 客户画像
python /home/daytona/skills/chuangzhan-owner-addon-scenario/scripts/owner_addon_cli.py owner_profile_tool --customer-id "C001"

# 需求洞察
python /home/daytona/skills/chuangzhan-owner-addon-scenario/scripts/owner_addon_cli.py demand_insight_tool --customer-id "C001"

# 产品推荐
python /home/daytona/skills/chuangzhan-owner-addon-scenario/scripts/owner_addon_cli.py non_auto_product_recommend_tool --customer-id "C001" --topk 3

# 推荐理由
python /home/daytona/skills/chuangzhan-owner-addon-scenario/scripts/owner_addon_cli.py recommendation_reason_tool --customer-id "C001" --product-codes "HEALTH_PLUS,ACCIDENT_GUARD"

# 生成话术
python /home/daytona/skills/chuangzhan-owner-addon-scenario/scripts/owner_addon_cli.py call_script_tool --customer-id "C001" --priority high

# 触客素材
python /home/daytona/skills/chuangzhan-owner-addon-scenario/scripts/owner_addon_cli.py outreach_material_tool --customer-id "C001" --scene "家庭保障"

# 外呼
python /home/daytona/skills/chuangzhan-owner-addon-scenario/scripts/owner_addon_cli.py outbound_call_tool --customer-id "C001" --agent "创展顾问小安"

# 全流程编排
python /home/daytona/skills/chuangzhan-owner-addon-scenario/scripts/run_owner_addon_flow.py --customer-id "C001" --agent "创展顾问小安"
```

## 调用规则（强约束）

1. 必须先完成客户池筛选，再进行推荐编排。
2. 推荐前必须完成需求洞察，不要跳过画像分析。
3. high 优先级客户必须执行外呼动作。

## 不要做的事

- 不要跳过客户筛选直接推荐产品。
- 不要在未生成推荐理由前直接输出销售结论。

## 输出规范

- 每个工具结果优先使用 `structuredContent`。
- 失败时返回 `status=error` 与明确错误信息（参数缺失、客户不存在、调用异常）。
- 最终结果必须包含客户分层、推荐清单、推荐理由、话术素材与下一步计划。

### 按工具结果的输出要求

#### `customer_pool_tool`

| 客户ID | 客户姓名 | 车险到期天数 | 最近互动天数 | 优先级 | 触达窗口 |
|--------|----------|--------------|--------------|--------|----------|
| {customer_id} | {customer_name} | {auto_policy_expire_days} | {last_interaction_days} | {priority} | {touch_window} |

#### `owner_profile_tool`

| 项目 | 内容 |
|------|------|
| 客户ID | {profile.customer_id} |
| 姓名 | {profile.customer_name} |
| 城市 | {profile.city} |
| 家庭结构 | {profile.family_structure} |
| 收入区间 | {profile.income_band} |

#### `demand_insight_tool`

| 需求标签 | 缺口分 | 月预算建议 | 年预算建议 | 下一步动作 |
|----------|--------|------------|------------|------------|
| {insight.need_tag} | {insight.gap_score} | {insight.monthly_budget} | {insight.annual_budget} | {insight.next_action} |

#### `non_auto_product_recommend_tool`

| 产品编码 | 产品名称 | 类型 | 建议保额 | 价格区间 | 匹配分 |
|----------|----------|------|----------|----------|--------|
| {recommendations[n].product_code} | {recommendations[n].product_name} | {recommendations[n].type} | {recommendations[n].coverage} | {recommendations[n].price_band} | {recommendations[n].match_score} |

#### `recommendation_reason_tool`

| 产品编码 | 推荐理由 | 命中特征 | 话术切入点 |
|----------|----------|----------|------------|
| {reasons[n].product_code} | {reasons[n].reason} | {reasons[n].matched_features} | {reasons[n].entry_point} |

#### `call_script_tool`

| 开场白 | 需求确认问句 | 产品切入句 | 异议处理句 | 收口动作 |
|--------|---------------|------------|------------|----------|
| {script.opening} | {script.need_question} | {script.product_entry} | {script.objection_handle} | {script.closing} |

#### `outreach_material_tool`

| 素材标题 | 素材类型 | 素材链接 | 适用客群 | 发送渠道 |
|----------|----------|----------|----------|----------|
| {materials[n].title} | {materials[n].type} | {materials[n].link} | {materials[n].segment} | {materials[n].channel} |

#### `outbound_call_tool`

| 外呼状态 | 沟通结果 | 预约时间 | 下一步计划 |
|----------|----------|----------|------------|
| {call_result.call_status} | {call_result.result_tag} | {call_result.appointment_time} | {call_result.next_action} |
