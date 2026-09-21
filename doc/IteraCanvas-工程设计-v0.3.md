# IteraCanvas（迭绘）工程设计

## 文档信息

- 文档版本：v0.3
- 创建时间：2026-09-21 14:03:59（Asia/Shanghai）
- 最近修订：2026-09-21 18:31:27（Asia/Shanghai）
- 需求依据：[`IteraCanvas-产品需求规格-v0.2-20260920-175518.md`](./IteraCanvas-产品需求规格-v0.2-20260920-175518.md)
- 文档状态：工程设计草案
- 适用阶段：本地单用户 Demo
- 目标读者：产品、AI 工程、后端、前端、测试与课程项目评审人员
- 工程设计唯一事实来源：是

> 产品规格当前仍是非基线草案。本方案给出可以开始实现的最小技术路径，但第 4 章列出的产品决策在冻结前仍可能引起数据结构、接口和验收标准变化。

> v0.3 已关闭产品规格中的 P0-02 工程处置问题：旧提示词 RAG、知识库、三模式实验及其入口全部退出，新项目不承担向后兼容。后续提升产品规格版本时应同步写入该决策。

## 0. 文档治理与边界

本文件是项目唯一的工程设计文档。文件名携带当前版本号；后续架构、数据模型、AI 流程、接口、部署和测试设计均通过重命名该唯一文件并提升版本号完成，不保留并行工程设计副本，也不再创建平行的“技术方案”“架构设计”或带时间戳的工程文档。

| 内容 | 唯一事实来源 | 说明 |
| --- | --- | --- |
| 当前产品需求 | `doc/IteraCanvas-产品需求规格-v0.2-20260920-175518.md` | 定义业务目标、范围、规则和验收意图 |
| 工程设计 | `doc/IteraCanvas-工程设计-v0.3.md` | 定义架构、数据、AI、API、实施和测试方法 |
| 安装与运行 | `README.md` | 只写操作说明，不新增架构决策 |
| Skills 采集状态 | `data/skills-showcase/manifest.json` | 只记录来源、版本、哈希、授权与发布状态 |
| 旧 RAG 架构图 | `outputs/legacy-rag-architecture/` | 仅作历史参考，不属于当前实现或验收范围 |

治理规则：

1. 业务规则以当前产品规格为准，本文件只引用其含义并落实为工程约束，不另建一套需求。
2. 产品规格变化后，在本文件对应章节更新实现影响；不得通过新增工程文档规避冲突。
3. 架构图是本文件的附件，不是独立决策来源；图与正文冲突时以本文件正文为准。
4. 历史产品规格可以保留用于追溯，但只有 README 标记的“当前产品需求”可指导实现。
5. README、代码注释和测试说明不得复制整段需求；应链接到产品规格或本文件的稳定章节。

### 0.1 修订记录

| 版本 | 时间 | 说明 |
| --- | --- | --- |
| v0.1 | 2026-09-21 14:03:59 | 首次形成完整 AI 工程实现方案 |
| v0.2 | 2026-09-21 14:57:53 | 固定带版本号的唯一工程设计入口，明确文档治理和旧 RAG 架构附件边界 |
| v0.3 | 2026-09-21 18:31:27 | 冻结旧 RAG 退出决策，改为清理旧 `src` 后按 IteraCanvas 目标结构重写 |

## 1. 实现结论

本项目不再基于旧 RAG 原型增量改造。采用以下路线：

1. 删除 `src/` 中仅服务旧提示词 RAG、知识库、三模式实验、CLI 和 Streamlit 演示的实现。
2. 保留 Python、FastAPI 和静态 HTML/JavaScript 技术栈，但按 IteraCanvas 领域模型重写应用入口和页面。
3. 新应用只提供 `/api/v1` 业务接口，不兼容 `/api/optimize`、`/api/status` 和 `/api/rebuild-kb`。
4. 使用 SQLite 保存任务状态和结构化结果，使用本地文件目录保存图片。
5. 先用固定 JSON 模拟模型跑通完整闭环，再接入一个真实多模态模型。
6. 主链路实现“任务—规格—轮次—图片—诊断—复核—补丁—下一轮—接受结果”。
7. Skills 展厅作为只读次级模块，从本地清单加载，只展示已通过授权与发布审核的条目，不执行 Skill。
8. Demo 不实现 RAG、向量数据库、多供应商框架、消息队列、微服务、多人权限、在线安装和语义推荐。

最小可交付闭环为：

```text
创建任务
→ 形成并确认规格版本
→ 创建外部生成轮次
→ 分批上传候选图
→ 获取结构化诊断
→ 用户复核诊断
→ 生成差异补丁和完整可复制结果
→ 创建下一轮或接受结果
```

## 2. 工程原则

### 2.1 单体优先

- 保留 Python、FastAPI 和当前静态 HTML/JavaScript 技术栈。
- 只运行 IteraCanvas 单体应用，不保留旧服务、旧入口或兼容层。
- 不为本地单用户 Demo 引入 Redis、Celery、Kafka、Docker 编排或独立前端构建链。

### 2.2 数据先于模型

- 在调用真实模型前，先冻结任务、规格版本、轮次、图片、诊断和补丁之间的绑定关系。
- AI 输出必须经过结构化校验后才能进入业务表。
- 原始 AI 结果、用户复核结果和最终有效结论分开保存。

### 2.3 模拟先于真实调用

- 先用可重复的模拟响应完成 API、页面、状态机和异常测试。
- 供应商确定后只实现一个真实多模态客户端。
- 模拟模式和真实模式必须使用同一组输入、输出模型。

### 2.4 历史不可被新状态改写

- 已确认的规格版本不可变。
- 轮次、诊断和补丁始终绑定产生时的规格版本。
- 用户纠正通过追加复核记录实现，不覆盖 AI 原始诊断。

### 2.5 明确失败，而不是产生半成品

- 模型超时、限流、结构无效或授权缺失时，诊断任务进入可重试失败状态。
- 失败调用不得推进轮次状态，不得保存半完整诊断，也不得删除已有历史。

## 3. 当前代码与目标能力差距

