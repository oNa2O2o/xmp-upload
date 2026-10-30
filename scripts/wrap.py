"""一条命令：竖版视频 + 1:1/16:9 生图设计 → <stem>_方.mp4 / <stem>_横.mp4（已校验）。

CLI:
  python wrap.py <竖版视频> <design_1x1.png> <design_16x9.png> <套版目录> [--stem 名] [--force]
                 [--output-dir 成片目录] [--config-only] [--preset medium] [--crf 18]
模块:
  import sys; sys.path.insert(0, r'<本目录>')
  from wrap import wrap_video
  r = wrap_video(video, d1x1, d16x9, out_dir, stem='女警')
  r['square'], r['landscape'], r['check_frames'], r['verification']

流程 = wrap_config.make_config（量分界线写 wrap.json）→ package.package（合成 + 校验）。
依赖：Python 3、Pillow、numpy、PATH 上的 ffmpeg / ffprobe。
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    # 按文件路径加载，避免和调用方环境里同名的 package / wrap_config 模块冲突
    key = f'video_wrap_design_{name}'
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


wrap_config = _load('wrap_config', 'wrap_config.py')
packager = _load('package', 'package.py')
SeamError = wrap_config.SeamError


def wrap_video(video, square, landscape, out_dir, stem=None, force=False, output_dir=None,
               preset=None, crf=None, config_only=False, log=print):
    """返回 dict：config / square / landscape / work_dir / verification / check_frames / report。
    边界可疑抛 SeamError；输出已存在抛 FileExistsError；校验失败抛 ValueError / CalledProcessError。"""
    cfg_path = wrap_config.make_config(video, square, landscape, out_dir, stem=stem, force=force,
                                       output_dir=output_dir, log=log)
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    if preset is not None or crf is not None:
        if preset is not None: cfg['preset'] = preset
        if crf is not None: cfg['crf'] = crf
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding='utf-8')
    base = cfg_path.parent
    out = (base / cfg['output_dir']).resolve()
    work = (base / cfg['work_dir']).resolve()
    result = {'config': str(cfg_path), 'square': str(out / cfg['variants'][0]['output']),
              'landscape': str(out / cfg['variants'][1]['output']), 'work_dir': str(work),
              'verification': str(work / 'verification.json'), 'check_frames': [], 'report': None}
    if config_only:
        return result
    report = packager.package(cfg_path)
    result['report'] = report
    result['check_frames'] = [f for o in report['outputs'] for f in o['check_frames']]
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description='竖版视频套版 → 1:1 + 16:9 成片')
    ap.add_argument('video'); ap.add_argument('square', help='1:1 设计图'); ap.add_argument('landscape', help='16:9 设计图')
    ap.add_argument('out_dir', help='套版目录：写 wrap.json、work/；默认成片也在这里')
    ap.add_argument('--stem', help='成片名前缀，默认=视频文件名')
    ap.add_argument('--force', action='store_true', help='边界可疑时仍继续（先人工核对设计图）')
    ap.add_argument('--output-dir', help='成片输出目录（默认=out_dir）')
    ap.add_argument('--config-only', action='store_true', help='只量边界写 wrap.json，不编码')
    ap.add_argument('--preset', help='x264 preset，默认 medium'); ap.add_argument('--crf', type=int, help='默认 18')
    a = ap.parse_args(argv)
    try:
        r = wrap_video(a.video, a.square, a.landscape, a.out_dir, a.stem, a.force, a.output_dir,
                       a.preset, a.crf, a.config_only)
    except (SeamError, FileExistsError) as e:
        raise SystemExit(f'{type(e).__name__}: {e}')
    print('配置', r['config'])
    if a.config_only:
        print('仅配置，未编码。下一步：python package.py', r['config'])
        return r
    print('方版', r['square'])
    print('横版', r['landscape'])
    print('校验', r['verification'])
    for f in r['check_frames']:
        print('检查帧', f)
    print('提示：打开检查帧人工确认无元素被视频盖住后再交付。')
    return r


if __name__ == '__main__':
    main()
