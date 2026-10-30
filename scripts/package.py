"""Composite accepted generated panels with real video; never redesign the panels.
Usage: python package.py task.json
Dependencies: Pillow, ffmpeg, ffprobe. Paths resolve relative to task.json.
"""
import argparse
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path
from PIL import Image


def run(args):
    return subprocess.run(args, check=True, capture_output=True)


def probe(path, count=False):
    args = ['ffprobe', '-v', 'error']
    if count:
        args += ['-count_frames']
    return json.loads(run(args + ['-show_streams', '-show_format', '-of', 'json', str(path)]).stdout)


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def audio_hash(path):
    return run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a',
                '-c', 'copy', '-f', 'streamhash', '-hash', 'sha256', '-']).stdout.decode().strip()


def rect_valid(rect, size):
    x, y, w, h = rect
    return all(isinstance(n, int) for n in rect) and x >= 0 and y >= 0 and w > 0 and h > 0 and x + w <= size[0] and y + h <= size[1]


def package(config_path):
    config_path = Path(config_path).resolve()
    cfg = json.loads(config_path.read_text(encoding='utf-8'))
    base = config_path.parent
    source = (base / cfg['source']).resolve()
    out = (base / cfg['output_dir']).resolve()
    work = (base / cfg['work_dir']).resolve()
    meta = probe(source, True)
    videos = [s for s in meta['streams'] if s['codec_type'] == 'video' and not s.get('disposition', {}).get('attached_pic')]
    if len(videos) != 1:
        raise ValueError('Expected one source video stream')
    v = videos[0]
    if v.get('sample_aspect_ratio', '1:1') not in ('1:1', 'N/A') or any(s.get('rotation', 0) != 0 for s in v.get('side_data_list', [])) or float(v.get('tags', {}).get('rotate', 0)) != 0:
        raise ValueError('Normalize rotation / pixel aspect ratio before packaging')
    fps = Fraction(v['avg_frame_rate'])
    if fps <= 0 or fps != Fraction(v['r_frame_rate']):
        raise ValueError('Variable/unknown frame rate: normalize and verify timing first')
    audio = [s for s in meta['streams'] if s['codec_type'] == 'audio']
    expected_audio = audio_hash(source) if audio else None
    variants = cfg['variants']
    if not variants:
        raise ValueError('No variants')
    # Preflight every output and all geometry before launching any encode.
    prepared = []
    seen = set()
    for variant in variants:
        name = variant['output']
        if Path(name).name != name or not name.lower().endswith('.mp4'):
            raise ValueError('Output must be an MP4 basename')
        dest = out / name
        if dest.exists() or dest in seen:
            raise FileExistsError(dest)
        seen.add(dest)
        width, height = variant['size']
        x, vw = variant['video_x'], variant['video_width']
        if any(not isinstance(n, int) or n % 2 for n in [width, height, x, vw]) or min(width, height, vw) <= 0 or x < 0 or x + vw > width:
            raise ValueError('Video/canvas geometry must be valid even integers')
        if abs(vw - height * v['width'] / v['height']) > 1:
            raise ValueError('Video aspect ratio changed beyond one-pixel rounding')
        design = Image.open(base / variant['design']).convert('RGB')
        canvas = Image.new('RGB', (width, height))
        coverage = Image.new('1', canvas.size, 0)
        from PIL import ImageDraw
        pen = ImageDraw.Draw(coverage)
        pen.rectangle((x, 0, x + vw - 1, height - 1), fill=1)
        for panel in variant['panels']:
            r, d = panel['rect'], panel['dest']
            if not rect_valid(r, design.size) or not rect_valid(d, canvas.size):
                raise ValueError('Panel out of bounds')
            sx, sy, sw, sh = r
            dx, dy, dw, dh = d
            if coverage.crop((dx, dy, dx + dw, dy + dh)).getbbox():
                raise ValueError('Panel overlaps video or another panel')
            canvas.paste(design.crop((sx, sy, sx + sw, sy + sh)).resize((dw, dh), Image.Resampling.LANCZOS), (dx, dy))
            pen.rectangle((dx, dy, dx + dw - 1, dy + dh - 1), fill=1)
        if coverage.getextrema() != (1, 1):
            raise ValueError('Uncovered canvas area')
        prepared.append((variant, dest, canvas))
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    report = {'source': str(source), 'source_sha256': sha256(source), 'outputs': []}
    for i, (variant, dest, canvas) in enumerate(prepared):
        background = work / f'background-{i}.png'
        canvas.save(background)
        width, height = variant['size']
        x, vw = variant['video_x'], variant['video_width']
        partial = out / (dest.stem + '.partial.mp4')
        if partial.exists():
            raise FileExistsError(partial)
        args = ['ffmpeg', '-hide_banner', '-nostdin', '-n', '-loop', '1', '-framerate', str(fps), '-i', str(background), '-i', str(source),
                '-filter_complex', f'[1:v:0]scale={vw}:{height}:flags=lanczos,setsar=1[v];[0:v][v]overlay={x}:0:shortest=1:format=auto,format=yuv420p[out]',
                '-map', '[out]', '-map', '1:a?', '-c:v', 'libx264', '-preset', cfg.get('preset', 'medium'), '-crf', str(cfg.get('crf', 18)),
                '-threads', '6', '-c:a', 'copy', '-movflags', '+faststart', str(partial)]
        with (work / f'encode-{i}.log').open('wb') as log:
            subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True)
        result = probe(partial, True)
        rv = next(s for s in result['streams'] if s['codec_type'] == 'video')
        if (rv['width'], rv['height']) != (width, height) or Fraction(rv['avg_frame_rate']) != fps or rv.get('nb_read_frames') != v.get('nb_read_frames'):
            raise ValueError(f'Video verification failed: {partial}')
        decode = run(['ffmpeg', '-v', 'error', '-i', str(partial), '-f', 'null', '-'])
        if decode.stderr.strip():
            raise ValueError(decode.stderr.decode(errors='replace'))
        ra = [s for s in result['streams'] if s['codec_type'] == 'audio']
        if len(ra) != len(audio) or (audio and audio_hash(partial) != expected_audio):
            raise ValueError('Audio bitstream changed')
        duration = float(meta['format']['duration'])
        times = cfg.get('check_times', [duration * .2, duration * .65, max(0, duration - 1)])
        frames = []
        for k, t in enumerate(times):
            if not 0 <= t < float(v.get('duration', duration)):
                raise ValueError('Check frame time out of range')
            frame = work / f'check-{i}-{k}.png'
            run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', str(partial), '-frames:v', '1', str(frame)])
            if not frame.exists():
                raise ValueError('No check frame written')
            frames.append(str(frame))
        if dest.exists():
            raise FileExistsError(dest)
        partial.rename(dest)
        report['outputs'].append({'file': str(dest), 'size': [width, height], 'fps': str(fps), 'frames': rv['nb_read_frames'],
                                  'duration': result['format']['duration'], 'full_decode': True,
                                  'audio_unchanged': True if audio else 'source has no audio', 'check_frames': frames,
                                  'visual_review': 'pending: open check frames before delivery'})
        (work / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Encoded and checked: {dest}', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    package(parser.parse_args().config)