| 能力 | 当前仓库状态 | 目标状态 | 处理方式 |
| --- | --- | --- | --- |
| FastAPI 服务 | 仅有旧提示词优化接口 | 承载 IteraCanvas `/api/v1` | 保留入口文件名，删除旧路由并重写 |
| RAG | 已实现加载、切分、向量化、检索和生成 | 当前产品不需要 | 删除实现和依赖，不建立兼容层 |
| LLM 客户端 | 仅支持 DeepSeek 文本 Chat Completions | 支持一套多模态诊断调用 | 删除旧客户端，新增统一 AI 调用模块 |
| 页面 | 当前是提示词优化原型 | 支持多步任务工作区 | 删除旧页面并新建 IteraCanvas 页面 |
| 结构化存储 | 无业务数据库 | SQLite 持久化完整历史 | 新增数据库与迁移初始化 |
| 图片存储 | 无任务级文件管理 | 原图、脱敏副本和引用图隔离保存 | 新增本地文件存储模块 |
| 规格版本 | 未实现 | 不可变版本并可追溯 | 新增领域模型和状态规则 |
| 生成轮次 | 未实现 | 一轮多提交、多候选图 | 新增轮次、提交和候选图模型 |
| 诊断与复核 | 未实现 | 结构化诊断、用户纠正与有效结论 | 新增 AI 流程和复核记录 |
| 修改补丁 | 未实现 | 差异、基准和合并结果同时保存 | 新增补丁生成与一致性校验 |
| Skills 展厅 | 已有 8 项清单、正文快照与授权状态 | 只读搜索、详情和复制 | 直接读取清单，不建立向量库 |
| 实验计量 | 旧三模式实验与当前目标不一致 | 人工流程与诊断助手流程对比 | 删除旧实验，按当前指标重新实现 |

## 4. 开发前决策门

以下内容未确定时可以开发模拟闭环，但不能宣称完成正式验收：

| 决策 | 本方案采用的暂定工程假设 | 未确认时的限制 |
| --- | --- | --- |
| 旧 RAG 处置（已确认） | 完全退出；删除旧接口、实现和实验脚本 | v0.3 已关闭，不再作为开发前阻塞项 |
| 生成轮次 | 一次外部生成请求是一轮，上传是提交 | 页面必须让用户选择追加或新建轮次 |
| 规格版本 | 每次保存修改创建新版本，确认后不可变 | 不允许覆盖历史规格 JSON |
| Skills 展厅关系 | 独立次级入口，不计入诊断主指标 | 不强行设计跨模块自动执行 |
| 多模态供应商 | 模拟客户端优先，正式供应商待定 | 不编写多供应商抽象层 |
| 授权范围 | 按任务、供应商、模型、用途和政策版本记录 | 未授权时只允许本地操作 |
| 实验最大轮次和预算 | 通过配置管理，正式实验前冻结 | 只能做预实验，不能形成正式结论 |
| 图片和时限阈值 | 使用第 17 章候选默认值 | 供应商确定后取更严格限制 |

## 5. 工程范围映射

本章用于说明产品规格如何落到工程交付，不是第二份需求清单。如与产品规格冲突，以当前产品规格为准，并同步修订本工程设计。

### 5.1 Demo 必须实现

- 任务创建、查看、分支、接受和本地删除。
- 自由文本需求输入、AI 规格提取、集中追问、用户确认与规格版本。
- 参考图上传及参考用途确认。
- 生成轮次、分批提交、一轮多图、重复文件识别和归属选择。
- 图片格式、大小、像素和数量校验。
- 模拟与真实多模态诊断、结构校验、失败重试和状态查询。
- 用户确认、纠正、不适用、无法判断和撤销纠正。
- 差异补丁、完整提示词、完整参数和冲突提示。
- 当前轮与上一轮的逐要求变化展示。
- 授权记录、调用记录和本地删除审计。
- Skills 展厅列表、关键词搜索、筛选、详情和复制。
- 对比实验需要的轮次、耗时、成本和通过率导出。

### 5.2 Demo 明确不实现

- 内置图片生成。
- 自动选出最佳图片。
- 多用户、登录、云同步和协作。
- 多供应商动态切换、复杂路由或自动降级。
- 在 Web 中运行、安装或下载 Skill。
- 在线抓取 GitHub、自动更新 Skill 或绕过授权状态发布。
- 向量化的 Skill 推荐；8 个条目使用普通搜索和标签即可。
- 微服务、分布式任务系统和独立运维平台。

## 6. 总体架构

```text
浏览器静态页面
    │  fetch / FormData / 轮询
    ▼
FastAPI 单体应用
    └─ 业务接口：/api/v1/*
       ├─ 任务与规格服务
       ├─ 轮次与图片服务
       ├─ 诊断、复核与补丁服务
       ├─ 授权与删除服务
       └─ Skills 展厅服务
              │
    ┌─────────┼──────────┐
    ▼         ▼          ▼
 SQLite    本地文件     AI 调用层
                       ├─ mock
                       └─ 单一真实多模态供应商
```

### 6.1 组件职责

| 组件 | 职责 | 不负责 |
| --- | --- | --- |
| Web UI | 收集输入、上传图片、展示状态和结果 | 不推断业务状态，不直接访问文件路径 |
| API 路由 | 参数校验、权限边界、响应与错误码 | 不拼装复杂 Prompt |
| 应用服务 | 执行状态转换、事务和业务规则 | 不保存全局内存真相 |
| SQLite | 保存结构化状态、版本、结果和审计 | 不保存图片二进制 |
| 文件存储 | 保存原图、脱敏副本和参考图 | 不使用用户文件名作为真实路径 |
| AI 调用层 | Prompt 组装、模型调用、重试和结构校验 | 不直接修改任务状态 |
| Skills 展厅 | 读取本地发布清单并提供搜索详情 | 不执行 Skill，不自动联网同步 |

### 6.2 运行拓扑

- 本地单进程运行，默认只监听 `127.0.0.1`。
- 一个 Uvicorn 进程、一个 SQLite 文件、一个运行时文件目录。
- AI 任务通过 FastAPI `BackgroundTasks` 执行并由前端轮询状态。
- 进程重启时，将遗留的 `queued`、`running` 状态改为 `failed_interrupted`，由用户手动重试。

> 这是 Demo 的刻意简化。只有当出现多用户、跨机器执行或任务丢失不可接受时，才引入真正的持久任务队列。

## 7. 领域模型与状态规则

### 7.1 核心术语

| 术语 | 工程定义 |
| --- | --- |
| 任务 `task` | 一次持续迭代的创作目标；重大目标变化产生分支任务 |
| 规格版本 `spec_version` | 某一时刻完整创作规格的不可变快照 |
| 要求 `criterion` | 规格中的单条可判断要求，拥有跨版本稳定 ID |
| 生成轮次 `generation_round` | 用户在外部平台发起的一次生成请求 |
| 图片提交 `submission` | 用户向指定轮次执行的一次上传动作 |
| 候选图 `candidate` | 某次外部生成返回的一张图片 |
| 诊断 `diagnosis` | 针对一个候选图和一个规格版本产生的 AI 结果 |
| 诊断复核 `diagnosis_review` | 用户对某条诊断进行确认或纠正的追加记录 |
| 补丁 `patch` | 从基准提示词与参数到合并结果的结构化修改集合 |

### 7.2 任务状态

