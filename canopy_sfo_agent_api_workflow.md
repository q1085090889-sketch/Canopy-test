# Canopy SFO Agent Workflow 与调用 API

## 目标

用 Codex Agent 本地闭环完成单一家办客户开发数据生产：

- 可动态配置国家/地区、目标开发客户数量、候选池数量、职位、AUM 门槛。
- 可动态选择调用 Apollo、Serper、Brave、Hunter、Gemini。
- 全流程保留人工半监督复核节点。
- 最终线索必须能联系到具体个人，而不是公司公共渠道。

## 完整 Workflow

### 阶段 1：Discover 候选发现

输入：

- `regions`：国家/地区，例如 `["Hong Kong", "Taiwan", "Thailand"]`
- `target_count`：最终目标客户数
- `candidate_limit`：候选池数量
- `target_titles`：CIO、FO Director、Principal 等
- `min_aum_usd`：最低 AUM

调用：

- Apollo：找候选机构、联系人姓名、职位、公司域名、LinkedIn 线索。

输出：

- `review_candidate_discovery.csv`

人工复核：

- 删除 MFO、服务商、基金销售、律所/信托顾问。
- 删除只有公司公共渠道的线索。
- 保留具体个人联系人。

### 阶段 2：Research 资料补全

输入：

- 人工批准后的 `review_candidate_discovery.csv`

调用：

- Serper + Brave：官网、媒体报道、家族背景、AUM、跨境资产、业务布局。
- Hunter：用公司域名 + 联系人姓名找个人商务邮箱。
- Gemini：结构化提取和四维评分。

输出：

- `review_research_enrichment.csv`
- `review_before_outreach_generation.csv`

人工复核：

- 检查 source URLs 是否支撑家族办公室判断。
- 检查邮箱是否为个人商务邮箱。
- 公司官网表单、公司总机、公共邮箱不合格。
- 高 AUM 但无资产复杂度证据的线索降级。

### 阶段 3：Outreach 触达内容生成

输入：

- 人工批准后的 `review_before_outreach_generation.csv`

调用：

- Gemini：生成 190-210 词英文个性化开发信。

输出：

- `canopy_sfo_validated_leads_YYYY-MM-DD.csv`
- `canopy_sfo_validated_leads_YYYY-MM-DD.json`
- `canopy_sfo_evaluation_workflow_YYYY-MM-DD.md`
- `run_manifest.json`

人工复核：

- 检查是否准确引用客户背景。
- 检查是否夸大或编造客户案例。
- 检查是否有温和邀约和不再联系选项。

## 评分逻辑

总分 40 分。

- `match_score` 产品匹配度：1-10 分。看跨境、多币种、多托管行、多实体、私募/地产/直接投资、人工报表压力。
- `reach_score` 触达可行性：1-10 分。个人邮箱/个人电话/个人 LinkedIn 才计分，公司公共渠道不计高分。
- `budget_score` 付费潜力：1-10 分。看资产体量、专业投资团队、财富科技预算、替换 Excel/旧系统意愿。
- `cycle_score` 转化周期：1-10 分。看数字化迫切度、决策链长度、近期资产扩张/重组/代际治理触发点。

客户等级：

- A 类高优：总分 >= 30
- B 类培育：20 <= 总分 < 30
- C 类低优：总分 < 20

## 启动 API Server

先在当前终端设置密钥环境变量。不要把密钥写入代码或配置文件。

```powershell
$env:APOLLO_API_KEY="..."
$env:HUNTER_API_KEY="..."
$env:SERPER_API_KEY="..."
$env:BRAVE_API_KEY="..."
$env:GEMINI_API_KEY="..."
$env:JWT_SECRET="..."
python .\canopy_sfo_agent_api.py --host 127.0.0.1 --port 8787
```

健康检查：

```powershell
curl http://127.0.0.1:8787/health
```

## API：创建任务

`POST /api/canopy-sfo/runs`

### Discover 示例

```json
{
  "stage": "discover",
  "config": {
    "task": {
      "target_count": 30,
      "candidate_limit": 60,
      "regions": ["Hong Kong", "Taiwan", "Mainland China", "Thailand", "Malaysia"],
      "min_aum_usd": 200000000,
      "require_email": true,
      "min_email_confidence": 70
    },
    "human_review": {
      "after_candidate_discovery": true,
      "after_research_enrichment": true,
      "before_outreach_generation": true
    }
  }
}
```

PowerShell 调用：

```powershell
$body = @{
  stage = "discover"
  config = @{
    task = @{
      target_count = 30
      candidate_limit = 60
      regions = @("Hong Kong", "Taiwan", "Mainland China", "Thailand", "Malaysia")
      min_aum_usd = 200000000
      require_email = $true
      min_email_confidence = 70
    }
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8787/api/canopy-sfo/runs" -ContentType "application/json" -Body $body
```

### Research 示例

人工复核 `review_candidate_discovery.csv` 后，把路径传入：

```json
{
  "stage": "research",
  "review_input": "C:\\Users\\admin\\Documents\\Canopy\\output\\api_runs\\RUN_ID\\review_candidate_discovery.csv",
  "config": {
    "task": {
      "target_count": 30,
      "candidate_limit": 60,
      "regions": ["Hong Kong", "Taiwan", "Thailand"]
    }
  }
}
```

### Outreach 示例

人工复核 `review_before_outreach_generation.csv` 后生成最终开发信：

```json
{
  "stage": "outreach",
  "review_input": "C:\\Users\\admin\\Documents\\Canopy\\output\\api_runs\\RUN_ID\\review_before_outreach_generation.csv",
  "config": {
    "task": {
      "target_count": 30,
      "regions": ["Hong Kong", "Taiwan", "Mainland China", "Thailand", "Malaysia"]
    }
  }
}
```

## API：查询任务

查询所有任务：

```powershell
Invoke-RestMethod "http://127.0.0.1:8787/api/canopy-sfo/runs"
```

查询单个任务：

```powershell
Invoke-RestMethod "http://127.0.0.1:8787/api/canopy-sfo/runs/RUN_ID"
```

返回字段：

- `run_id`
- `stage`
- `status`：running / succeeded / failed
- `run_dir`
- `config_path`
- `log_path`
- `artifacts`

## 动态配置字段

```json
{
  "task": {
    "target_count": 30,
    "candidate_limit": 60,
    "regions": ["Hong Kong", "Taiwan"],
    "target_titles": ["CIO", "Head of Family Office", "Principal"],
    "min_aum_usd": 200000000,
    "require_email": true,
    "min_email_confidence": 70
  },
  "resources": {
    "apollo": true,
    "serper": true,
    "brave": true,
    "hunter": true,
    "gemini_scoring": true,
    "gemini_outreach": true
  },
  "human_review": {
    "after_candidate_discovery": true,
    "after_research_enrichment": true,
    "before_outreach_generation": true
  },
  "rate_limit": {
    "request_delay_seconds": 1.2
  }
}
```

## 关键约束

最终输出必须满足：

- 有具体个人姓名。
- 有具体职位。
- 有个人商务邮箱、个人电话或个人 LinkedIn。
- 公共邮箱、公司官网表单、公司 LinkedIn 不算合格触达。
- 每条线索必须保留 source URLs 和人工复核记录。
