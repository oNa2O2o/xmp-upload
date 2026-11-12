# 官方素材（skill 内置，不去 Z: 找）

用户 2026-11-12：「官方图片这种通用素材给我内置到放到skill里，还找你妈找，同步更新每一个单独的skill」。mm-packager 和 xmp-upload 各带一份同样的文件。

| 文件 | 内容 | 来源 |
|---|---|---|
| `Google_Play_Badge_JA.svg.png` | 日文 Google Play「で手に入れよう」官方原图 | Z:/创新事业部/AIGC项目视频组/设计师物料总库/平面素材/UI素材/商店图标 |
| `ios_badge.png` | 日文 App Store「からダウンロード」官方原图 | 同上 |
| `store_badges_EN.png` | 英文 GET IT ON Google Play / Download on the App Store 合图 | 同上（原名 6b7660ba…-v2jd7g.png） |
| `logo_icon.png`、`logo_word.png` | MiraiMind 图标、MIRAiMIND 字标 | Z:/创新事业部/AIGC项目视频组/mm-packager资源/jp-endcard/assets |
| `badges.png` | 两个日文官方标同尺寸并排（588×150 画布居中），给 app-ui、jp-endcard 用 | 用 mm-packager `modules/endcard3/mmlib.py` 的 `store_badges(height=75, gap=40)` 从上面两张原图生成 |

两个标同尺寸的做法：同高等比缩放，App Store 外框按 Google Play 宽度补齐，原版内容居中（`store_badges()`）。原图有更新时替换这里的文件，再重新生成 `badges.png`（xmp-upload 还要重新生成 `assets/h5/assets/as.png`、`gp.png`：`store_badges(height=120, gap=0)` 拆成两张）。