```text
draft → active → accepted
  │        │
  └────────┴─→ branch（创建新任务，不改变父任务历史）
```

- `draft`：任务已创建，但尚无确认规格。
- `active`：至少有一个确认规格版本，可以创建生成轮次。
- `accepted`：用户接受某个候选图；仍可查看和导出，但继续迭代前必须重新激活或创建分支，具体交互由产品确认。
- 删除采用物理删除流程，不增加 `deleted` 业务状态。

### 7.3 规格版本状态

```text
draft → confirmed
```

- 草稿版本允许编辑，但每次点击“保存规格”即生成新的版本记录。
- `confirmed` 版本禁止修改内容；后续编辑从它复制生成新草稿版本。
- `criterion_id` 在要求语义不变时沿用；新增要求生成新 ID；删除的要求不进入新版本。
- AI 推断不会因“确认整份规格”自动变成用户明确要求，除非用户逐项或批量勾选确认。

### 7.4 轮次状态

```text
waiting_images
    → diagnosing
    → awaiting_review
    → patch_ready
    → closed
```

- 一个轮次只能绑定一个确认的规格版本。
- 分批上传不会自动增加轮次编号。
- 同一 SHA-256 文件在同一轮次内只创建一个候选图；跨轮上传相同文件允许，但页面必须警告。
- 候选图尚未产生诊断时允许修改轮次归属；已产生诊断后必须先删除该候选图的诊断链或重新上传，避免历史绑定被静默改写。

### 7.5 诊断任务状态

```text
queued → running → succeeded
                 ↘ failed_retryable
                 ↘ failed_final
```

- `failed_retryable`：超时、限流、服务端错误、进程中断或一次结构校验失败。
- `failed_final`：未授权、不支持的图片、超过最大重试次数或模型持续返回无效结果。
- 重试创建新的模型调用记录，但复用同一个业务诊断 ID，成功前不得产生有效诊断项。

## 8. SQLite 数据设计

### 8.1 选型

- 使用 Python 标准库 `sqlite3`，不引入 ORM。
- 启动时执行 `PRAGMA foreign_keys = ON` 和 `PRAGMA journal_mode = WAL`。
- 使用 `PRAGMA user_version` 管理小规模手写迁移。
- 主键使用 UUID 字符串；时间统一保存 UTC ISO 8601，界面转换为本地时区。
- JSON 字段以 UTF-8 文本保存，写入前必须通过 Pydantic 模型校验。

### 8.2 表结构

| 表 | 关键字段 | 关键约束 |
| --- | --- | --- |
| `tasks` | `id`、`parent_task_id`、`title`、`status`、`current_spec_version_id`、`accepted_candidate_id` | 父任务删除策略需明确；状态值受检查约束 |
| `spec_versions` | `id`、`task_id`、`version_no`、`status`、`source_version_id`、`spec_json`、`created_at` | `task_id + version_no` 唯一；确认后禁止更新 `spec_json` |
| `generation_rounds` | `id`、`task_id`、`round_no`、`spec_version_id`、`platform`、`model_name`、`prompt_snapshot`、`params_json`、`status` | `task_id + round_no` 唯一；必须绑定确认规格 |
| `submissions` | `id`、`round_id`、`submitted_at`、`note` | 一轮可以有多次提交 |
| `candidates` | `id`、`round_id`、`submission_id`、`original_path`、`sanitized_path`、`sha256`、`mime_type`、`width`、`height`、`created_at` | `round_id + sha256` 唯一 |
| `diagnoses` | `id`、`candidate_id`、`spec_version_id`、`status`、`prompt_version`、`result_json`、`error_json`、`created_at`、`completed_at` | 成功前 `result_json` 为空；候选图与规格版本不可改 |
| `diagnosis_reviews` | `id`、`diagnosis_id`、`item_id`、`decision`、`corrected_json`、`created_at` | 只追加不覆盖；最新一条是当前有效复核 |
| `patches` | `id`、`task_id`、`source_round_id`、`source_spec_version_id`、`selected_item_ids_json`、`base_prompt`、`base_params_json`、`diff_json`、`merged_prompt`、`merged_params_json`、`created_at` | 基准、差异和合并结果同时保存 |
| `consents` | `id`、`task_id`、`provider`、`model_name`、`purpose`、`data_types_json`、`policy_version`、`granted_at`、`revoked_at` | 只有未撤回且范围完全匹配的授权有效 |
| `model_calls` | `id`、`task_id`、`diagnosis_id`、`provider`、`model_name`、`prompt_version`、`request_hash`、`image_hashes_json`、`status`、`attempt_no`、`latency_ms`、`usage_json`、`error_code` | 不保存图片 Base64；随任务删除 |
| `audit_events` | `id`、`task_id`、`event_type`、`entity_type`、`entity_id`、`details_json`、`created_at` | 记录关键状态、授权、调用和删除动作 |
| `idempotency_keys` | `key`、`operation`、`request_hash`、`response_json`、`created_at` | 相同 key 和不同请求哈希返回冲突 |
| `deletion_jobs` | `id`、`deleted_task_id`、`paths_json`、`status`、`error_json`、`created_at`、`completed_at` | 不依赖任务外键，任务删除后仍保留最小删除结果 |

### 8.3 规格 JSON 结构

`spec_versions.spec_json` 保存完整快照：

```json
{
  "context": {
    "purpose": "电商主图",
    "platform": "通用",
    "audience": "年轻消费者",
    "subject": "香水瓶",
    "scene": "深色摄影棚",
    "style": "极简商业摄影",
    "composition": "居中构图",
    "color": "黑金",
    "lighting": "轮廓光",
    "aspect_ratio": "1:1",
    "text_requirements": [],
    "negative_requirements": []
  },
  "criteria": [
    {
      "criterion_id": "crt_uuid",
      "category": "subject",
      "statement": "香水瓶标签清晰可辨",
      "importance": "hard",
      "source": "user",
      "status": "confirmed",
      "verification_mode": "visual"
    }
  ],
  "reference_images": []
}
```

### 8.4 有效诊断结论

系统不直接修改 AI 结果，而是按以下顺序计算当前有效结论：

1. 读取 `diagnoses.result_json` 中的原始诊断项。
2. 按 `diagnosis_id + item_id` 查询最新复核记录。
3. 若无复核，使用 AI 原始结论并标记“未复核”。
4. 若用户确认，使用原始结论并标记“用户已确认”。
5. 若用户纠正，使用 `corrected_json`。
6. 若用户选择不适用或无法判断，后续补丁和通过率按相应规则排除。

该计算由一个公共函数完成，页面、补丁生成和实验统计必须复用同一结果。

## 9. 文件存储设计

### 9.1 目录

