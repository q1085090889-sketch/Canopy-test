# Canopy 单一家办开发 Codex Agent SOP

## 核心目标

用 Codex Agent 半自动完成“找得到、看得准、联系得上”的单一家办开发任务。最终 30 家线索必须能触达到具体个人，而不是只有公司官网、公司总机或公司 LinkedIn。

## 最高优先级规则：必须到具体个人

最终名单的合格触达标准：

- 一级合格：个人商务邮箱，例如 `name@company.com`，且 Hunter 置信度达到配置阈值。
- 二级合格：个人 LinkedIn 主页，URL 必须是 `/in/` 类型，不是公司主页。
- 三级合格：个人直线电话、办公室分机或明确归属该联系人的办公电话。

不合格：

- 公司官网 contact-us 表单。
- 公司总机。
- `info@`、`contact@`、`enquiry@` 等公共邮箱。
- 公司 LinkedIn 页面。
- 只有公司名称，没有具体联系人。

不合格线索只能进入“待补充池”，不能进入最终 30 家。

## 什么客户真正适合 Canopy

强适配客户通常有这些特征：

- 跨银行、跨券商、跨托管行资产分散。
- 有外部管理人、私募基金、直接股权、地产、结构化产品或另类资产。
- 跨境资产明显，涉及多币种、多税区、多实体。
- 家族成员、投资团队、外部顾问需要看同一套资产视图。
- 仍在用 Excel、PDF 月报、银行后台截图或人工对账。
- 有代际传承、家族治理、审计留痕、合并报告需求。

弱适配客户：

- 只有单一经营公司，没有明确金融资产或家族资本平台。
- 公开信息显示主要是 MFO、财富顾问、基金销售或服务商。
- 只有公司层面的公共联系方式。
- 家族投资复杂度无法验证，且没有可触达个人。

## 最有效的评估维度

### 1. 产品匹配度 match_score

比单纯 AUM 更重要的是“资产数据复杂度”。判断信号包括托管行数量、外部管理人数量、跨币种资产、私募/直接投资比例、实体数量、报告频率和人工对账强度。

### 2. 触达可行性 reach_score

这是早期开拓最关键维度。个人商务邮箱、个人 LinkedIn、个人电话越明确，分数越高。公司入口不计高分。

### 3. 付费潜力 budget_score

看家族是否有专业投资团队、外部顾问、长期跨境资产和数字化预算。AUM 只是底线，不是充分条件。

### 4. 转化周期 cycle_score

看是否有明确痛点触发：报表混乱、外部管理人多、代际交接、审计要求、资产跨境扩张、团队刚扩编或系统替换窗口。

## 半监督 Workflow

### 阶段 1：候选发现

Codex 调 Apollo 拉候选，限制地区、职位、SFO 关键词和候选数量。

人工复核：

- 删除 MFO、基金销售、服务商、律师/信托顾问。
- 删除没有具体联系人的记录。
- 标记需要补充个人邮箱或 LinkedIn 的记录。

输出：`review_candidate_discovery.csv`

### 阶段 2：公开资料补全

Codex 调 Serper + Brave 查官网、媒体报道、家族背景、资产规模、跨境资产、业务类型和潜在管理痛点。

人工复核：

- 检查 source_urls 是否能支撑“单一家办或单一家族投资平台”判断。
- 标记 AUM 是否可靠。
- 判断 core_pain 是否真实，不允许模型凭空编造。

输出：`review_research_enrichment.csv`

### 阶段 3：个人触达补全

Codex 调 Hunter，用企业域名 + 个人姓名找商务邮箱。

人工复核：

- 个人邮箱优先，公共邮箱剔除。
- 没有邮箱但有个人 LinkedIn 的可以保留。
- 只有公司官网表单的剔除或退回补充。

### 阶段 4：评分与分级

Codex 用 Gemini 输出四维评分，但人工必须复核高分线索。

人工复核重点：

- 高分是否只是因为 AUM 大。
- 联系人是否真有采购影响力。
- 是否存在明显合规或声誉风险。
- 是否需要先通过银行、律所、信托、家办协会暖介绍。

输出：`review_before_outreach_generation.csv`

### 阶段 5：生成开发信

只有人工批准的线索进入 Gemini 生成英文开发信。

人工复核：

- 开头是否准确引用对方背景。
- 是否有未经证实的客户案例或夸张承诺。
- 是否包含 15 分钟演示邀约。
- 是否有退订/不再联系选项。

## 参数化任务颗粒度

操作者每次可在 `canopy_sfo_task_config.example.json` 中调整：

- `target_count`：最终要多少家。
- `candidate_limit`：初始抓取多少候选。
- `regions`：国家/地区范围。
- `target_titles`：目标职位。
- `min_aum_usd`：最低 AUM。
- `require_email`：是否必须个人邮箱。
- `min_email_confidence`：Hunter 邮箱置信度。
- `resources`：启用或关闭 Apollo、Serper、Brave、Hunter、Gemini。
- `human_review`：每个复核节点是否停下来。

## Codex Agent 运行方式

第一步先跑候选发现并停在人工复核：

```powershell
python .\canopy_sfo_pipeline.py --config .\canopy_sfo_task_config.example.json --out-dir .\output
```

复核 CSV 后，把 `approve` 改为 `Y` 或 `N`，再继续下一阶段：

```powershell
python .\canopy_sfo_pipeline.py --config .\canopy_sfo_task_config.example.json --review-input .\output\review_candidate_discovery.csv --out-dir .\output
```

## 合规要求

- 不爬取 LinkedIn 页面，只使用 Apollo/Hunter 等商业合规 enrichment 数据源和公开搜索结果。
- 陌生邮件单次发送不超过 10 封。
- 邮件必须提供不再联系或退订方式。
- 线索只用于 Canopy 商务开发，不转售、不外泄。
- 数据保存不超过 3 年。
- 客户要求删除数据时，7 日内清理。
- 台湾、香港和东南亚家办保留数据来源和使用记录备查。
