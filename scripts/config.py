"""个人配置：每个使用者一份 config.json（放在 skill 根目录，不进 git），其余脚本都从这里取路径和设计师代号。

python config.py check                     已配置 → 打印 OK + 配置；未配置 → 打印 NEED_SETUP 并退出码 10（首次使用要先问设计师姓名）
python config.py setup --name <姓名> [--code <代号>] [--root <工作目录>] [--chrome <chrome.exe>]
                                           按命名台花名册把姓名换成代号；建 输入/已上传/套版 目录；复制命名台；检查依赖
python config.py show                      打印当前配置
"""
import json, os, re, shutil, subprocess, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(SKILL, 'config.json')
BUNDLED_HTML = os.path.join(SKILL, 'assets', '素材命名台.html')
CHROME_CANDIDATES = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
]


def _read():
    if not os.path.exists(CFG_PATH): return None
    with open(CFG_PATH, encoding='utf-8') as fh: return json.load(fh)


def load():
    c = _read()
    if not c:
        sys.exit('NEED_SETUP：还没配置。首次使用先问用户设计师姓名，再跑 python scripts/config.py setup --name <姓名>')
    return c


def html_path(root=None):
    """命名规则源：优先工作目录里的 素材命名台.html（可单独更新），没有就用 skill 自带的。"""
    root = root or (_read() or {}).get('root')
    p = os.path.join(root, '素材命名台.html') if root else ''
    return p if p and os.path.exists(p) else BUNDLED_HTML


def load_D(path=None):
    with open(path or html_path(), encoding='utf-8') as fh:
        for line in fh:
            s = line.strip()
            if s.startswith('const D = '):
                return json.loads(s[len('const D = '):].rstrip(';'))
    sys.exit('素材命名台.html 里找不到 const D')


def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p): return p
    return shutil.which('chrome') or shutil.which('chrome.exe') or ''


def deps():
    miss = []
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool): miss.append(f'{tool}（装 ffmpeg 并加入 PATH，例：winget install Gyan.FFmpeg）')
    for mod, pkg in (('playwright', 'playwright'), ('PIL', 'pillow'), ('numpy', 'numpy')):
        try: __import__(mod)
        except ImportError: miss.append(f'python 包 {pkg}（pip install {pkg}）')
    return miss


def setup(name, code=None, root=None, chrome=None):
    D = load_D(BUNDLED_HTML)
    roster = {r['name']: r['code'] for r in D['roster']}
    code = (code or roster.get(name) or '').upper()
    if not code:
        sys.exit(f'NEED_CODE：花名册里没有「{name}」，问用户的设计师代号（2–4 个大写字母，一般是姓名拼音首字母），'
                 f'再加 --code 重跑。花名册：{"、".join(f"{k}={v}" for k, v in roster.items())}')
    if not re.fullmatch(r'[A-Z]{2,4}', code) or code in D['blacklist']:
        sys.exit(f'设计师代号非法：{code}（2–4 个大写字母，且不能是 {",".join(D["blacklist"])}）')
    if code in roster.values() and roster.get(name) != code:
        print(f'⚠ 代号 {code} 在花名册里属于别人，确认没撞再用')
    if not root:
        root = os.path.join(f'F:\\{name}' if os.path.isdir('F:\\') else os.path.expanduser('~'), '素材命名上传')
    root = os.path.abspath(root)
    for d in ('输入', '已上传', '套版'): os.makedirs(os.path.join(root, d), exist_ok=True)
    dst = os.path.join(root, '素材命名台.html')
    if not os.path.exists(dst): shutil.copy2(BUNDLED_HTML, dst)
    chrome = chrome or find_chrome()
    c = {'designer_name': name, 'designer': code, 'root': root, 'chrome': chrome,
         'profile': os.path.join(root, '.xmp_profile'), 'cdp_port': 9333}
    with open(CFG_PATH, 'w', encoding='utf-8') as fh: json.dump(c, fh, ensure_ascii=False, indent=2)
    print('SETUP_OK'); show(c)
    if not chrome: print('⚠ 没找到 Chrome，装好后用 --chrome <chrome.exe 路径> 重跑 setup')
    m = deps()
    if m: print('⚠ 缺依赖：\n  ' + '\n  '.join(m))
    else: print('依赖齐全')
    print('下一步：python scripts/xmp.py check（NOT_LOGGED_IN 就 xmp.py login 让用户登录 XMP，登录完 xmp.py headless）')


def show(c=None):
    c = c or load()
    for k, v in c.items(): print(f'{k}: {v}')
    print(f'命名台: {html_path(c["root"])}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    a = sys.argv[1:]
    cmd = a[0] if a else 'check'
    if cmd == 'check':
        c = _read()
        if not c: print('NEED_SETUP'); sys.exit(10)
        print('OK'); show(c)
        m = deps()
        if m: print('⚠ 缺依赖：\n  ' + '\n  '.join(m))
    elif cmd == 'show':
        show()
    elif cmd == 'setup':
        import argparse
        ap = argparse.ArgumentParser(prog='config.py setup')
        ap.add_argument('--name', required=True); ap.add_argument('--code'); ap.add_argument('--root'); ap.add_argument('--chrome')
        x = ap.parse_args(a[1:])
        setup(x.name, x.code, x.root, x.chrome)
    else:
        sys.exit(__doc__)