```text
runtime/
├─ iteracanvas.db
├─ tmp/
├─ trash/
└─ tasks/
   └─ <task_id>/
      ├─ references/
      └─ rounds/
         └─ <round_id>/
            ├─ originals/
            └─ sanitized/
```

- `runtime/` 必须加入 `.gitignore`。
- 数据库只保存相对 `runtime/` 的受控路径，不保存任意绝对路径。
- 文件名使用候选图 UUID 和服务端确定的扩展名，不使用用户原文件名。

### 9.2 上传事务

1. 先写入 `runtime/tmp/<uuid>`。
2. 检查字节数，使用图片解码验证真实格式、尺寸和像素总量。
3. 计算 SHA-256，并检查同轮重复文件。
4. 生成去除 EXIF 的发送副本；原图保持不变。
5. 将两个文件移动到任务目录。
6. 在一个数据库事务中创建提交和候选图记录。
7. 数据库写入失败时删除本次新文件；文件移动失败时回滚数据库事务。

### 9.3 路径与图片安全

- 只接受 PNG、JPEG 和 WebP 的有效解码结果，不能只相信扩展名或请求头。
- 拒绝包含路径分隔符的服务端文件标识，所有路径通过 `Path.resolve()` 校验仍位于任务根目录。
- 配置 Pillow 的最大像素限制，防止解压炸弹图片。
- 发送给第三方的是脱敏副本，不记录图片 Base64，不在错误日志输出本地绝对路径。
- 删除任务前先解析并验证所有目标路径均位于对应任务目录，再删除文件与数据库记录。

## 10. AI 工程流程

### 10.1 调用层设计

新增一个 `ai_gateway.py`，只暴露以下三个业务函数：

```python
extract_spec(task_text, reference_images) -> SpecExtractionResult
diagnose_candidate(spec, candidate, references, generation_context) -> DiagnosisResult
generate_patch(spec, reviewed_items, base_prompt, base_params) -> PatchResult
```

- 通过 `AI_MODE=mock|real` 切换模拟和真实调用。
- 模拟与真实实现返回相同 Pydantic 模型。
- 供应商确定前不创建通用 Provider 接口、工厂或插件系统。
- 真实模式只支持一个供应商和一个已配置模型。

### 10.2 Prompt 版本管理

Prompt 以 Python 多行字符串集中保存在 `ai_prompts.py`，每个流程具有明确版本：

- `spec_extract.v1`
- `image_diagnosis.v1`
- `patch_generation.v1`

每次模型调用记录 Prompt 版本、模型、请求哈希和图片哈希。修改 Prompt 且可能改变输出语义时必须提升版本；只修正文案错字可以不升版本，但应保留 Git 记录。

Demo 阶段不引入 Prompt 管理平台。测试夹具与正式调用都通过同一 Prompt 构造函数生成输入。

### 10.3 创作规格提取

输入：

- 用户自由文本。
- 参考图片及用户声明的参考用途。
- 当前规格版本；首次创建时为空。

模型输出：

```json
{
  "context": {},
  "criteria": [
    {
      "criterion_id": "crt_uuid",
      "category": "composition",
      "statement": "主体位于画面中央",
      "importance": "hard",
      "source": "user",
      "status": "confirmed",
      "verification_mode": "visual"
    }
  ],
  "missing_questions": [
    {
      "question_id": "q_uuid",
      "question": "图片计划用于什么场景？",
      "affects": ["purpose", "aspect_ratio"],
      "required": false
    }
  ],
  "inferences": [
    {
      "field": "style",
      "value": "极简",
      "confidence": "medium",
      "reason": "根据用户描述推断"
    }
  ]
}
```

处理规则：

- 明确来自用户原文的要求才可标记 `source=user`。
- 模型推断一律为 `source=ai_inference`、`status=pending`。
- 跳过问题保存为 `unknown/skipped`，不生成硬约束。
- 一次集中返回全部关键缺失问题，页面不逐题调用模型。
- 用户回答后重新调用提取流程并创建新规格版本，不原地修改旧版本。

### 10.4 候选图诊断

每张候选图独立诊断，输入包括：

- 候选图的脱敏副本。
- 当前轮次绑定的完整规格版本。
- 参考图片及用途。
- 可选的外部平台、模型、提示词和参数快照。
- 可选的上一轮已选候选图摘要；不要求模型自动排名多张图片。

结构化输出：

```json
{
  "summary": "整体主体正确，但标签文字不可读。",
  "items": [
    {
      "item_id": "diag_item_uuid",
      "criterion_id": "crt_uuid",
      "kind": "criterion",
      "verdict": "fail",
      "evidence": {
        "description": "瓶身中央标签文字模糊",
        "region": "画面中央偏下"
      },
      "severity": "high",
      "confidence": "high",
      "possible_causes": ["生成模型对小字处理不稳定"],
      "violates_confirmed_hard_constraint": true
    }
  ],
  "observations": [],
  "uncertainties": []
}
```

诊断规则：

- `verdict` 只允许 `pass`、`fail`、`uncertain`、`not_applicable`。
- 没有经过用户确认的 AI 推断不得产生硬约束失败。
- 审美、商业和参考图观察放入独立观察项，不伪装成规格要求。
- 置信度使用 `low/medium/high`，不显示未经校准的伪精确百分比。
- 模型必须给出可读证据位置；边界框为可选信息，不把模型估计的坐标当作精确标注。
- 一张图片诊断失败不应删除同轮其他图片的成功诊断。

### 10.5 用户复核

用户对每条诊断可以执行：

- `confirm`：接受 AI 原结论。
- `correct`：修改结论、证据或原因。
- `not_applicable`：本条不适用于当前任务。
- `cannot_judge`：用户暂时无法判断。
- `revert`：撤销上一次复核，恢复到前一条有效记录。

后续补丁只读取“有效诊断结论”公共函数的结果。AI 原始 JSON 永不因用户复核而被覆盖。

### 10.6 补丁生成

输入：

- 用户选中的有效诊断项 ID。
- 来源规格版本。
- 来源轮次的提示词和参数快照。
- 已确认需要保持不变的正确部分。

输出：

```json
{
  "prompt_changes": [
    {
      "operation": "add",
      "from": null,
      "to": "瓶身标签使用大号清晰无衬线字体",
      "reason": "提高标签可读性",
      "diagnosis_item_ids": ["diag_item_uuid"]
    }
  ],
  "parameter_changes": [
    {
      "name": "aspect_ratio",
      "old_value": "1:1",
      "new_value": "1:1",
      "operation": "keep"
    }
  ],
  "keep_unchanged": ["黑金配色", "居中构图"],
  "conflicts": [],
  "side_effects": [],
  "merged_prompt": "完整、可直接复制的提示词",
  "merged_params": {}
}
```

