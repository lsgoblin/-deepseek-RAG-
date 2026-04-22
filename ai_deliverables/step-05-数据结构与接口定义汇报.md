# Step 05 数据结构与接口定义汇报

## 本步目标

定义项目核心数据结构和模块接口签名，为后续各功能模块实现提供稳定边界。

## 实际完成内容

1. 新增 `src/schemas.py`，定义公共数据结构：
   - `SourceDocument`
   - `TextChunk`
   - `RetrievedChunk`
   - `LLMAnswer`
2. 将以下模块从“纯占位说明”升级为“带签名的接口骨架”：
   - `loaders.py`
   - `splitter.py`
   - `embedder.py`
   - `vectordb.py`
   - `retriever.py`
   - `prompt_builder.py`
   - `llm.py`
   - `rag_pipeline.py`
   - `compare.py`
   - `build_kb.py`
   - `ui.py`
3. 为核心函数补充了 docstring。
4. 当前所有接口均保持“可导入、未实现”的状态，使用 `NotImplementedError` 明确后续实现阶段。

## 产出文件

- `D:\test\deployment-model-v2\src\schemas.py`
- `D:\test\deployment-model-v2\src\loaders.py`
- `D:\test\deployment-model-v2\src\splitter.py`
- `D:\test\deployment-model-v2\src\embedder.py`
- `D:\test\deployment-model-v2\src\vectordb.py`
- `D:\test\deployment-model-v2\src\retriever.py`
- `D:\test\deployment-model-v2\src\prompt_builder.py`
- `D:\test\deployment-model-v2\src\llm.py`
- `D:\test\deployment-model-v2\src\rag_pipeline.py`
- `D:\test\deployment-model-v2\src\compare.py`
- `D:\test\deployment-model-v2\src\build_kb.py`
- `D:\test\deployment-model-v2\src\ui.py`

## 当前未完成项

- 文档加载逻辑尚未实现
- 文本切分逻辑尚未实现
- 向量化、向量库、检索、DeepSeek 调用均尚未实现
- CLI 和对比实验还只有接口骨架

## 验收结果

- 核心对象和函数签名已明确
- 模块边界已形成
- 后续步骤可在当前接口层上逐个补实现

## 下一步计划

执行 `S06`，实现文档加载模块，优先支持 `txt`、`md`、`pdf`、`docx` 四类文件的统一纯文本提取。

