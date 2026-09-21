# 8 个图片 Skills 本地验证报告

- 验证日期：2026-09-20
- 验证范围：`data/skills-showcase/manifest.json` 中的 8 个正文快照
- 生成方式：Codex 内置图片生成能力；每个 Skill 独立调用一次
- 测试输入：因用户未提供源照片，照片驱动型 Skill 使用合成测试场景；因此只验证核心视觉语言，不能据此声称真实源图保真链路通过

## 总结

- `SKILL.md` 存在且 SHA-256 与 manifest 一致：8/8
- 可生成具有对应核心视觉语言的样图：8/8
- 完整可安装、可严格执行的 Skill 包：0/8
- 可直接公开发布：仍须服从 manifest 的许可证状态；本次生成不改变授权结论

“可生成样图”与“完整可用 Skill 包”是两个不同结论。当前目录由 README 明确标记为 `content_only`，多数条目缺少正文要求的 `references/`、`scripts/` 或 `assets/`。

## 逐项结果

| # | Skill | 核心视觉生成 | 严格契约结论 | 主要观察 | 依赖/授权结论 |
|---|---|---|---|---|---|
| 1 | `heytea-doodle-poster` | 通过 | 条件通过 | 实拍感柠檬汽水瓶、4 个黑线微型工人、留白与无文字均符合测试约束 | 14 个显式引用均缺失；manifest 为 `ready_with_license_notice`，补齐依赖前仍不是完整包 |
| 2 | `scenes-gathered-zine-v1-3` | 通过 | 条件通过 | 3:5 竖版、真实照片锚点、明显纤维撕纸边、单一红色结构与微文字均出现 | 无显式文件引用缺失；真实用户照片保真未验证；manifest 为 `restricted_review` |
| 3 | `tait-crt-interface-skill` | 通过 | 未完全通过 | 4:3、限制色板、CRT 扫描线、桶形边缘和固定签名均出现；前景应用窗数量/提取窗结构没有完全满足严格蓝图 | 5 个显式引用缺失，且缺 `finalize_crt.py` 路径；manifest 为 `blocked_no_license` |
| 4 | `photo-abstract-editorial` | 通过 | 条件通过 | 上方照片、下方象牙白抽象关系面板和英文标题清楚；没有框、胶带或拼贴阴影 | 3 个显式引用缺失；真实输入照片的“不改动”约束未验证；manifest 为 `restricted_review` |
| 5 | `yarn-rug-reference` | 通过 | 部分通过 | 上下对照、构图保持、低色块和毛绒纤维效果成立 | 输出为 1024×1536，比例正确但未达到正文规定的精确 1080×1620；manifest 为 `ready_with_license_notice` |
| 6 | `travel-memory-sticker-card` | 通过 | 条件通过 | 3:2 横卡、左侧主图、右侧恰好 6 枚贴纸、3 个关键词均出现 | 1 个显式引用缺失；真实源图锚点未验证；manifest 为 `blocked_redistribution` |
| 7 | `gc-minimal-zine-poster-v0-3` | 通过 | 条件通过 | 大留白、旧纸、种子/雨滴单一视觉事件、钴蓝强调、指定标题与页码均出现 | 5 个显式引用缺失；manifest 为 `ready_with_license_notice`，补齐依赖前仍不是完整包 |
| 8 | `ip-illustration-for-yourself` / `ip-illustration-character-system` | 通过 | 条件通过 | PIP 主视图与 3 个辅助视图保持围巾、挎包和配色一致 | 13 个显式引用缺失；展厅 ID 与 frontmatter 名称不同但 manifest 已备注；manifest 为 `blocked_no_license` |

## 样图文件

| 文件 | 尺寸 | SHA-256 |
|---|---:|---|
| `01-heytea-doodle-poster.png` | 1024×1536 | `6d8d5c36937384081fb93305771b2f9dbe0e96659ec694301ab5834e616abaea` |
| `02-scenes-gathered-zine-v1-3.png` | 971×1619 | `09ccf9016b681728961658d4d3bd80f56d66660dbba1fb2547487e3d8cec26f0` |
| `03-tait-crt-interface-skill.png` | 1448×1086 | `38ce38f1dd1e1c8c3035b08bda973d1a270efb8300021168290dc2655a197102` |
| `04-photo-abstract-editorial.png` | 1024×1536 | `8ce6cee4232b2cf9ae7ed9aff2e262cfebb1cfb3334bfb03b6d1d0d87f95c251` |
| `05-yarn-rug-reference.png` | 1024×1536 | `a5546c4f1a246bcef60c19caee5aa7164f2e2b23c2d497ddfa4e12ec528fbefb` |
| `06-travel-memory-sticker-card.png` | 1536×1024 | `8581bc4853c4265c530d29095c73f2d9a3c44a1fbf4fb2b5b6db9d3be1c51aaf` |
| `07-gc-minimal-zine-poster-v0-3.png` | 1024×1536 | `71e5d42a8784eac76a2fe2cd58347b99ac8d1fe1654b05c93f9a34f4be27e9d4` |
| `08-ip-illustration-for-yourself.png` | 1254×1254 | `4515df63572d147fbfcd7a464d38af857ac8dfdddc232563cd9beb3015ecf5a1` |

## 本次提示词摘要

1. 无文字柠檬汽水实物海报，4 个黑线微型工人，保持瓶体写实。
2. 山湖照片锚点、撕纸纤维边、红色独木舟延伸成单一结构色的 3:5 Zine。
3. 4:3 夜班无线电操作员 CRT 界面，四色限制色板、共享像素网格、桶形畸变与固定签名。
4. 红椅、蓝窗、斜影的照片/象牙白抽象关系双联画，标题 `A Chair Waiting`。
5. 红木屋、山丘与小路的上下对照，底图转为 7 色簇绒毛线地毯。
6. 海边电车黄昏旅行卡，左侧主图、右侧 6 枚贴纸、3 个英文关键词。
7. “种子记得雨”的极简旧纸海报，单一钴蓝雨滴窗口与标题 `MEMORY OF RAIN`。
8. 奶油色水獭 PIP 的角色锚点页，黄围巾、青绿挎包、主视图加三辅助视图。

## 建议

若下一步要把这些条目从“展厅正文快照”升级为可执行 Skill，优先级应为：补齐全部必读引用与脚本 → 建立真实源图回归集 → 对计数、文字、尺寸和保真做自动化检查 → 完成许可证复核 → 再开放安装或发布入口。
