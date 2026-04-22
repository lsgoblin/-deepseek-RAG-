# Step 04 配置模块实现汇报

## 本步目标

实现 `src/config.py`，统一管理默认配置、环境变量读取和路径解析。

## 实际完成内容

1. 重写 `src/config.py`，不再使用占位说明。
2. 定义了不可变配置对象 `Settings`。
3. 支持从项目根目录的 `.env` 文件读取配置。
4. 支持环境变量覆盖 `.env` 中的同名配置。
5. 定义并收口了核心默认值：
   - `DEEPSEEK_BASE_URL`
   - `EMBEDDING_MODEL`
   - `VECTOR_DB_TYPE`
   - `VECTOR_DB_DIR`
   - `TOP_K`
   - `CHUNK_SIZE`
   - `CHUNK_OVERLAP`
   - `TEMPERATURE`
   - `MAX_DOCS`
6. 使用 `pathlib.Path` 统一处理项目路径、数据目录、输出目录和向量库目录。
7. 提供 `get_settings()` 作为全项目统一配置入口。

## 产出文件

- `D:\test\deployment-model-v2\src\config.py`

## 当前未完成项

- 还没有创建实际 `.env` 文件
- 还没有与后续业务模块联调
- 尚未增加配置合法性校验和更详细的错误提示

## 验收结果

- 配置模块已具备独立导入条件
- 已具备读取默认配置和环境变量的能力
- API Key 没有硬编码在源码中

## 下一步计划

执行 `S05`，定义公共数据结构和各模块接口签名，形成稳定接口层。

