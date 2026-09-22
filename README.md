# IteraCanvas（迭绘）

本项目是本地单用户图片诊断与迭代助手。当前已完成阶段 2 Mock AI 闭环：任务、不可变规格版本、生成轮次、图片上传、诊断轮询、用户复核、补丁生成、轮次比较、结果接受、分支和受控删除。

当前实现以以下文档为准：

- 产品需求：[`doc/IteraCanvas-产品需求规格-v0.4-20260921-192456.md`](doc/IteraCanvas-产品需求规格-v0.4-20260921-192456.md)
- 工程设计：[`doc/IteraCanvas-工程设计-v0.5.md`](doc/IteraCanvas-工程设计-v0.5.md)

## 安装

```powershell
python -m pip install -r requirements.txt
```

可选地设置运行目录：

```powershell
$env:ITERACANVAS_RUNTIME_DIR = "D:\iteracanvas-runtime"
```

阶段 2 默认使用 `AI_MODE=mock`；真实供应商在阶段 4 接入。

默认运行数据写入项目根目录的 `runtime/`，该目录不应提交到 Git。

## 启动

```powershell
uvicorn src.api_app:app --host 127.0.0.1 --port 8010
```

打开 `http://127.0.0.1:8010/` 可查看服务信息。阶段 1 以 API 验收为主，业务接口统一位于 `/api/v1`：

- `POST /api/v1/tasks`：创建任务
- `POST /api/v1/tasks/{id}/spec-versions`：保存规格草稿
- `POST /api/v1/tasks/{id}/spec-extractions`：获取 Mock AI 规格提取结果
- `POST /api/v1/spec-versions/{id}/confirm`：确认规格
- `POST /api/v1/tasks/{id}/rounds`：创建生成轮次
- `POST /api/v1/rounds/{id}/submissions`：分批上传 PNG、JPEG 或 WebP
- `POST /api/v1/candidates/{id}/diagnoses`：启动 Mock AI 诊断（返回 `202`）
- `GET /api/v1/diagnoses/{id}`：轮询诊断状态、AI 原始结果和有效结论
- `POST /api/v1/diagnoses/{id}/reviews`：追加确认、纠正、不适用、无法判断或撤回复核
- `POST /api/v1/rounds/{id}/patches`：根据有效诊断生成补丁
- `GET /api/v1/rounds/{id}/comparison`：按 `criterion_id` 比较相邻轮次
- `POST /api/v1/tasks/{id}/accept`：接受候选图并关闭任务
- `POST /api/v1/tasks/{id}/branches`：从已确认规格创建分支
- `DELETE /api/v1/tasks/{id}`：删除叶子任务并返回删除报告

副作用接口支持 `Idempotency-Key`。同一轮相同 SHA-256 图片返回 `409 DUPLICATE_CANDIDATE`；跨轮重复允许上传，但候选图会带 `cross_round_duplicate=true` 警告。

## 阶段边界

阶段 2 只使用确定性的 Mock AI，不提供旧 `/api/optimize`、`/api/status`、`/api/rebuild-kb` 接口，也不加载旧 RAG、向量库或 Skills 展厅。真实多模态供应商和页面属于后续阶段。

当前图片阈值：单文件 10 MiB、最大 40,000,000 像素、每轮 8 张、每任务 50 张、每任务本地存储 500 MB。

## 测试

```powershell
python -m pytest -q
```

阶段 1/2 测试覆盖规格确认、轮次创建、分批上传、同轮重复、跨轮重复、诊断轮询、用户复核、补丁、比较、接受、幂等和分支删除顺序。

## 数据与隐私

SQLite 数据库位于 `runtime/iteracanvas.db`；原图和去 EXIF 副本位于 `runtime/tasks/<task_id>/`。应用不在阶段 1 调用第三方模型。删除父任务前必须先删除所有子分支；删除报告只描述本地数据，不暗示第三方删除。

备份时停止服务后复制整个 `runtime/` 目录；恢复时将目录放回 `ITERACANVAS_RUNTIME_DIR` 指向的位置即可。
