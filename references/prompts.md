# 套版提示词（MiraiMind）

分两部分：**标准**（每条素材通用的参考图、文案库、版式规则）和**案例**（只属于某条素材，只能参考）。

# 标准

## 参考图

1. `assets/brand-lockup.png` — 图标 + 字标（原图字是白色）。**字标颜色跟背景走**：深色底保持白色，浅色底在提示词里写明改成深海军蓝 #0F1530。
2. `assets/app-icon.png` — App 图标
3. `character_ref.png` — 从视频截出的角色，1–2 帧裁成方图横拼
4. `video_preview.png` — 视频一帧，只用作视频区占位
5. `assets/store-badges.png` — **只有 EN 用**（英文官方徽章）。其他地区不传这张，在提示词里逐字写出当地语言的徽章文字让模型画：
   - JP：「App Storeからダウンロード」「Google Play で手に入れよう」
   - KR / TC：首次使用时写出并给用户确认

## 文案库（标语、卖点；每条素材从这里挑，新句子要中文对照给用户确认）

| 地区 | 标语候选 | 卖点 | 状态 |
|---|---|---|---|
| EN | — | `100,000+ Characters` / `Available 24/7` / `Instant Replies` / `Feels Real` | 已确认（马尔福） |
| JP | `AIキャラと本気トーク`（AI 角色真心聊天）；女性向 `AIの彼と、本気の恋。`（和 AI 恋人谈一场认真的恋爱） | `10万+ キャラクター`、`24時間いつでも`（24 小时随时）、`即レス`（秒回）、`まるで本物`（像真的一样） | 女警、JP 13 条用过，用户已选定 |
| KR | — | `10만+ 캐릭터` / `24시간 언제나` / `즉시 답장` / `진짜 같은 대화` | 草稿，待确认 |
| TC | — | `10萬+ 角色` / `24小時隨時在線` / `秒回` / `超真實` | 草稿，待确认 |

剧情台词（如聊天气泡）**不进文案库**，每条素材按剧情重写。

## 版式（按地区选默认方向，每条素材仍要用户确认）

| 地区 | 默认方向 | 依据 |
|---|---|---|
| JP | 方版「暗色留白 B」+ 横版「H3 聊天气泡」 | 女警：花哨日式被否（太扎眼、太花，要留白、暗色背景）；用户从 4 个方向选了 B、横版选了 H3 |
| EN | 欧美极简（下方提示词） | 马尔福 |
| KR / TC | 没有默认，先出方向总览让用户挑 | 未实测 |

**暗色留白 B（1:1）**：近黑底，无纹理、闪光、描边、光晕；面板上方 logo → 两行横排白色黑体标语；中下部角色压暗在阴影里，只留轮廓光和发光的眼睛，渐隐进黑底；底部两个小号商店徽章并排。不放奖牌、胶囊标签。

**H3（16:9）**：先出好 1:1，用 1:1 成图做 Image 1 风格参考。左面板 logo → 标语 → 两个暗色聊天气泡（角色小头像 + 一句贴合剧情的台词，用户回一句短话）→ 底部一行灰字卖点；右面板压暗角色 + 底部徽章并排。

## 通用提示词约束（每次都写进去）

- **用户指定（m01026），每张生图必须加**：「去除画面中的噪点和高频细节，保持所有线条颜色和亮度不变」，英文写作 `Remove all noise and high-frequency detail from the image; keep every line, color and brightness unchanged.`
- 画面图不带字（NO text），文字一律用真字体排版；镜头要有动态机位（俯拍、仰拍、倾斜、特写），不要平视站桩。

- Geometry: the video ends at ONE perfectly straight vertical line; every panel element at least 3% of canvas width away from it; nothing crosses it. 这段空隙由生图本身留出；合成时不压黑带、不缩小面板，面板铺满视频以外的区域，元素完整不裁切。
- 日文竖排时："AI" written horizontally as one unit (縦中横), the I must not look like a long-vowel bar.
- Text verbatim, each exactly once, outside the video; no other text, no 無料/free, no prices.
- No border, shadow, rounded corners or phone frame around the video.

## 方向总览（新角色 / 新地区 / 用户不满意时）

并行出 3–4 张不同方向的 1:1（每个方向一次 image_generate 调用），拼成带 A/B/C/D 字母的对比图放 `.tmp_wrap/待选/`，单张放同名子文件夹，`explorer` 打开，给每张写一句差异说明。用户选定后再出该方向的 16:9（横版也可以出 3 个文案方向的总览），选定版放 `.tmp_wrap/终版/`。

