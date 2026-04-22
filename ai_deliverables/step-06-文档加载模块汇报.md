# Step 06 文档加载模块汇报

## 本步目标

实现文档加载模块，支持 `txt`、`md`、`pdf`、`docx` 的统一纯文本提取，并保证单个文件失败不拖垮整体流程。

## 实际完成内容

1. 在 `src/loaders.py` 中实现了文档发现函数 `discover_documents()`。
2. 实现了单文件加载函数 `load_document()`。
3. 实现了批量加载函数 `load_documents()`。
4. 支持的文件类型：
   - `.txt`
   - `.md`
   - `.pdf`
   - `.docx`
5. 为文本文件增加了多编码读取兜底：
   - `utf-8`
   - `utf-8-sig`
   - `gb18030`
6. 为 `pdf` 和 `docx` 增加了运行时依赖检查，缺少依赖时给出明确报错信息。
7. 批量加载时采用“单文件失败跳过并记录 warning”的策略，满足主流程稳定性要求。
8. 为每个文档生成稳定的 `doc_id`，统一映射为 `SourceDocument` 数据结构。

## 产出文件

- `D:\test\deployment-model-v2\src\loaders.py`

## 当前未完成项

- 还没有在真实课程文档样本上做批量验证
- PDF 和 DOCX 的提取质量尚未针对复杂版式做专项处理
- 尚未接入 `unstructured` 扩展格式支持

## 验收结果

- 已具备统一文档发现与加载能力
- 已具备异常文件隔离能力
- 输出对象已统一到 `SourceDocument`

## 下一步计划

执行 `S07`，实现文本切分模块，将长文档转为保留来源信息的 chunk 列表。

