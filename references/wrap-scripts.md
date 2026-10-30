# 套版合成脚本用法（原 video-wrap-design）

把一条**竖版成片**放进已确认的生图套版，输出 **1080×1080 方版** 和 **1920×1080 横版**，并自动校验。
可独立运行，也可作为 Python 模块被其他技能/脚本调用。

## 依赖

- Python 3.8+
- `pip install -r requirements.txt`（Pillow、numpy）
- `ffmpeg`、`ffprobe` 在 PATH 上（需含 libx264）

## 目录

```
scripts/wrap.py          一条命令入口 + Python API（wrap_video）
scripts/wrap_config.py   从设计图量视频占位区分界线，写 wrap.json（不编码）
scripts/package.py       按 wrap.json / task.json 合成 + 校验
references/              配置示例、生图提示词
tests/smoke.py           合成脚本的 FFmpeg 冒烟测试（临时合成素材）
SKILL.md                 Agent 技能说明（生图套版完整工作流）
```

## 设计图要求

- `design_1x1.png`：视频占位在**左侧**，品牌面板在右；分界线在图宽 40%–75% 之间。
- `design_16x9.png`：视频占位**居中**，左右各一面板；左分界线在 20%–45%，右分界线在 55%–80%。
- 分界线须是一条竖直、整列可见的颜色突变。量不准时脚本会停下（见下文 `--force`）。

## 命令行

```bash
cd scripts
python wrap.py <竖版视频.mp4> <design_1x1.png> <design_16x9.png> <套版目录> --stem 女警
```

输出（默认都在 `<套版目录>`）：

| 文件 | 说明 |
|---|---|
| `<stem>_方.mp4` / `<stem>_横.mp4` | 成片 |
| `wrap.json` | 量到的配置，可手改后用 `python package.py wrap.json` 重跑 |
| `work/check-*.png` | 检查帧（每版 3 张），**交付前须人工查看** |
| `work/verification.json` | 尺寸、帧率、帧数、完整解码、音轨位流哈希校验结果 |

常用参数：

| 参数 | 作用 |
|---|---|
| `--stem 名` | 成片名前缀，默认用视频文件名 |
| `--output-dir 目录` | 成片放到别处（wrap.json/work 仍在套版目录） |
| `--config-only` | 只量边界写 wrap.json，不编码，先人工核对 |
| `--force` | 分界线强度 <12 或面板拉伸 >7% 时仍继续（先确认设计图没问题） |
| `--preset` / `--crf` | x264 参数，默认 `medium` / `18` |

分步执行（与 SKILL.md 节点 6 一致）：

```bash
python wrap_config.py <视频> <1x1> <16x9> <套版目录> --stem 名 [--output-dir 目录]
python package.py <套版目录>/wrap.json
```

## 作为模块

```python
import sys
sys.path.insert(0, r'<xmp-upload>/scripts')
from wrap import wrap_video, SeamError

r = wrap_video('竖版.mp4', 'design_1x1.png', 'design_16x9.png', '套版/女警',
               stem='女警', output_dir=None, force=False, preset=None, crf=None,
               config_only=False, log=print)      # log=lambda *a: None 可静默
r['square']        # .../女警_方.mp4
r['landscape']     # .../女警_横.mp4
r['config']        # wrap.json
r['verification']  # work/verification.json
r['check_frames']  # 检查帧路径列表
r['report']        # 校验报告 dict（config_only=True 时为 None）
```

异常：

- `SeamError`（`ValueError` 子类）：分界线可疑，未写配置。
- `FileExistsError`：成片已存在，绝不覆盖；换 `stem` 或先移走旧成片。
- `ValueError` / `subprocess.CalledProcessError`：源视频不合规（变帧率、旋转、SAR≠1）或校验失败。

也可单独调用：`wrap_config.make_config(...)` 返回 wrap.json 路径；`package.package(cfg_path)` 返回报告。

## 行为说明

- 视频高度固定 1080，宽度按源比例取偶数（9:16 → 608px），顶底贴边、无边框。
- 音轨 `-c:a copy` 原样保留，并比较位流哈希；不使用输出级 `-shortest`。
- 同一套版目录重跑时，旧的 `wrap.json`、`work/` 自动移到 `旧版_<月日-时分>/`；已存在的成片不会被覆盖。
- 路径都写成绝对路径进 wrap.json；脚本内无任何机器相关的硬编码路径。

## 测试

```bash
python tests/smoke.py
```