校验规则：

- 保存基准快照、结构化差异和完整合并结果。
- 参数对象由服务端应用 `add/replace/remove/keep` 操作并重新计算，检查模型给出的 `merged_params` 是否一致。
- 自然语言提示词难以稳定应用字符级操作，因此以模型返回的 `merged_prompt` 为可复制结果；界面使用 Python `difflib` 生成展示差异。
- 任何冲突必须在响应中显式列出；存在未解决冲突时，不把补丁标记为可直接应用。
- 未提供原提示词时，可以生成“建议补充片段”和新的完整建议，但必须标记基准缺失，不能声称是精确差异。

### 10.7 轮次比较

Demo 不额外调用模型进行轮次比较。比较逻辑基于稳定的 `criterion_id` 和有效诊断结论确定：

| 上一轮 | 当前轮 | 结果 |
| --- | --- | --- |
| `fail` | `pass` | 改善 |
| `pass` | `fail` | 退步 |
| 相同 | 相同 | 无变化 |
| 任一为 `uncertain` | 任意 | 不确定 |
| 当前规格不存在该要求 | 任意 | 不比较 |

审美观察由于没有稳定规格 ID，只展示新增、消失或文字变化，不参与硬约束通过率。

### 10.8 旧 RAG 退出边界

- 当前实现不加载知识库、不生成向量、不访问向量数据库，也不提供 RAG 配置项。
- 规格提取、图片诊断和补丁生成只使用任务数据、用户确认信息和当前模型调用上下文。
- 旧 RAG 源码、接口、CLI、Streamlit 页面和三模式实验不迁移到新应用。
- `outputs/legacy-rag-architecture/` 仅作历史参考，不构成运行时依赖。
- 若未来重新引入检索增强，必须先提升工程设计版本并定义数据来源、失败降级、实验分组和验收标准。

### 10.9 结构校验和修复

- 使用 Pydantic 严格模型，枚举限制状态值，未知字段拒绝写入。
- 模型原始响应先解析 JSON，再进行业务校验。
- 第一次结构无效时，可以用错误摘要执行一次“只修复 JSON 结构”的重试。
- 第二次仍无效则进入 `failed_retryable` 或 `failed_final`，不得使用不完整字段拼凑结果。
- 模型输出中的 ID 必须属于请求上下文；未知 `criterion_id` 和 `diagnosis_item_id` 直接拒绝。

### 10.10 调用、重试与幂等

1. API 校验候选图、规格版本和有效授权。
2. 创建诊断业务记录和模型调用记录。
3. 返回 `202 Accepted` 与诊断 ID。
4. 后台任务将状态改为 `running` 并发起调用。
5. 仅对连接错误、超时、HTTP 429 和 5xx 重试。
6. 使用短指数退避，最多执行配置的重试次数。
7. 成功后在一个数据库事务内保存完整结果并更新状态。
8. 前端通过 `GET /api/v1/diagnoses/{id}` 轮询。

所有产生副作用的 POST 请求接受 `Idempotency-Key`。相同键与相同请求返回第一次结果；相同键与不同请求返回 `409 Conflict`。

## 11. Skills 展厅实现

### 11.1 数据来源

- `data/skills-showcase/manifest.json` 继续作为采集来源、版本、哈希和授权状态的唯一事实来源。
- 清单中的 `publication_status` 只代表许可证门槛，不等于已经在展厅发布。
- 建议为每项新增 `gallery_status`：`draft`、`published`、`archived`。
- 只有 `gallery_status=published` 且许可证状态允许展示的条目才进入用户列表。
- `blocked_no_license` 和 `blocked_redistribution` 永远不能被管理员强制发布。

### 11.2 发布校验

发布命令按顺序检查：

1. `manifest.json` 可以解析，ID 唯一。
2. `local_path` 位于允许的采集根目录内。
3. `SKILL.md` 存在，实际 SHA-256 与清单一致。
4. frontmatter 至少包含 `name` 和 `description`。
5. 展厅别名和实际调用名分别保存，不要求相同。
6. 来源 URL、提交哈希、许可证和署名信息完整。
7. 完整包声称引用的脚本、参考和资源均存在；`content_only` 条目明确标注非完整包。
8. 授权状态允许当前展示方式。

管理员发布使用 CLI 即可：

```powershell
python -m src.skills_catalog validate
python -m src.skills_catalog publish <skill-id>
```

Demo 不需要管理员 Web 后台。

### 11.3 用户发现 Skill

8 个首批条目不需要向量数据库。服务启动时构建内存索引，搜索以下字段：

- 展厅标题和实际 Skill 名称。
- 简介和适用任务。
- 输入类型：文字、照片、数据、参考图。
- 输出类型：图片、海报、科研图、界面等。
- 风格和场景标签。

搜索使用 Unicode `casefold()` 后的普通包含匹配，筛选采用精确标签匹配。详情页必须显示推荐理由、来源、版本、许可证、完整性状态和复制范围。

## 12. REST API 设计

### 12.1 接口策略

- 新产品接口统一使用 `/api/v1`。
- 删除 `/api/status`、`/api/optimize` 和 `/api/rebuild-kb`，不提供兼容别名。
- 错误响应统一包含 `code`、`message`、`details` 和 `request_id`。
- 上传接口使用 `multipart/form-data`，其他接口使用 JSON。

### 12.2 核心接口

| 方法与路径 | 用途 | 成功响应 |
| --- | --- | --- |
| `POST /api/v1/tasks` | 创建任务 | `201` 任务摘要 |
| `GET /api/v1/tasks` | 任务列表 | `200` 分页列表 |
| `GET /api/v1/tasks/{task_id}` | 获取任务及当前状态 | `200` 任务详情 |
| `POST /api/v1/tasks/{task_id}/spec-versions` | 保存新的规格版本 | `201` 规格版本 |
| `POST /api/v1/spec-versions/{id}/confirm` | 确认规格版本 | `200` 已确认版本 |
| `POST /api/v1/tasks/{task_id}/branches` | 从指定状态创建分支 | `201` 新任务 |
| `POST /api/v1/tasks/{task_id}/rounds` | 创建生成轮次 | `201` 轮次 |
| `POST /api/v1/rounds/{round_id}/submissions` | 分批上传候选图 | `201` 提交与候选图列表 |
| `POST /api/v1/candidates/{candidate_id}/diagnoses` | 启动诊断 | `202` 诊断任务 |
| `GET /api/v1/diagnoses/{diagnosis_id}` | 查询诊断状态和结果 | `200` 诊断 |
| `POST /api/v1/diagnoses/{id}/reviews` | 追加用户复核 | `201` 复核记录 |
| `POST /api/v1/rounds/{round_id}/patches` | 根据选中问题生成补丁 | `202` 补丁任务或 `201` 模拟结果 |
| `GET /api/v1/rounds/{round_id}/comparison` | 与上一轮比较 | `200` 差异结果 |
| `POST /api/v1/tasks/{task_id}/accept` | 接受候选图并完成任务 | `200` 任务状态 |
| `POST /api/v1/tasks/{task_id}/consents` | 授予外部调用授权 | `201` 授权记录 |
| `POST /api/v1/consents/{id}/revoke` | 撤回授权 | `200` 授权状态 |
| `DELETE /api/v1/tasks/{task_id}` | 删除受控本地数据 | `200` 删除报告 |
| `GET /api/v1/skills` | 搜索和筛选已发布 Skill | `200` 列表 |
| `GET /api/v1/skills/{skill_id}` | Skill 详情与可复制内容 | `200` 详情 |

