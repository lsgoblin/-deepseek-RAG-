# Prompt Optimization Comparison Results

This report compares `LLM-only`, `Retrieval-only`, and `RAG` modes for the same inputs.

## Case 1: 人物类提示词优化

- Raw prompt: 赛博朋克女战士站在雨夜街头
- Platform: 即梦
- Style: 电影感，霓虹，高细节
- Goal: 增强人物造型、场景氛围和镜头语言

### llm_only

- Status: success
- Optimized prompt: 赛博朋克女战士，湿漉漉的雨夜街头，霓虹灯光倒映在积水路面，她身穿高领战术风衣，金属义肢手臂，发梢滴落雨水，眼神冷峻，背景是霓虹招牌和摩天楼，电影感构图，浅景深，高细节，暗调氛围，侧逆光勾勒轮廓
- Notes:
  - 补充了人物造型细节：高领战术风衣、金属义肢手臂、发梢滴落雨水、眼神冷峻
  - 强化了场景氛围：湿漉漉的雨夜、霓虹灯光倒映积水、霓虹招牌和摩天楼背景
  - 增加了镜头语言：电影感构图、浅景深、侧逆光勾勒轮廓、暗调氛围

### retrieval_only

- Status: success
- Retrieval query: `原始提示词：赛博朋克女战士站在雨夜街头
目标平台：即梦
风格偏好：电影感，霓虹，高细节
优化目标：增强人物造型、场景氛围和镜头语言`
- Notes:
  - 共检索到 3 个相关片段。
  - 该模式只展示可追溯的知识片段，不生成最终优化提示词。
- Sources: jimeng_prompt_knowledge_base.md
- Top chunk source: jimeng_prompt_knowledge_base.md
- Top chunk preview: Sheet1 - 风格与艺术表现: 赛博朋克风格 - 镜头与构图: 反射镜头 - 人物与服饰: 穿厚重羽绒服的滑雪者 - 场景与背景: 冬季的滑雪度假村 - 细节与服饰: 灯光下的影子效果 - 色调与光效: 阴暗的光影效果 - 文化与环境: 日式庭院 - combined_prompt: 赛博朋克风格，反射镜头，穿厚重羽绒服的滑雪者，冬季的滑雪度假村，灯光下...

### rag

- Status: success
- Optimized prompt: 赛博朋克风格，反射镜头，霓虹纹身的光纤女战士，雨夜街头，灯光下的影子效果，阴暗的光影效果，熔岩玻璃气泡，青瓷釉色的冷调反光，伦敦的街头景象
- Retrieval query: `原始提示词：赛博朋克女战士站在雨夜街头
目标平台：即梦
风格偏好：电影感，霓虹，高细节
优化目标：增强人物造型、场景氛围和镜头语言`
- Notes:
  - 补充了风格与艺术表现：明确为赛博朋克风格，增强电影感
  - 补充了镜头与构图：使用反射镜头，增强视觉层次和霓虹氛围
  - 补充了人物与服饰：将女战士细化为霓虹纹身的光纤女战士，提升高细节和霓虹元素
  - 补充了场景与背景：保留雨夜街头，并加入伦敦的街头景象，增强场景氛围
  - 补充了细节与服饰：加入灯光下的影子效果和熔岩玻璃气泡，增加高细节
  - 补充了色调与光效：使用阴暗的光影效果和青瓷釉色的冷调反光，强化霓虹和电影感
- Sources: jimeng_prompt_knowledge_base.md
- Top chunk source: jimeng_prompt_knowledge_base.md
- Top chunk preview: Sheet1 - 风格与艺术表现: 赛博朋克风格 - 镜头与构图: 反射镜头 - 人物与服饰: 穿厚重羽绒服的滑雪者 - 场景与背景: 冬季的滑雪度假村 - 细节与服饰: 灯光下的影子效果 - 色调与光效: 阴暗的光影效果 - 文化与环境: 日式庭院 - combined_prompt: 赛博朋克风格，反射镜头，穿厚重羽绒服的滑雪者，冬季的滑雪度假村，灯光下...

## Case 2: 场景类提示词优化

- Raw prompt: 清晨云海中的古风山寺
- Platform: Midjourney
- Style: 东方美学，空灵，层次丰富
- Goal: 强化空间层次、光影和环境细节

### llm_only

- Status: success
- Optimized prompt: 清晨，云海翻涌，一座古风山寺隐现于云雾之中，飞檐翘角，青瓦白墙，寺前石阶蜿蜒，松柏苍翠，远处山峦层叠，晨光微曦，金色光线穿透云层，洒在寺庙和山间，光影交错，空灵静谧，层次丰富，东方美学，超现实，细节精致，8K
- Notes:
  - 补充了空间层次：山峦层叠、云海翻涌、石阶蜿蜒，强化了远近关系
  - 强化了光影细节：晨光微曦、金色光线穿透云层、光影交错，增加了氛围感
  - 细化了建筑元素：飞檐翘角、青瓦白墙、松柏苍翠，使主体更具体
  - 加入了风格关键词：空灵静谧、超现实、细节精致、8K，符合东方美学和空灵要求

### retrieval_only

- Status: success
- Retrieval query: `原始提示词：清晨云海中的古风山寺
目标平台：Midjourney
风格偏好：东方美学，空灵，层次丰富
优化目标：强化空间层次、光影和环境细节`
- Notes:
  - 共检索到 3 个相关片段。
  - 该模式只展示可追溯的知识片段，不生成最终优化提示词。
