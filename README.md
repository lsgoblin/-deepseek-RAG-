# deployment-model-v2

基于 DeepSeek 的 RAG 信息检索系统项目骨架。

## 当前状态

当前仓库已完成初始化，不包含业务实现代码。

已创建内容：

- 项目目录结构
- 依赖清单 `requirements.txt`
- 环境变量模板 `.env.example`
- 源码占位模块
- 输出与向量库存储目录

## 目录结构

```text
deployment-model-v2/
├─ data/
├─ notebooks/
├─ outputs/
│  ├─ experiment_results/
│  └─ screenshots/
├─ src/
│  ├─ __init__.py
│  ├─ build_kb.py
│  ├─ compare.py
│  ├─ config.py
│  ├─ embedder.py
│  ├─ llm.py
│  ├─ loaders.py
│  ├─ prompt_builder.py
│  ├─ rag_pipeline.py
│  ├─ retriever.py
│  ├─ splitter.py
│  ├─ ui.py
│  └─ vectordb.py
├─ vector_store/
├─ .env.example
├─ .gitignore
├─ README.md
├─ requirements.txt
└─ 项目计划.md
```

## 后续建议顺序

1. 完成 `src/config.py` 中的配置读取实现。
2. 实现文档加载与文本切分模块。
3. 接入 embedding、向量库、检索与 DeepSeek 调用。
4. 串联 CLI 和对比实验流程。