### 12.3 关键错误码

| HTTP | 业务错误码 | 场景 |
| --- | --- | --- |
| `400` | `INVALID_STATE_TRANSITION` | 当前状态不允许执行操作 |
| `400` | `INVALID_IMAGE` | 文件不是有效支持图片 |
| `403` | `CONSENT_REQUIRED` | 缺少匹配的外部调用授权 |
| `404` | `ENTITY_NOT_FOUND` | 任务、轮次或诊断不存在 |
| `409` | `DUPLICATE_CANDIDATE` | 同轮重复图片 |
| `409` | `IDEMPOTENCY_CONFLICT` | 幂等键被不同请求复用 |
| `413` | `UPLOAD_LIMIT_EXCEEDED` | 文件、数量或任务容量超限 |
| `422` | `MODEL_OUTPUT_INVALID` | 模型输出未通过结构校验 |
| `429` | `MODEL_RATE_LIMITED` | 供应商限流且重试耗尽 |
| `502` | `MODEL_PROVIDER_ERROR` | 上游模型服务失败 |
| `504` | `MODEL_TIMEOUT` | 调用超过时限 |

## 13. Web 页面设计

Demo 使用原生 HTML、CSS 和 JavaScript，不引入 React/Vue 构建链。

### 13.1 页面区域

1. **任务列表**：创建、继续、分支和删除任务。
2. **规格工作区**：自由文本、参考图、集中问题、要求列表和版本标识。
3. **轮次工作区**：创建轮次、选择追加或新轮、分批上传和候选图卡片。
4. **诊断工作区**：逐要求结论、证据、复核动作和选中修复项。
5. **补丁工作区**：差异视图、完整提示词、完整参数、冲突和复制按钮。
6. **历史时间线**：规格版本、轮次、模型状态和接受结果。
7. **Skills 展厅**：关键词、标签、卡片列表和详情抽屉。

### 13.2 必须显示的来源与状态

- 当前任务 ID、分支来源和任务状态。
- 当前轮次绑定的规格版本，查看历史时不得显示成最新规格。
- 每条要求的来源、确认状态和重要性。
- 诊断是 AI 原始结果还是用户纠正后的有效结果。
- 模型调用中、失败、可重试和最终失败状态。
- 补丁基准、差异和完整可复制结果。
- Skill 来源、提交版本、许可证与是否完整包。

### 13.3 轮询与恢复

- 创建异步任务后每 1 至 2 秒轮询一次，完成或失败即停止。
- 刷新页面后根据诊断 ID 恢复轮询，不重新提交 POST。
- 提交按钮在请求进行中禁用，并使用幂等键防止双击重复创建。
- 关闭页面不会取消服务器调用；重新打开任务后可继续查看状态。

## 14. 隐私、安全与删除

### 14.1 外部调用授权

授权弹窗至少展示：

- 供应商与模型。
- 将发送的数据类型：图片、提示词、参数、规格或参考图。
- 调用目的：规格分析、图片诊断或补丁生成。
- 已知的数据保留、训练使用和远程删除政策。
- 本地删除不等于第三方同步删除。

授权范围哈希由供应商、模型、用途、数据类型和政策版本生成。任一项变化都要求重新授权。

### 14.2 日志最小化

- 应用日志不记录 API Key、图片二进制、完整授权令牌或图片绝对路径。
- `model_calls` 保存请求哈希、图片哈希、模型、耗时、用量和错误，不保存 Base64。
- 是否保存完整 Prompt 和原始模型响应由本地隐私选项控制；若保存，必须随任务删除。
- `.env`、`runtime/` 和第三方本地正文继续保持在 Git 忽略范围内。

### 14.3 删除流程

1. 查询任务关联的所有数据库记录和文件路径，并创建独立的 `deletion_jobs` 记录。
2. 校验路径均位于 `runtime/tasks/<task_id>`。
3. 将任务目录原子移动到 `runtime/trash/<deletion_job_id>`；移动失败时不改数据库。
4. 在事务内删除任务及级联结构化数据；事务失败时尝试将目录移回原位。
5. 删除隔离目录和相关临时文件，并更新删除任务状态。
6. 生成删除报告：本地数据库、原图、脱敏图、缓存、调用日志和第三方状态。
7. 若隔离目录删除失败，返回部分失败并通过 `deletion_jobs` 保留可重试记录，不宣称完全删除。

## 15. 候选配置默认值

以下值用于开始开发和编写测试，产品与供应商评审后再冻结；真实供应商限制更严格时取更严格值。

| 配置 | 候选值 |
| --- | --- |
| `SUPPORTED_IMAGE_FORMATS` | PNG、JPEG、WebP |
| `MAX_IMAGE_BYTES` | 10 MiB |
| `MAX_IMAGE_PIXELS` | 40,000,000 |
| `MAX_IMAGES_PER_ROUND` | 8 |
| `MAX_IMAGES_PER_TASK` | 50 |
| `TASK_STORAGE_LIMIT_MB` | 500 |
| `MODEL_TIMEOUT_SECONDS` | 90 |
| `MODEL_MAX_RETRIES` | 2 |
| `MODEL_JSON_REPAIR_ATTEMPTS` | 1 |
| `EXPERIMENT_MAX_ROUNDS` | 6 |
| `DIAGNOSIS_POLL_INTERVAL_SECONDS` | 1.5 |

新增依赖仅建议：

- `Pillow`：可靠解码图片、读取尺寸和生成无 EXIF 副本。
- `python-multipart`：FastAPI 文件上传。

不新增 SQLAlchemy、Alembic、任务队列、前端框架或第二套向量数据库。

## 16. 建议代码结构

