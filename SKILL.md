---
name: xmp-upload
version: 3.0.0
description: 把 F:\钟海明\素材命名上传\输入 里的视频按素材命名台规则重命名（可一条素材出 FB/GG/TT 多个渠道版本），上传到 XMP 的 MiraiMind素材库/<地区>/<渠道>/<性向> 文件夹，并在本地 已上传\<周一>-<周日> 归档。用户说「素材命名上传」「上传XMP」「重命名上传」「传素材」「素材入库」或调用 /skill:xmp-upload 时使用。
---

# XMP 素材命名上传

固定路径：
- 输入：`F:\钟海明\素材命名上传\输入`
- 归档：`F:\钟海明\素材命名上传\已上传\<本周一YYMMDD>-<本周日YYMMDD>`（例 `261019-261025`）
- 命名规则源：`F:\钟海明\素材命名上传\素材命名台.html`（脚本实时读取其中 `const D = {...}`，规则/标签更新了不用改脚本）
- XMP 登录态：Chrome 配置目录 `F:\钟海明\素材命名上传\.xmp_profile`，CDP 端口 9333。**登录态已保存，不要退出、不要换目录、不要让用户重新登录。**
- **这个 Chrome 默认无窗口（`--headless=new`）**，在后台跑，不弹窗、不抢焦点，不会打扰用户工作。它和用户日常用的 Chrome 是两个独立进程，脚本只会杀带 `xmp_profile` 的进程。只有登录失效时才用 `python scripts/xmp.py login` 开一个带窗口的给用户登录，登录完用 `python scripts/xmp.py headless` 切回后台。
- 文件夹 id 通过 XMP 接口拿（`xmp.py folders`，缓存到 `folder_ids.json`）。直接打开 `/creative/upload?folder_id=…` 上传，不用点左侧的树。

脚本都在本 skill 的 `scripts/`，运行前 `export PYTHONIOENCODING=utf-8`。

## 命名格式（2026-10-22 起，命名台 `素材命名台_20261022_T编号_保留画风`）

```
视频：日期-地区-V-素材类型-面向-时长｜画风｜【标签id,...】｜{T月日设计师序号}｜-渠道-设计师-尺寸-版本
图片：日期-地区-P-素材类型-面向-画风｜【标签id,...】｜{T月日AI序号}｜-GG-AI-尺寸-版本
261021-JP-V-原创-男性向-30秒｜2D｜【562,247,493,456】｜{T1021ZHM1}｜-FB-ZHM-竖-1.mp4
```

- 10-22 删掉了 **板式 / 勾子 / 短标题**；画风改成 **真人 / 2D / 3D**（「二次元」脚本自动转 2D；无角色的素材用户规定写「无」）。
- **素材编号** `{T` + 月日 4 位 + 设计师代码 + 序号 `}`，不再带年份和性别字母。旧格式 `{material20261021MZHM1}` 脚本仍能识别（查重、查序号），但不再生成。
- **序号 = 该设计师当天第几条**（编号里带设计师代码；XMP 上同事也是按人各自从 1 数）。`python scripts/xmp.py seq [YYMMDD] [设计师]` 查 XMP 最新 2000 条 + 本地 已上传/输入，输出 `NEXT n` 作为默认值。已经用过的序号不改。
- 图片（`--form P`）：渠道固定 GG、设计师固定 AI，没有时长。
- 全性向：命名台只有男/女性向，但 XMP 有全性向文件夹，用户确认继续支持。
- 同一条素材的所有尺寸、所有渠道、所有版本共用一个编号；编号后跟一个「｜」再接 `-渠道`。同一编号不能给两条内容不同的素材：`naming.py build` 查本地，冲突时 `--apply` 拒绝。
- 规则改版后批量改历史文件：`naming.py convert <旧名>` 生成新名 → 存对照表 json → `scripts/rename_xmp.py <对照表> [--only 关键字] [--apply]` 调 XMP 接口 `updateName` 直接改名（保留素材 ID 和投放数据，不重传，改完逐个核对）→ 本地按对照表 os.rename。10-22 那次的对照表在 `已上传±019-261025\改名对照_20261022.json`。

## 每条视频需要用户提供的信息

| 字段 | 可选值 | 谁来定 |
|---|---|---|
| 地区 | JP / KR / EN / TC | 用户 |
| 图片/视频 | V / P | 默认 V |
| 素材类型 | 原创 / 迭代 / 二创 / UGC | 用户 |
| 面向 | 男性向 / 女性向 / 全性向 | 用户 |
| 画风 | 真人 / 2D / 3D / 无 | 用户（可看视频建议） |
| 标签 | 1–5 个该地区标签 id | 我用 `naming.py tags` 搜，用户确认 |
| 渠道 | FB / GG / TT，可多选，每个渠道出一个文件（图片固定 GG） | 用户 |
| 素材编号序号 | 1 以上整数，该设计师当天第几条 | `xmp.py seq` 给默认值，用户确认 |

