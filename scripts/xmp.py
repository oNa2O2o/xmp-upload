"""XMP helper: drive a dedicated Chrome (profile F:\\钟海明\\素材命名上传\\.xmp_profile, CDP 9333).
Default is headless (no window, doesn't disturb the user). `python xmp.py login` restarts it with a window for re-login.
CLI: python xmp.py check | login | headless | folders | id <JP/Facebook/男性向> | ls <JP/Facebook/男性向> | open <path>
     | show <JP/Facebook/男性向> [...] [--print]   用户自己的默认浏览器打开这些文件夹的素材列表（上传完成后给用户看）"""
import sys, json, time, os, re, subprocess, urllib.request
from playwright.sync_api import sync_playwright

CDP = 'http://127.0.0.1:9333'
LIB = 'MiraiMind素材库'
BASE = 'https://xmp.mobvista.com'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PROFILE = r'F:\钟海明\素材命名上传\.xmp_profile'
ID_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'folder_ids.json')
NODES_JS = """() => [...document.querySelectorAll('.virtual-tree-node')].map((n,i)=>({i, pad: parseInt(n.style.paddingLeft)||0, top: parseFloat(n.style.top)||0,
  title: (n.querySelector('span[title]')||{}).title, leaf: !!n.querySelector('.arrow.no-child'),
  open: ((n.querySelector('.arrow i')||{}).className||'').includes('expend')}))"""


def cdp_up():
    try:
        urllib.request.urlopen(CDP + '/json/version', timeout=2); return True
    except Exception:
        return False


def kill_xmp_chrome():
    """Only kills the dedicated Chrome using .xmp_profile — never the user's normal Chrome."""
    subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                    "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*xmp_profile*' } "
                    "| ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }"], capture_output=True)
    for _ in range(20):
        if not cdp_up(): break
        time.sleep(0.5)
    time.sleep(1.5)