```text
src/
├─ __init__.py                 # Python 包标记
├─ api_app.py                  # FastAPI 入口，只挂载 IteraCanvas 路由和静态页面
├─ iteracanvas_config.py       # 环境变量、阈值和运行时路径
├─ iteracanvas_routes.py       # /api/v1 路由
├─ iteracanvas_models.py       # 请求、响应与 AI Pydantic 模型
├─ iteracanvas_db.py           # SQLite 初始化、迁移和事务
├─ iteracanvas_services.py     # 状态转换与业务用例
├─ iteracanvas_files.py        # 图片验证、哈希、脱敏和删除
├─ ai_gateway.py               # mock/real 调用、重试和校验
├─ ai_prompts.py               # 版本化 Prompt
├─ skills_catalog.py           # 清单校验、发布和搜索
├─ experiment_export.py        # 当前产品实验事件导出
└─ iteracanvas.html            # 单页静态工作区

tests/
├─ test_core_flow.py           # 一条完整闭环集成测试
├─ test_acceptance_cases.py    # 产品规格 AC-* 用例
└─ fixtures/
   ├─ ai_spec_result.json
   ├─ ai_diagnosis_result.json
   └─ ai_patch_result.json

runtime/                       # 运行时数据，不提交 Git
```

### 16.1 重写前删除清单

以下文件只服务旧项目，重写前全部删除，包括已被 Git 跟踪的文件：

```text
src/build_kb.py
src/build_vector_store.py
src/compare.py
src/config.py
src/deepseek_rag_homepage_prototype.html
src/embedder.py
src/export_jimeng_prompt_kb.py
src/llm.py
src/loaders.py
src/prompt_builder.py
src/prompt_optimizer.py
src/rag_pipeline.py
src/retriever.py
src/schemas.py
src/splitter.py
src/ui.py
src/vectordb.py
src/web_app.py
```

保留 `src/__init__.py`。保留 `src/api_app.py` 这一入口路径，但删除其旧内容后按本章职责重写。删除完成后，`src/` 不得再导入旧 RAG 模块。

## 17. 实施过程

### 阶段 0：冻结可编码规则

工作：

1. 按第 16.1 节删除旧 `src` 文件，并移除只服务旧代码的依赖。
2. 确认删除后仅保留 `src/__init__.py` 和待重写的 `src/api_app.py`。
3. 确认生成轮次、上传提交和候选图定义。
4. 确认规格版本不可变规则及分支触发方式。
5. 确认 Skills 展厅是独立次级入口。
6. 将第 15 章阈值标记为“接受”或替换为正式值。

退出条件：旧代码与旧依赖清理完成；形成一页决策记录；未确认项明确负责人和截止点。此阶段不需要等待模型供应商确定。

### 阶段 1：建立持久化骨架

工作：

1. 新增运行时配置、SQLite 初始化和迁移版本。
2. 建立任务、规格版本、轮次、提交、候选图、诊断、复核、补丁、授权和调用表。
3. 实现文件上传、真实格式验证、哈希、去除 EXIF 和安全删除。
4. 实现领域状态转换和统一错误模型。
5. 为副作用接口加入幂等键。

退出条件：不调用 AI，也能完成创建任务、保存并确认规格、创建轮次、分批上传、重复识别和删除任务。

### 阶段 2：用模拟 AI 跑通纵向闭环

工作：

1. 建立三组 Pydantic AI 输出模型和固定 JSON 夹具。
2. 实现规格提取、诊断和补丁的模拟调用。
3. 实现后台任务状态与前端轮询接口。
4. 实现用户复核和有效结论计算。
5. 实现基于 `criterion_id` 的轮次比较。

退出条件：一条自动化集成测试能够完成：

```text
任务 → 规格 v1 → 轮次 1 → 上传 → 模拟诊断
→ 用户纠正 → 生成补丁 → 轮次 2 → 比较 → 接受结果
```

### 阶段 3：完成 Demo 页面

工作：

1. 新建 `iteracanvas.html`，并由 FastAPI 根路径提供新产品入口。
2. 完成任务、规格、轮次、诊断、补丁和历史页面状态。
3. 显示规格版本、内容来源、授权状态和模型任务状态。
4. 实现刷新恢复、重复提交保护和复制完整结果。
5. 完成分支与本地删除交互。

退出条件：非开发人员只通过页面即可完成阶段 2 的完整闭环，刷新浏览器不会重复创建轮次或模型调用。

### 阶段 4：接入一个真实多模态供应商

工作：

1. 完成供应商的数据保留、训练使用、删除能力和图片限制登记。
2. 实现授权弹窗和授权范围校验。
3. 实现真实请求、超时、有限重试、结构修复和用量记录。
4. 建立不少于 12 个固定案例的 Prompt 回归集。
5. 对比模拟模式与真实模式的状态行为一致性。

退出条件：真实模式能够稳定返回结构化诊断；异常情况下不丢失历史、不产生半成品、不发生未授权调用。

### 阶段 5：交付 Skills 展厅

工作：

1. 为 manifest 增加展示元数据和 `gallery_status`。
2. 实现清单校验与发布 CLI。
3. 对许可允许的完整条目补齐引用资源和署名信息。
4. 实现只读列表、普通搜索、标签筛选、详情和复制。
5. 对限制或禁止再分发条目执行隐藏或仅显示元数据策略。

退出条件：展厅不会返回未发布、无授权或禁止再分发的正文；8 个候选条目的状态均有明确解释。

### 阶段 6：开展预实验

工作：

1. 实现实验事件导出和指标计算脚本。
2. 使用固定案例完成一轮预实验。
3. 根据预实验冻结最大轮次、候选图数量、预算和计时方法。

退出条件：实验数据能够区分人工流程与诊断助手流程；同一案例可以复现，异常数据处理规则明确。

## 18. 测试策略

### 18.1 测试层级

| 层级 | 覆盖重点 | 执行方式 |
| --- | --- | --- |
| 领域单元测试 | 状态转换、规格不可变、有效诊断、参数补丁和删除路径校验 | 纯 Python，临时 SQLite |
| API 集成测试 | 状态码、事务、幂等、上传、轮询和级联删除 | FastAPI TestClient + 临时目录 |
| AI 契约测试 | mock 与 real 返回相同结构、未知 ID 拒绝、JSON 修复 | 固定 JSON 夹具 |
| 页面冒烟测试 | 主闭环、刷新恢复、复制、错误提示 | 浏览器手工或最少自动化脚本 |
| 供应商冒烟测试 | 一张小图成功、超时、限流和授权拦截 | 手工触发，控制调用成本 |

### 18.2 产品验收映射

