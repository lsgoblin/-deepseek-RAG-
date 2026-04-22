# Step 11 检索模块汇报

## 本步目标

实现检索模块，完成用户问题向量化和 top-k 相似片段召回。

## 实际完成内容

1. 在 `src/retriever.py` 中实现了 `retrieve_top_k()`。
2. 将检索流程收敛为两步：
   - 使用 `embed_query()` 生成问题向量
   - 使用 `search_similar()` 从向量库中召回结果
3. 检索输出统一为 `RetrievedChunk` 列表，便于后续 Prompt 构造和来源展示。

## 产出文件

- `D:\test\deployment-model-v2\src\retriever.py`

## 当前未完成项

- 尚未加入 rerank
- 尚未加入 BM25 混合检索
- 尚未加入检索结果过滤和阈值裁剪

## 验收结果

- 检索编排接口已形成
- 已与 embedding 模块和向量库模块打通接口

## 下一步计划

执行 `S12`，实现统一 Prompt 构造模块。