- Sources: jimeng_prompt_knowledge_base.md
- Top chunk source: jimeng_prompt_knowledge_base.md
- Top chunk preview: 色调与光效: 青铜器氧化般的绿调光泽 - 文化与环境: 古埃及的神殿 - combined_prompt: 运动风格，遮蔽镜头，赛博观音千手义体，冰川封存的二战潜艇，青花瓷冰裂纹，青铜器氧化般的绿调光泽，古埃及的神殿  ### Record 049  - 序号: 49 - source_sheet: Sheet1 - 风格与艺术表现: 复古风格 - 镜头与构...

### rag

- Status: success
- Optimized prompt: 东方美学，空灵，层次丰富，清晨云海中的古风山寺，青铜器氧化般的绿调光泽，玛瑙纹路的光影交错，翡翠绿的水下折射光线，抽屉式纵深，不完美构图镜头
- Retrieval query: `原始提示词：清晨云海中的古风山寺
目标平台：Midjourney
风格偏好：东方美学，空灵，层次丰富
优化目标：强化空间层次、光影和环境细节`
- Notes:
  - 补充了色调与光效维度：从参考中提取了‘青铜器氧化般的绿调光泽’、‘玛瑙纹路的光影交错’和‘翡翠绿的水下折射光线’，以强化光影层次和空灵质感
  - 补充了构图与空间维度：引入‘抽屉式纵深’和‘不完美构图镜头’，增强空间层次感和视觉深度
  - 保留了原始主题‘清晨云海中的古风山寺’和‘东方美学，空灵，层次丰富’的风格要求，未改变核心意图
- Sources: jimeng_prompt_knowledge_base.md
- Top chunk source: jimeng_prompt_knowledge_base.md
- Top chunk preview: 色调与光效: 青铜器氧化般的绿调光泽 - 文化与环境: 古埃及的神殿 - combined_prompt: 运动风格，遮蔽镜头，赛博观音千手义体，冰川封存的二战潜艇，青花瓷冰裂纹，青铜器氧化般的绿调光泽，古埃及的神殿  ### Record 049  - 序号: 49 - source_sheet: Sheet1 - 风格与艺术表现: 复古风格 - 镜头与构...

## Case 3: 产品海报类提示词优化

- Raw prompt: 一款高端香水的广告海报
- Platform: 通用
- Style: 商业摄影，极简高级
- Goal: 突出材质、品牌感和广告构图

### llm_only

- Status: success
- Optimized prompt: A minimalist commercial photography advertisement poster for a high-end perfume, featuring a single elegant glass bottle with a metallic cap, placed on a reflective marble surface, soft studio lighting creating subtle shadows, emphasizing the luxurious texture of the glass and metal, clean composition with negative space, brand-focused, high contrast, sharp details, 8K resolution, cinematic lighting, premium advertising style.
- Notes:
  - 补充了具体场景元素：玻璃瓶身、金属瓶盖、大理石表面、反射效果
  - 强化了材质表现：玻璃与金属的质感、光影细节
  - 明确了摄影风格：商业摄影、极简构图、负空间、品牌感
  - 增加了技术参数：柔光、高对比、8K分辨率、电影级布光

### retrieval_only

- Status: success
- Retrieval query: `原始提示词：一款高端香水的广告海报
目标平台：通用
风格偏好：商业摄影，极简高级
优化目标：突出材质、品牌感和广告构图`
- Notes:
  - 共检索到 3 个相关片段。
  - 该模式只展示可追溯的知识片段，不生成最终优化提示词。
- Sources: ai_image_prompts_synthesis.md, jimeng_prompt_knowledge_base.md
- Top chunk source: ai_image_prompts_synthesis.md
- Top chunk preview: 么是画面主角 2. 场景：主角位于什么环境 3. 构图：远近景、视角、主体位置、留白 4. 风格：摄影、插画、水彩、3D、海报、像素风 5. 视觉细节：材质、纹理、颜色、道具、动作 6. 光线与氛围：晨光、霓虹、柔光、压抑、治愈、史诗感 7. 约束：不要什么、哪些部分不能变 8. 输出要求：尺寸、质量、格式、是否参考原图、是否局部编辑  ## 各来源共同强调...

### rag

- Status: success
- Optimized prompt: 商业摄影，极简高级风格，一款高端香水广告海报。香水瓶置于画面中央偏下，采用低角度微距拍摄，瓶身由磨砂玻璃与金属材质构成，表面有细腻的纹理和反光。背景为纯色渐变（如深灰到黑或香槟金），左侧柔光主灯打亮瓶身，右侧补光勾勒轮廓，底部有微弱反射光。构图留白充足，突出品牌感和材质质感，无文字和水印，16:9比例，超高清画质。
- Retrieval query: `原始提示词：一款高端香水的广告海报
目标平台：通用
风格偏好：商业摄影，极简高级
优化目标：突出材质、品牌感和广告构图`
- Notes:
  - 补充了材质特征（磨砂玻璃、金属、纹理反光），突出品牌感和高级感
  - 明确了构图（中央偏下、低角度微距、留白）和光线方案（左侧主光、右侧补光、底部反射），增强广告海报的视觉冲击力
  - 添加了背景风格（纯色渐变）和输出尺寸（16:9、超高清），符合商业摄影和极简高级的要求
- Sources: ai_image_prompts_synthesis.md, jimeng_prompt_knowledge_base.md
- Top chunk source: ai_image_prompts_synthesis.md
- Top chunk preview: 么是画面主角 2. 场景：主角位于什么环境 3. 构图：远近景、视角、主体位置、留白 4. 风格：摄影、插画、水彩、3D、海报、像素风 5. 视觉细节：材质、纹理、颜色、道具、动作 6. 光线与氛围：晨光、霓虹、柔光、压抑、治愈、史诗感 7. 约束：不要什么、哪些部分不能变 8. 输出要求：尺寸、质量、格式、是否参考原图、是否局部编辑  ## 各来源共同强调...
