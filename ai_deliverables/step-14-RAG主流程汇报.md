# Step 14 RAG 主流程汇报

## 本步目标

串联 embedding、向量库、检索、Prompt 构造和 DeepSeek 调用，形成完整的端到端 RAG 主流程。

## 实际完成内容

1. 在 `src/rag_pipeline.py` 中实现了 `ensure_knowledge_base()`：
   - 首次调用时自动检查本地向量库是否为空
   - 若为空，则自动执行文档加载、切分、向量化与索引写入
2. 实现了 `answer_question()`：
   - 检查问题输入
   - 确保知识库已准备好
   - 执行 top-k 检索
   - 构造 Prompt
   - 调用 DeepSeek 生成答案
   - 回填来源文档列表
3. 为“无检索结果”场景增加了兜底响应：
   - `根据现有资料无法回答`
4. 将主流程对外收敛为单一入口，方便后续 CLI 和对比实验模块复用。

## 产出文件

- `D:\test\deployment-model-v2\src\rag_pipeline.py`

## 当前未完成项

- 尚未与 CLI 界面联动
- 尚未在真实 DeepSeek API Key 条件下做完整端到端联调
- 尚未加入知识库强制重建、增量更新等管理能力

## 验收结果

- RAG 核心链路已在代码层串联完成
- 后续 `S15` 可直接接入 CLI

## 下一步计划

执行 `S15`，实现可连续提问的命令行交互界面。

