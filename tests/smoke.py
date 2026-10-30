"""Real FFmpeg smoke checks; temporary synthetic media only."""
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wrap_package', root / 'scripts/package.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix='video-wrap-test-') as temp:
    p = Path(temp)
    # 1 second video, slightly longer AAC audio: regression for -shortest truncation.
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=108x192:r=30:d=1',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100:duration=1.08',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(p / 'source.mp4')], check=True)
    Image.new('RGB', (400, 400), '#b4dccc').save(p / 'design.png')
    cfg = {'source': 'source.mp4', 'output_dir': 'out', 'work_dir': 'work', 'preset': 'ultrafast', 'check_times': [.2, .6, .9], 'variants': [
        {'design': 'design.png', 'output': 'square.mp4', 'size': [192, 192], 'video_x': 0, 'video_width': 108,
         'panels': [{'rect': [0, 0, 100, 400], 'dest': [108, 0, 84, 192]}]},
        {'design': 'design.png', 'output': 'wide.mp4', 'size': [384, 216], 'video_x': 132, 'video_width': 122,
         'panels': [{'rect': [0, 0, 100, 400], 'dest': [0, 0, 132, 216]}, {'rect': [300, 0, 100, 400], 'dest': [254, 0, 130, 216]}]}]}
    config = p / 'task.json'
    config.write_text(json.dumps(cfg))
    report = module.package(config)
    assert len(report['outputs']) == 2
    assert all(o['audio_unchanged'] is True and o['frames'] == '30' for o in report['outputs'])
    try:
        module.package(config)
        raise AssertionError('Existing output overwritten')
    except FileExistsError:
        pass
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p / 'source.mp4'), '-map', '0:v', '-c', 'copy', str(p / 'silent.mp4')], check=True)
    cfg.update(source='silent.mp4', output_dir='silent-out', work_dir='silent-work')
    config.write_text(json.dumps(cfg))
    report = module.package(config)
    assert all(o['audio_unchanged'] == 'source has no audio' for o in report['outputs'])
    cfg.update(output_dir='invalid-out')
    cfg['variants'][0]['video_width'] = 90
    config.write_text(json.dumps(cfg))
    try:
        module.package(config)
        raise AssertionError('Aspect-ratio mismatch accepted')
    except ValueError:
        pass
print('PASS: 2 ratios, audio tail preservation, silent source, no overwrite, aspect-ratio rejection')
