"""archive.py <原视频> <已上传成功的改名文件...>
把改名文件移到 已上传\\<本周一YYMMDD>-<本周日YYMMDD>\\，原视频送回收站。"""
import datetime, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

ROOT = config.load()['root']


def week_dir(d=None):
    d = d or datetime.date.today()
    mon = d - datetime.timedelta(days=d.weekday())
    sun = mon + datetime.timedelta(days=6)
    return os.path.join(ROOT, '已上传', f'{mon:%y%m%d}-{sun:%y%m%d}')


def recycle(path):
    p = os.path.abspath(path).replace("'", "''")
    subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                    "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("
                    f"'{p}','OnlyErrorDialogs','SendToRecycleBin')"], check=True)


if __name__ == '__main__':
    orig, files = sys.argv[1], sys.argv[2:]
    dst = week_dir(); os.makedirs(dst, exist_ok=True)
    for f in files:
        target = os.path.join(dst, os.path.basename(f))
        if os.path.exists(target): sys.exit(f'归档里已有同名文件: {target}')
        shutil.move(f, target); print('归档', target)
    if os.path.exists(orig) and os.path.abspath(orig) not in map(os.path.abspath, files):
        recycle(orig); print('原视频已进回收站', orig)
