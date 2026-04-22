# Step 13 DeepSeek 调用模块汇报

## 本步目标

实现 DeepSeek API 调用模块，完成请求发送、异常处理和响应解析。

## 实际完成内容

1. 在 `src/llm.py` 中实现了 `generate_answer()`。
2. 通过 `src/config.py` 统一读取：
   - `DEEPSEEK_API_KEY`
   - `DEEPSEEK_BASE_URL`
   - `DEEPSEEK_MODEL`
   - `TEMPERATURE`
3. 使用 `requests` 调用 DeepSeek 兼容的 `chat/completions` 接口。
4. 实现了响应解析函数 `_extract_message_content()`。
5. 增加了以下错误处理：
   - Prompt 为空
   - API Key 缺失
   - HTTP 请求失败
   - 响应结构缺失
   - 返回答案为空
6. 将最终结果统一映射为 `LLMAnswer`。

## 产出文件

- `D:\test\deployment-model-v2\src\llm.py`
- `D:\test\deployment-model-v2\.env.example`
- `D:\test\deployment-model-v2\src\config.py`

## 当前未完成项

- 尚未做真实 API 联调
- 尚未增加重试机制
- 尚未输出 token 用量、耗时等统计信息

## 验收结果

- 已具备标准化 DeepSeek 调用能力
- 已具备失败时的明确报错路径

## 下一步计划

执行 `S14`，串联完整 RAG 主流程。