自动/默认：日期=今天；时长=ffprobe 取最近档位（6/15/30/40秒）；尺寸=分辨率（竖/横/方）；设计师=ZHM；版本=1（重名或用户指定时递增）。

可以直接发给用户的填写模板：
```
文件：女警.mp4
地区：JP　类型：原创　面向：男性向　画风：2D
标签：警察 制服 霸道（或 id）
渠道：FB GG TT
素材序号：（我先查好填上，你确认）
```

## 流程

1. **看输入**：`ls 输入`，对每个视频 `python scripts/naming.py probe <视频>`，把时长/尺寸告诉用户。信息不全就用上面的模板问，缺什么问什么，不要猜地区/面向/渠道。
2. **选标签**：`python scripts/naming.py tags <地区> <关键词...>`（中文、日文都能搜），给出 id + 中文名让用户确认。
3. **预览命名**：`python scripts/naming.py build <视频> --region .. --type .. --gender .. --style 2D --tags 1,2,3 --seq <序号> --channels FB,GG,TT`（序号先跑 `python scripts/xmp.py seq`）。校验失败会列出原因。把全部文件名给用户看，⛔ **等用户确认**。
4. **生成文件**：同一条命令加 `--apply`，在 输入 里按渠道复制改名文件，原视频不动。用 `explorer.exe "F:\钟海明\素材命名上传\输入"` 打开文件夹给用户看。
5. **上传**（用户说传之后）：所有改名文件一条命令传完（可以跨多条视频），默认 4 个并行：
   `python scripts/upload.py "<改名文件1>" "<改名文件2>" ...`（先加 `--dry` 只看 文件→XMP文件夹 的对应关系）
   - 目标文件夹从文件名自动推出：`<地区>/<FB→Facebook|GG→Google|TT→Tiktok>/<男性向|女性向|全性向>`。
   - JP/Facebook 下的 M1–M6、F1–F6 子文件夹**不管**，只传到 男性向/女性向。
   - 上传前会用接口查目标文件夹，已有同名素材就直接报错（这时改版本号）。
   - 每个文件输出 `VERIFIED <路径> <文件名>` 才算成功（上传后用接口查列表确认）。全部成功 exit 0；有 FAILED 就 exit 2，停下来查，不要重复上传。
6. **归档**：全部 VERIFIED 后 `python scripts/archive.py <原视频> <改名文件1> <改名文件2> ...`：改名文件移到本周归档目录（所有渠道版本都留），原视频进回收站。
7. 汇报：每个文件 → XMP 路径 → 归档路径。

## 坑（已踩过）

- 接口 `xmp-api.mobvista.com` 必须带 `authorization: Bearer …`，页面里直接 fetch 会返回 401。`xmp.api_token()` 会从页面自己发出的请求里截取 token。
  - 文件夹树：`POST /material_center/folder/config {"zone":"company"}`
  - 列表：`GET /mediacenter/manage/searchList?folder_id=…`
- 上传结束后会关掉多余的标签页，只留一个 manage 页。
- 选文件只能用 CDP `DOM.setFileInputFiles` 设置一次。Playwright 的 `set_input_files` 走 CDP 会超时，但文件其实已经加进去了，再设一次就会重复。`upload.py` 会检查卡片数，不是 1 就不点确定。
- 上传页「过滤重复素材」默认勾选。XMP 里已有同一个视频时卡片数可能一直是 0，最后超时。这时告诉用户「XMP 已有重复素材」，不要自作主张取消勾选。
- 页面上有 driver.js 新手引导遮罩，会挡住点击，`xmp.clean()` 会把它删掉。
- 左侧虚拟树点击不稳（KR 超时、TC 找不到），所以上传已经不依赖它。`open_folder()` 只留作人工排查。
- Chrome 没开的话，`xmp.get_page()` 会用保存的登录配置**以无窗口方式**自动启动。`python scripts/xmp.py check` 输出 NOT_LOGGED_IN 时，跑 `xmp.py login`，让用户登录一次，然后跑 `xmp.py headless`。
- 要给用户看 XMP 里的结果，用 `python scripts/xmp.py ls JP/Google/男性向` 列出文件名，不要开窗口。
- 上传页的标签、创意人都不填，设计师默认就是钟海明。
