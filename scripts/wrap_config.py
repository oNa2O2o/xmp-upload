"""wrap_config.py <源视频> <1比1设计图> <16比9设计图> <输出目录> [--stem 女警] [--force] [--output-dir 目录]
从生图设计里自动量出视频占位区的左右边界（逐列 RGB 突变的行中位数最大的位置），
生成同目录 package.py 用的 wrap.json，输出 <stem>_方.mp4 / <stem>_横.mp4。
只生成配置并打印量到的边界，供人工核对；不编码。
也可作模块使用：from wrap_config import make_config  →  返回 wrap.json 路径。"""
import argparse, json, shutil, subprocess, time
from pathlib import Path
import numpy as np
from PIL import Image

H = 1080


class SeamError(ValueError):
    """边界可疑（面板拉伸 >7% 或分界线强度 <12），未写配置。"""


def probe(v):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                          '-of', 'csv=p=0', str(v)], capture_output=True, text=True, check=True).stdout.strip()
    w, h = map(int, out.split(',')[:2]); return w, h


def edges(img, lo, hi):
    """strongest column jump inside [lo,hi) of image width -> boundary index (first column after the jump)."""
    # median over rows of adjacent-column RGB difference: a straight vertical seam scores on every row,
    # content edges only on some rows. Works on dark designs where mean luminance doesn't change.
    a = np.asarray(Image.open(img).convert('RGB')).astype(float)
    d = np.median(np.abs(np.diff(a, axis=1)).sum(2), axis=0); w = a.shape[1]
    s, e = int(lo * w), int(hi * w)
    i = s + int(np.argmax(d[s:e]))
    # jumps often span 2-3 columns; move past the whole ramp
    j = i
    while j + 1 < len(d) and j - i < 12 and d[j + 1] > d[i] * 0.4: j += 1
    k = i
    while k - 1 >= 0 and i - k < 12 and d[k - 1] > d[i] * 0.4: k -= 1
    return k, j + 1, a.shape[1], a.shape[0], float(d[i])


def even(n): return int(round(n / 2)) * 2


def make_config(video, square, landscape, out_dir, stem=None, force=False, output_dir=None, log=print):
    """量边界并写 <out_dir>/wrap.json；返回该路径。边界可疑且 force=False 时抛 SeamError。"""
    vw0, vh0 = probe(video)
    vw = even(H * vw0 / vh0)
    stem = stem or Path(video).stem
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    # 换设计重做：旧的 wrap.json / work 自动移到 旧版_<时间>\，设计图由调用方放好
    if (out / 'wrap.json').exists() or (out / 'work').exists():
        old = out / f'旧版_{time.strftime("%m%d-%H%M")}'; old.mkdir()
        for n in ('wrap.json', 'work'):
            if (out / n).exists(): shutil.move(str(out / n), str(old / n))
        log('旧配置已移到', old)
    # 1:1 — video on the left, panel on the right
    k, j, W, Hd, s = edges(square, 0.40, 0.75)
    sq_panel = [j + 2, 0, W - j - 2, Hd]  # +1px margin past the blend ramp
    log(f'1:1  设计 {W}x{Hd}  视频右边界 {k}-{j} (强度 {s:.0f}) → 面板 rect {sq_panel}')
    # 16:9 — video centred
    kl, jl, W2, H2, s1 = edges(landscape, 0.20, 0.45)
    kr, jr, _, _, s2 = edges(landscape, 0.55, 0.80)
    left = [0, 0, kl - 1, H2]; right = [jr + 2, 0, W2 - jr - 2, H2]
    log(f'16:9 设计 {W2}x{H2}  视频列 {kl}-{jr} (强度 {s1:.0f}/{s2:.0f}) → 左 {left} 右 {right}')
    side = (1920 - vw) // 2
    cfg = {'source': str(Path(video).resolve()), 'output_dir': str(Path(output_dir).resolve()) if output_dir else '.', 'work_dir': 'work', 'variants': [
        {'design': str(Path(square).resolve()), 'output': f'{stem}_方.mp4', 'size': [1080, 1080], 'video_x': 0, 'video_width': vw,
         'panels': [{'rect': sq_panel, 'dest': [vw, 0, 1080 - vw, 1080]}]},
        {'design': str(Path(landscape).resolve()), 'output': f'{stem}_横.mp4', 'size': [1920, 1080], 'video_x': side, 'video_width': vw,
         'panels': [{'rect': left, 'dest': [0, 0, side, 1080]}, {'rect': right, 'dest': [side + vw, 0, 1920 - side - vw, 1080]}]}]}
    warn = []
    for v in cfg['variants']:
        for p in v['panels']:
            r, d = p['rect'], p['dest']
            ratio = (r[2] / r[3]) / (d[2] / d[3])
            if abs(ratio - 1) > 0.07: warn.append(f'面板拉伸 {ratio:.3f}，超过 7%')
    if min(s, s1, s2) < 12: warn.append(f'边界不明显（强度 {min(s, s1, s2):.0f} < 12）')
    for w_ in warn: log('⚠', w_)
    if warn and not force:
        raise SeamError('边界可疑：打开设计图人工核对，确认后加 --force，或手改 wrap.json。未写配置。')
    p = out / 'wrap.json'; p.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding='utf-8')
    log('写入', p)
    return p


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('square'); ap.add_argument('landscape')
    ap.add_argument('out_dir'); ap.add_argument('--stem'); ap.add_argument('--force', action='store_true')
    ap.add_argument('--output-dir', help='成片输出目录（默认=套版目录 out_dir）')
    a = ap.parse_args()
    try:
        make_config(a.video, a.square, a.landscape, a.out_dir, a.stem, a.force, a.output_dir)
    except SeamError as e:
        raise SystemExit(str(e))


if __name__ == '__main__':
    main()
