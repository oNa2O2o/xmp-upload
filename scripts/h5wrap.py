"""H5 套版：渲染面板 + 合成方 / 横版（替代生图套版的默认路线）。

用法：
  python h5wrap.py <任务目录> --spec <原片名关键字>=<theme>:<copy> [...] [--copy copy.json] [--only 关键字]
    theme: light（浅色视频）/ dark（深色视频）
    copy : copy.json 的 key，值为 ["标语", "描述"]（<br> 断行；取自投放看板验证过的文案）；
           不传 --copy 时用模板内置的 JP 示例组 a/b/c
  不传 --spec 时全部 dark:a。

输出：任务目录里 <原片名>_方.mp4 / _横.mp4；<任务目录>/h5work/ 下的面板 png 和检查帧（交付前人工看）。
原片列表只读 manifest.json 的 sources，不按目录通配。
"""
import sys, os, json, shutil, subprocess, argparse, pathlib

HERE = pathlib.Path(__file__).resolve().parent
TPL = HERE.parent / 'assets' / 'h5'


def sh(*a): subprocess.run(a, check=True)


def probe(f, key):
    return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', f'stream={key}',
                           '-of', 'csv=p=0', f], capture_output=True, text=True).stdout.strip().split(',')[0]


def dur(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
                                capture_output=True, text=True).stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('task'); ap.add_argument('--spec', nargs='*', default=[]); ap.add_argument('--copy')
    ap.add_argument('--only'); ap.add_argument('--crf', default='18')
    a = ap.parse_args()
    m = json.load(open(os.path.join(a.task, 'manifest.json'), encoding='utf-8'))
    srcs = [f for k, f in m['sources'].items() if k.split(':')[0] == '竖']
    if a.only: srcs = [f for f in srcs if a.only in os.path.basename(f)]
    work = pathlib.Path(a.task) / 'h5work'; (work / 'bg').mkdir(parents=True, exist_ok=True)
    # 模板复制进工作目录（背景帧要和 html 同目录相对引用）
    for x in ('wrap.html', 'assets'):
        t = work / x
        if not t.exists(): (shutil.copytree if (TPL / x).is_dir() else shutil.copyfile)(TPL / x, t)
    copies = json.load(open(a.copy, encoding='utf-8')) if a.copy else {}
    from urllib.parse import quote
    from playwright.sync_api import sync_playwright
    jobs = []
    for i, f in enumerate(srcs, 1):
        stem = os.path.splitext(os.path.basename(f))[0]; bid = f'{i:02d}'
        theme, copy = 'dark', 'a'
        for s in a.spec:
            k, v = s.split('=')
            if k in stem: theme, copy = v.split(':')
        sh('ffmpeg', '-v', 'error', '-y', '-ss', str(round(dur(f) * .35, 2)), '-i', f, '-frames:v', '1', '-update', '1', str(work / 'bg' / f'{bid}.png'))
        jobs.append((f, stem, bid, theme, copy))
    with sync_playwright() as p:
        b = p.chromium.launch()
        for f, stem, bid, theme, copy in jobs:
            for mode, w in (('sq', 1080), ('ls', 1920)):
                pg = b.new_page(viewport={'width': w, 'height': 1080})
                pg.goto((work / 'wrap.html').as_uri() + f'?mode={mode}&theme={theme}&bg={bid}&c={copy}'
                        + (f'&t={quote(copies[copy][0])}&d={quote(copies[copy][1])}' if copy in copies else ''))
                pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(400)
                pg.screenshot(path=str(work / f'{bid}_{mode}.png')); pg.close()
        b.close()
    for f, stem, bid, theme, copy in jobs:
        fps = probe(f, 'r_frame_rate')
        for mode, x, suf in (('sq', 0, '_方'), ('ls', 656, '_横')):
            out = os.path.join(a.task, stem + suf + '.mp4')
            sh('ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', fps, '-i', str(work / f'{bid}_{mode}.png'), '-i', f,
               '-filter_complex', f'[1:v]scale=608:1080,setsar=1[v];[0:v][v]overlay={x}:0:shortest=1,format=yuv420p[o]',
               '-map', '[o]', '-map', '1:a?', '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'medium', '-crf', a.crf, out)
            sh('ffmpeg', '-v', 'error', '-y', '-ss', '10', '-i', out, '-frames:v', '1', '-update', '1', str(work / f'check_{bid}{suf}.png'))
        print('done', stem)
    print('检查帧', work)


if __name__ == '__main__':
    main()
