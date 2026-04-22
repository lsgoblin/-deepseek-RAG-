# Step 07 文本切分模块汇报

## 本步目标

实现文本切分模块，按 `chunk_size` 和 `chunk_overlap` 将文档内容切分为后续向量化可用的文本块。

## 实际完成内容

1. 在 `src/splitter.py` 中实现了单文档切分函数 `split_document()`。
2. 实现了批量切分函数 `split_documents()`。
3. 当前采用字符级滑动窗口切分策略。
4. 为切分参数增加了基础校验：
   - `chunk_size > 0`
   - `chunk_overlap >= 0`
   - `chunk_overlap < chunk_size`
5. 空文本文档会安全返回空列表，不会报错。
6. 每个切分结果统一映射为 `TextChunk`：
   - `chunk_id`
   - `source_doc`
   - `chunk_text`
   - `chunk_index`
   - `metadata`
7. `metadata` 中保留了：
   - `doc_id`
   - `source_path`
   - `file_type`

## 产出文件

- `D:\test\deployment-model-v2\src\splitter.py`

## 当前未完成项

- 还没有做基于句子或段落边界的更细致切分
- 还没有加入针对 Prompt 长度的更智能裁剪策略
- 暂未加入 chunk 质量评估或去重策略

## 验收结果

- 已具备稳定 chunk 生成能力
- 已保留来源追踪信息
- 已满足后续 embedding 模块的基础输入要求

## 下一步计划

执行 `S08`，实现最小知识库构建入口，串联文档加载与文本切分并输出中间结果摘要。