| 产品用例 | 工程测试 |
| --- | --- |
| `AC-IMG-01` | 有效 PNG/JPEG/WebP；伪扩展名；超字节、超像素和损坏文件 |
| `AC-RND-01` | 一轮多图、两次提交、同轮重复、跨轮相同文件、归属纠正 |
| `AC-API-01` | 超时、429、500、无效 JSON、重试耗尽和进程中断恢复 |
| `AC-AUTH-01` | 未授权、授权匹配、范围变化、撤回和重新授权 |
| `AC-SPEC-01` | v1 诊断后创建 v2，查看 v1 仍使用原规格 |
| `AC-BRANCH-01` | 分支继承指定快照，父任务保持不变 |
| `AC-DIAG-01` | 确认、纠正、不适用、无法判断和撤销纠正 |
| `AC-PATCH-01` | 单补丁、多补丁、参数删除、冲突和基准缺失 |
| `AC-DEL-01` | 数据库、原图、脱敏图、临时文件和调用记录删除报告 |
| `AC-RECOVER-01` | 双击、刷新、重复幂等键和服务重启后的任务状态 |

### 18.3 AI 质量评估

结构正确不代表诊断正确。固定案例集至少覆盖人物、场景、商品海报、含文字图片和参考图对齐，并记录：

- 结构化输出一次通过率。
- 已确认硬约束的诊断一致率。
- AI 虚构用户要求的次数，目标应为 0。
- 证据是否能在图片中被人工定位。
- 用户纠正率和主要纠正类型。
- 补丁是否覆盖所选问题。
- 补丁是否错误修改未选中的正确部分。
- 合并后提示词与参数是否可直接复制。

正式实验前由同一套人工标注规则评审模型输出。模型或 Prompt 版本变化后重新跑固定集，不能只挑成功案例。

## 19. 对比实验实现

### 19.1 实验事件

为每个实验任务记录：

- 组别、参与者匿名 ID、案例 ID 和流程顺序。
- 外部平台、模型版本、初始提示词和参数。
- 每次外部生成请求的轮次编号和候选图数量。
- 每次人工操作和模型调用的开始、结束时间。
- 建议是否采用、硬约束通过情况、用户接受和退出原因。
- 模型调用用量、估算成本、失败和重试次数。

### 19.2 指标计算

- 主指标：达到预先定义验收门槛所需的外部生成请求数。
- 同时报告用户主动接受和硬约束达标，不能合并成一个不透明指标。
- 达到最大轮次仍未完成的任务记录为截尾或失败，不从样本中删除。
- 每轮候选图数量固定，否则额外候选图会提高偶然命中概率。
- 人工与辅助流程顺序随机化或平衡，避免学习效应。
- Prompt 版本和模型版本必须进入实验记录。

### 19.3 导出

提供一个只读导出命令：

```powershell
python -m src.experiment_export --format json --out outputs/experiment_results/run.json
```

导出使用数据库快照计算，不依赖页面内存状态。正式分析脚本只读取导出文件，不直接修改业务数据库。

## 20. 本地部署与运维

### 20.1 启动

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn src.api_app:app --host 127.0.0.1 --port 8010
```

启动时执行：

1. 检查并创建 `runtime/` 目录。
2. 执行 SQLite 小版本迁移。
3. 校验 Skills manifest，但不因不可发布条目阻止主应用启动。
4. 把遗留的 `queued/running` AI 任务标记为中断失败。
5. 输出模型模式、数据库路径和已发布 Skill 数量，不输出密钥。

### 20.2 健康检查

新增 `GET /api/v1/health`，返回：

- 应用版本和数据库 schema 版本。
- SQLite 是否可读写。
- 运行时目录是否可写。
- `AI_MODE` 和是否配置真实模型密钥。
- Skills 清单是否有效及已发布数量。

健康检查不主动调用收费模型。

### 20.3 备份与恢复

- Demo 备份单位为 SQLite 文件和整个 `runtime/tasks` 目录。
- 备份前使用 SQLite backup API 获取一致快照，不直接复制正在写入的数据库文件。
- 恢复必须同时恢复数据库与任务文件；二者版本不一致时进入只读修复提示。

## 21. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 产品 P0 决策继续变化 | 数据结构返工 | 先做模拟纵向闭环，正式供应商和实验后置 |
| 模型不稳定输出 JSON | 诊断失败或字段污染 | 严格模型、一次结构修复、失败不落半成品 |
| 多图成本和耗时过高 | Demo 不可控 | 每图独立诊断、限制每轮数量、记录成本 |
| 本地文件与数据库不一致 | 数据丢失或无法删除 | 临时文件、事务补偿、路径校验、删除报告 |
| 把 AI 推断当成用户要求 | 错误诊断 | 来源与状态双字段，硬约束只接受确认项 |
| 旧代码残留造成错误复用 | 新实现继续依赖旧领域模型 | 阶段 0 删除旧文件、旧依赖和旧接口，并检查无残留导入 |
| Skill 许可证不允许再分发 | 法务和发布风险 | 许可证状态与发布状态分离，阻断项不可强制绕过 |
| BackgroundTasks 在重启时中断 | 任务未完成 | 启动时标记失败并允许重试；多用户阶段再上持久队列 |
| SQLite 并发上限 | 扩展受限 | 当前单用户足够；出现真实并发再迁移数据库 |

## 22. 完成定义

Demo 只有在以下条件全部满足时才算工程完成：

1. `src/` 不再包含或导入第 16.1 节列出的旧项目代码。
2. 应用只暴露 IteraCanvas 页面和 `/api/v1` 接口。
3. 用户能通过 Web 完成一条两轮以上的图片诊断迭代。
4. 每个历史结果都能追溯到准确的规格版本、图片和模型调用。
5. AI 推断、用户确认和用户纠正能被清楚区分。
6. 一轮多图、分批上传和重复上传不会错误增加生成轮次。
7. 页面能同时提供差异和完整可复制提示词、参数。
8. 未授权时没有外部调用；删除任务时产生可信的本地删除报告。
9. Skills 展厅不会展示许可证禁止或尚未发布的完整正文。
10. 产品规格中的 10 个最低验收场景全部有自动化或可复现测试记录。
11. 固定 AI 案例集完成回归，Prompt 和模型版本均可追踪。
12. 对比实验可以导出轮次、耗时、成本和硬约束结果。
13. README 包含安装、配置、启动、备份、恢复和隐私边界说明。

## 23. 推荐的下一步

按最短路径执行：

1. 产品确认第 4 章暂定假设和第 15 章阈值。
2. 先实现阶段 1 的 SQLite、文件存储和状态规则。
3. 立即建立阶段 2 的单条完整集成测试和三个模拟 AI 夹具。
4. 只有模拟闭环稳定后才开发完整页面和购买真实模型调用。
5. 真实诊断通过固定案例回归后，再做 Skills 展厅和对比实验。

这一顺序优先验证产品最核心的不确定性：系统是否能保存正确的迭代历史，并输出用户愿意采用的诊断和补丁。其余扩展能力均不应阻塞该闭环。