## 实测参数

生成套版图用 image2.5 模型（gpt-image-2.5-flare）。审核图的视频区用真实视频帧替换生图占位后再给用户看。

gpt-image-2.5-flare：2048×2048 返回 1254×1254，2560×1440 返回 1672×941。边界一律用 `wrap_config.py` 量，不按百分比推算。深色设计亮度变化小，wrap_config 用「逐行相邻列色差取中位数」找分界线；强度 <12 或面板拉伸 >7% 会拒绝写配置（`--force` 可跳过，需先人工核对）。

# 标准提示词：欧美极简（EN）

## 1:1 提示词（替换 {} 部分）

```
Use case: complete finished mobile-game advertising video-wrapper DESIGN MOCKUP (not a background plate).
Input images: Image 1: exact MiraiMind app icon + wordmark lockup (palette reference; keep the M-ghost icon shape and the wordmark spelling "MIRAiMIND" exactly; render the wordmark in dark navy #0F1530 instead of white). Image 2: exact app icon. Image 3: character identity reference — {角色外观：发型发色、眼睛、表情、服装，逐项写清}. Image 4: source video screenshot, use ONLY as the placeholder preview inside the video area. Image 5: authorized App Store / Google Play badge artwork.
Canvas: square 1:1.
Geometry: LEFT exactly 56.25% of the canvas width is one 9:16 vertical video preview, from x=0 to 56.25%, y=0 to 100%. It touches the LEFT, TOP and BOTTOM canvas edges. Fill it with Image 4. RIGHT remaining 43.75% is the brand panel. Keep all design elements strictly inside the right panel; whitespace lives inside the right panel, never as a gutter around the video.
Right panel, top to bottom: MiraiMind icon + "MIRAiMIND" wordmark at top; the same character from Image 3 ({姿势}), fading softly into the background; main feature with a people icon: "{主卖点大字}" large and "{主卖点小字}" below it; then three feature rows each with a simple purple line icon: clock with green online dot — "{功能1}"; chat bubble with lightning bolt — "{功能2}"; chat bubble with heartbeat line — "{功能3}"; at the bottom both store badges side by side copied from Image 5.
Backdrop of right panel: pearl-white with very subtle iridescent accents taken from the logo gradient (cyan #4CF0F0, lime #C8F060, lavender #A0A0FF, pink #F0A0F0).
Text (verbatim, each exactly once, outside the video): "MIRAiMIND", "{主卖点大字}", "{主卖点小字}", "{功能1}", "{功能2}", "{功能3}", plus the badge text. No other text, no extra headlines, no invented features, no prices.
Typography: bold rounded modern {语言} gothic, dark navy, high legibility; main number in purple-blue gradient.
Constraints: NO outer video border, NO shadow, NO rounded corners on the video, NO phone frame, NO top or bottom video margin. Character entirely outside the video area. Cohesive, polished, premium anime-app ad.
```

## 16:9 提示词

和 1:1 相同，只换这几段：

```
Canvas: landscape 16:9.
Geometry: CENTER video preview column from x=34.18% to x=65.82% of canvas width, y=0 to 100%, a 9:16 vertical video filled with Image 4. It touches the TOP and BOTTOM canvas edges, no frame. Keep all design outside the video column; spacing only inside the side panels.
LEFT panel: MiraiMind icon large on top, "MIRAiMIND" wordmark under it; main feature …; then three feature rows ….
RIGHT panel: the same character from Image 3 (half body, large), fading softly into the background at the bottom; both store badges side by side near the bottom copied from Image 5.
```


# 案例（只属于某条素材，只能参考）

## 女警（JP，男性向，2026-10-20）