def start_chrome(headless=True):
    args = [CHROME, '--remote-debugging-port=9333', f'--user-data-dir={PROFILE}', '--no-first-run', '--window-size=1600,1000']
    if headless: args.insert(1, '--headless=new')
    subprocess.Popen(args + [BASE + '/creative/manage'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
    for _ in range(40):
        time.sleep(0.5)
        if cdp_up(): time.sleep(2); return
    raise SystemExit('Chrome CDP 9333 启动失败')


def ensure_chrome():
    if not cdp_up(): start_chrome(headless=True)


def get_page(p):
    ensure_chrome()
    b = p.chromium.connect_over_cdp(CDP)
    pages = [x for c in b.contexts for x in c.pages if 'xmp.mobvista.com' in x.url]
    pg = pages[0] if pages else b.contexts[0].new_page()
    return b, pg


def clean(pg):
    pg.evaluate("""document.querySelectorAll('.driver-overlay,.driver-popover').forEach(e=>e.remove());
      document.body.classList.remove('driver-active');""")


def nodes(pg):
    ns = pg.evaluate(NODES_JS); ns.sort(key=lambda n: n['top']); return ns


def logged_in(pg):
    if '/creative/manage' not in pg.url:
        pg.goto(BASE + '/creative/manage')
    for _ in range(15):
        pg.wait_for_timeout(1000)
        if LIB in pg.evaluate('()=>document.body.innerText'): return True
    return False


def open_folder(pg, path):
    """path like 'JP/Facebook/男性向' under LIB. Expands virtual tree, clicks last title, verifies breadcrumb."""
    if '/creative/manage' not in pg.url:
        pg.goto(BASE + '/creative/manage'); pg.wait_for_timeout(4000)
    clean(pg)
    parts = [LIB] + path.strip('/').split('/')
    parent_pad = -1; parent_top = -1
    for k, name in enumerate(parts):
        node = None
        for n in nodes(pg):
            if n['top'] > parent_top and n['pad'] > parent_pad and n['title'] == name:
                node = n; break
            if parent_pad >= 0 and n['top'] > parent_top and n['pad'] <= parent_pad:
                break
        if node is None:
            raise SystemExit(f'folder not found in tree: {name} (path {path})')
        el = pg.locator('.virtual-tree-node').nth(node['i'])
        el.scroll_into_view_if_needed()
        if k == len(parts) - 1:
            el.locator('span[title]').click(); pg.wait_for_timeout(2500)
        elif not node['open'] and not node['leaf']:
            el.locator('.arrow').click(); pg.wait_for_timeout(1500)
        node = [n for n in nodes(pg) if n['title'] == name and abs(n['top'] - node['top']) < 1][0]
        parent_pad, parent_top = node['pad'], node['top']
    clean(pg)
    t = pg.evaluate('()=>document.body.innerText')
    m = re.search(r'企业素材库\s*/\s*' + LIB + r'((?:\s*/\s*[^\s/]+)+)', t)
    crumb = '/'.join(x.strip() for x in m.group(1).split('/') if x.strip()) if m else ''
    if crumb.split('/')[-len(parts) + 1:] != parts[1:]:
        raise SystemExit(f'面包屑不对: 想打开 {path}，实际 {crumb}')
    return crumb


def load_ids():
    try:
        with open(ID_CACHE, encoding='utf-8') as fh: return json.load(fh)
    except Exception:
        return {}


API = 'https://xmp-api.mobvista.com'
_TOKEN = {}


def api_token(pg):
    """Bearer token sniffed from the page's own API request (plain fetch gets 401)."""
    if 'v' not in _TOKEN:
        t = pg.context.new_page()
        try:
            with t.expect_request(lambda r: API in r.url and 'authorization' in r.headers, timeout=30000) as ri:
                t.goto(BASE + '/creative/manage')
            _TOKEN['v'] = ri.value.headers['authorization']
        finally:
            t.close()
    return _TOKEN['v']


def folder_map(pg):
    """{'JP/Facebook/男性向': 'company_…', …} for everything under LIB, via API; saved to folder_ids.json."""
    r = pg.request.post(API + '/material_center/folder/config', data={'zone': 'company'}, headers={'authorization': api_token(pg)})
    data = r.json()['data']
    out = {}
    def walk(n, path):
        if path: out[path] = n['id']
        for c in n.get('children') or []: walk(c, (path + '/' if path else '') + c['name'])
    walk([n for n in data if n['name'] == LIB][0], '')
    with open(ID_CACHE, 'w', encoding='utf-8') as fh: json.dump(out, fh, ensure_ascii=False, indent=1)
    return out


def folder_id(pg, path):
    ids = load_ids()
    if path not in ids: ids = folder_map(pg)
    if path not in ids: raise SystemExit(f'XMP 里没有文件夹: {LIB}/{path}')
    return ids[path]


def list_names(pg, fid, n=100):
    r = pg.request.get(API + '/mediacenter/manage/searchList', headers={'authorization': api_token(pg)},
                       params={'page': 1, 'page_size': n, 'folder_id': fid, 'show_deep': 0, 'show_stats': 0,
                               'column_list': 'id,name', 'is_export': 0, 'media_source': 'local', 'is_global': 0})
    return [x['name'] for x in r.json()['data']['list']]


ROOT_FOLDER = 'company_111496979'   # MiraiMind素材库


def recent_names(pg, n=2000):
    """MiraiMind素材库全部子文件夹里最新的 n 个素材名（接口按上传时间倒序；keyword 参数会被忽略）。"""
    tok, out = api_token(pg), []
    for page in range(1, n // 500 + 1):
        r = pg.request.get(API + '/mediacenter/manage/searchList', headers={'authorization': tok},
                           params={'page': page, 'page_size': 500, 'folder_id': ROOT_FOLDER, 'show_deep': 1, 'show_stats': 0,
                                   'column_list': 'id,name', 'is_export': 0, 'media_source': 'local', 'is_global': 0})
        lst = r.json()['data']['list']; out += [x['name'] for x in lst]
        if len(lst) < 500: break
    return out


def next_seq(pg, date6, designer='ZHM'):
    """该设计师当天的下一个素材序号：XMP 最新 2000 条 + 本地 已上传/输入（新旧编号格式都算）。"""
    from naming import scan_mids, local_names
    used = scan_mids(date6, recent_names(pg) + local_names(), designer)
    return (max(used) + 1 if used else 1), used


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'login':
        kill_xmp_chrome(); start_chrome(headless=False)
        print('已打开带窗口的 XMP Chrome，请登录；登录后运行 python xmp.py headless 切回后台')
        sys.exit()
    if cmd == 'headless':
        kill_xmp_chrome(); start_chrome(headless=True); cmd = 'check'
    if cmd == 'show':
        ids = load_ids()
        for path in [a for a in sys.argv[2:] if not a.startswith('--')]:
            if path not in ids: raise SystemExit(f'folder_ids.json 里没有 {path}，先跑 python xmp.py folders')
            url = f'{BASE}/creative/manage?folder_id={ids[path]}'
            print(path, url)
            if '--print' not in sys.argv: os.startfile(url)
        sys.exit()
    with sync_playwright() as p:
        b, pg = get_page(p)
        if cmd == 'check':
            print('LOGGED_IN' if logged_in(pg) else 'NOT_LOGGED_IN')
        elif cmd == 'open':
            print(open_folder(pg, sys.argv[2]))
        elif cmd == 'id':
            print(folder_id(pg, sys.argv[2]))
        elif cmd == 'seq':
            import datetime
            d6 = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().strftime('%y%m%d')
            n, used = next_seq(pg, d6, sys.argv[3] if len(sys.argv) > 3 else 'ZHM')
            for s, keys in sorted(used.items()): print(f'已用 {s}:', *keys, sep='\n   ')
            print('NEXT', n)
        elif cmd == 'folders':
            for k, v in folder_map(pg).items(): print(k, v)
        elif cmd == 'ls':
            print('\n'.join(list_names(pg, folder_id(pg, sys.argv[2]))))
