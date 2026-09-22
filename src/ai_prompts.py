"""Versioned prompts shared by the mock gateway and future provider."""

SPEC_PROMPT_VERSION = "spec_extract.v1"
DIAGNOSIS_PROMPT_VERSION = "image_diagnosis.v1"
PATCH_PROMPT_VERSION = "patch_generation.v1"

SPEC_EXTRACT_PROMPT = "从用户描述和参考图中提取可验证创作规格；不要把 AI 推断写成用户要求。"
IMAGE_DIAGNOSIS_PROMPT = "逐条检查创作规格，返回 verdict、证据、严重程度、置信度和可能原因。"
PATCH_GENERATION_PROMPT = "只针对用户选择的问题生成补丁，并保留已经正确的部分。"