- 选定：方版 B（`min_B_silhouette.png`）+ 横版 H3（`h3_chat.png`），设计在 `F:\钟海明\素材命名上传\套版\女警\`。
- 只属于这条：金色点缀和深蓝色调（来自制服和夜景）；聊天台词「今夜、少し付き合ってもらえる？」/「もちろん。」；命名字段 气泡对话 / D强势压迫 / 深夜被女警官拦车 / 标签 159,46,414,678,579。
- 过程：欧美版 → 花哨日式（被否：太扎眼太花）→ 4 个暗色方向选 B → 横版只有 logo + 标语被嫌空 → 3 个横版文案方向选 H3。
### 被否：花哨日式 1:1 提示词（反例，不要再用）

参考图只用 4 张：brand-lockup、app-icon、character_ref、video_preview（不传英文 store-badges，徽章让模型按文字画日文版）。

```
Use case: complete finished JAPANESE-market mobile app advertising video-wrapper DESIGN MOCKUP, in the style of Japanese smartphone game / マンガアプリ / 美少女ゲーム web ads (日本のアプリ広告バナー風), not a Western minimal layout.
Input images: Image 1: exact MiraiMind icon + wordmark lockup (keep M-ghost icon shape and spelling "MIRAiMIND" exactly; wordmark rendered white with thick dark navy outline). Image 2: exact app icon. Image 3: character identity reference — {角色外观}. Image 4: source video screenshot, use ONLY as placeholder inside the video area.
Canvas: square 1:1.
Geometry (strict): LEFT exactly 56.25% of canvas width is one 9:16 vertical video preview, x=0 to 56.25%, y=0 to 100%, touching LEFT, TOP and BOTTOM edges, filled with Image 4, no frame. The video ends at ONE perfectly straight vertical line. RIGHT 43.75% is the design panel; every panel element starts at least 3% of canvas width right of that line, nothing crosses it.
Right panel: background {场景色调，如 deep night-navy to violet gradient} with gold sparkles, light rays and subtle 集中線. Big VERTICAL catch copy written 縦書き along the panel's right edge: "AI" written horizontally as one unit (縦中横, the I must not look like a long-vowel bar) followed vertically by "キャラと本気トーク", heavy bold Japanese gothic, white letters with thick pink-magenta outline and gold glow (縁取り文字). Character from Image 3 large, half body, {姿势}, slightly breaking out of a manga-style panel. Top: app icon + "MIRAiMIND" wordmark. Lower panel, centered and fully inside the panel: gold medal badge with "10万+" huge and "キャラクター" under it; magenta pill tags "24時間いつでも", "即レス" (row) and "まるで本物" (below); two black store badges stacked vertically reading exactly "App Storeからダウンロード" (Apple logo) and "Google Play で手に入れよう" (Google Play logo).
Text (verbatim, each exactly once, outside the video): "MIRAiMIND", "AIキャラと本気トーク", "10万+", "キャラクター", "24時間いつでも", "即レス", "まるで本物", "App Storeからダウンロード", "Google Play で手に入れよう". No other text, no 無料, no prices.
Constraints: NO border, shadow, rounded corners or phone frame around the video. Character entirely in the right panel. Polished premium Japanese anime-app ad.
```

### 被否：花哨日式 16:9 提示词

和日式 1:1 相同，只换这几段：

```
Canvas: landscape 16:9.
Geometry (strict): CENTER video column from x=34.18% to x=65.82%, y=0 to 100%, filled with Image 4, touching TOP and BOTTOM, no frame, straight vertical edges; nothing from the side panels crosses them.
LEFT panel: app icon + "MIRAiMIND" wordmark at top; huge 縦書き catch copy in two columns: "AIキャラと" (AI as 縦中横) and "本気トーク", white with thick pink-magenta outline; next to it the gold medal badge "10万+" / "キャラクター"; three magenta pill tags "24時間いつでも", "即レス", "まるで本物" stacked.
RIGHT panel: character from Image 3 large, half body, {姿势}, speed lines; at the bottom two black store badges side by side "App Storeからダウンロード" and "Google Play で手に入れよう".
```

### 女警 JP 踩坑

- 第一次生成：`AI` 的 I 被画成长音「ー」→ 用编辑提示「AI 縦中横」修好。
- 1:1 第一次卖点区（奖牌、标签、App Store 徽章）越过分界线伸进视频区 → 合成后被视频盖住半截。提示词里要写死「一条笔直分界线 + 元素离线 ≥3%」，商店徽章竖排。生成后**必须看 check 帧确认没有元素被切**。
- 日式深色设计亮度变化小，旧的按列平均亮度找边界会失败（强度 13）。`wrap_config.py` 已改为「逐行相邻列色差取中位数」，强度 <12 或面板拉伸 >7% 会拒绝写配置（`--force` 可跳过）。


## JP 13 条（floze / 未亡人雪女 / 猫娘报恩 / 尾板 / 学妹辣妹，2026-10-29）

- 终稿：设计 `F:\BaiduSyncdisk\PI Agnet\.tmp_wrap\终版\ZHM<n>_方版.png / _横版.png`；floze（女性向）方版选 C（暗紫红 +「AIの彼と、本気の恋。」），尾板方横都选 B（大号「10万+ キャラクター」），其余 9 条用方版 B + 横版 H3，每条按自己的角色单独出图。成片 117 个（13 条 × 竖方横 × FB/GG/TT）全部 VERIFIED，例：`261029-JP-V-原创-男性向-40秒｜3D｜【584,219,422】｜{T1029ZHM5}｜-FB-ZHM-方-1.mp4`。
- 只属于这批的字段：雪女三条画风分别是真人 / 3D / 2D；学妹辣妹是迭代 + 3D（文件名没写迭代）；尾板画风「无」、标签 701。
- 踩坑：
  - 用户只说「上传xmp」，我直接走了命名上传：没套版、命名没确认就传了 39 个竖版，全部从 XMP 删掉重来。
  - 先逐项问字段被否；画风按组判，雪女三条、学妹辣妹（AI 超写实应为 3D）都判错。
  - 子 agent 的草稿、原图、作废版散在多个目录，用户问「哪个是终版」→ 改成只给 `终版\` 和 `待选\`。
  - 子 agent 为让角色离开分界线，在线旁压黑带、横版缩小面板留底边 → 用户指出黑边；从 `*_raw.png` 重拼，面板铺满、视频区换成真实帧。

---

## 附：通用套版提示词模板（非 MiraiMind 项目 / 自定义产品用）

使用前替换全部 `{变量}`。用户的明确要求优先。示例卖点不是其他项目默认产品承诺。

### 输入参考角色

- Image 1: exact product app icon, palette reference.
- Image 2: exact product wordmark; keep letter shapes and spelling.
- Image 3: character identity reference; preserve face, hair, clothing, rendering style.
- Image 4: source video screenshot, placeholder preview only.
- Image 5: authorized App Store / Google Play badge artwork.

可以合并或减少参考，但重新核对提示词编号，不把图标参考误作人物参考。缺少官方徽章时查找授权素材，生成图中的近似标志不得声称为像素准确的官方文件。

### 公共正文

Generate a COMPLETE finished advertising video-wrapper DESIGN MOCKUP, not merely a background plate.
Reference roles: {roles}.
Backdrop: pearl-white with very subtle accents taken from the actual logo: {palette}. Generous whitespace inside the information panel only.
Subject: the same character as reference {character_ref}, preserving {identity_invariants}. Keep the character entirely outside the video area.
Brand: include {app_icon_and_or_wordmark}, faithful shape and spelling.
Feature copy, verbatim, each exactly once outside the video preview: {exact_feature_strings}.
Feature icon semantics: {icon_mapping}. Use a consistent simple visual language, readable at output size.
Stores: include both original badge designs {exact_badge_strings}; preserve the recognizable Apple / Google Play marks.
Typography: {type_direction}, high legibility, clear primary/secondary hierarchy.
Constraints: NO outer video border, NO shadow, NO rounded corners, NO phone frame, NO top or bottom video margin, no extra headlines, no invented features. Render a cohesive complete composition.

### 1:1 几何附加段（9:16源）

Square canvas. LEFT exactly 56.25% of the canvas is one 9:16 vertical video preview, x=0 to 56.25%, y=0 to 100%. It touches the LEFT, TOP and BOTTOM edges of the canvas. Fill with the video screenshot. RIGHT remaining 43.75% is the brand panel: logo at top, character below, main feature, supporting feature rows, download badges at bottom. Keep all outer design strictly on the right. Whitespace is within the right panel, never a gutter around video.

### 16:9 几何附加段（9:16源）

Landscape 16:9 canvas. CENTER video preview x=34.18% to 65.82%, y=0 to 100%. It touches the TOP and BOTTOM edges, with no frame. LEFT panel: brand at top, main feature and supporting feature rows. RIGHT panel: character and download badges. Keep all design outside the video column. Internal panel spacing only.

### 本次已确认文案实例

- `100,000+ Characters` — 多人物图标
- `Available 24/7` — 时钟＋在线点
- `Instant Replies` — 对话＋闪电
- `Feels Real` — 对话＋心跳

这些只是马尔福素材中用户确认的文案。未来任务应重新读取用户的文案，不默认产品一定具有这些功能。

### 定向编辑模板

Image 1 is the accepted layout to edit. Change ONLY {specific_defect}. Keep {accepted_geometry, colors, face, exact_copy, other_assets} unchanged. All video edges remain flush to canvas. Do not move or redraw other panels.

若模型未精确保持文字或Logo，多轮仍失败，诚实报告限制并给出可选修正方案；不得违背“别自己拼”的约束私自改用手工设计。
