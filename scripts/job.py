"""job.py — 每条素材一个任务文件夹 + 清单，上传/展示/归档只处理清单里的文件。

  group  [输入目录]                 扫描输入，按同名归组，判断竖/方/横，报告缺尺寸/时长不一致/同尺寸重复
  start  <名> <文件...>             把这条素材的文件移到 输入\\_处理中\\<名>\\，写 manifest.json
  collect <任务目录>               naming --apply 之后，把改名文件记进清单
  dupcheck <任务目录> [--drop]      按内容 MD5 + 文件名查 XMP 目标文件夹；--drop 把重复的移到 重复未传\\
  upload <任务目录> [--dry]         只上传清单里的改名文件（调用同目录 upload.py）
  show   <任务目录> [--print]       上传完成后，用用户的默认浏览器打开每个目标文件夹的 XMP 列表页给用户看（不截图）
  finish <任务目录>                 改名文件归档；原片和中间成片进回收站；删掉空任务目录
运行前 export PYTHONIOENCODING=utf-8。
"""
import glob, hashlib, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
UP = HERE
sys.path.insert(0, UP)
ROOT = r'F:\钟海明\素材命名上传'
INBOX = os.path.join(ROOT, '输入')
VIDEO = ('.mp4', '.mov', '.m4v')
NAMED = re.compile(r'^\d{6}-[A-Z]+-[VP]-')
SIZE_SUFFIX = re.compile(r'([_\-\s]*(\d{3,4}[xX×]\d{3,4}|竖|方|横|9[x:]16|1[x:]1|16[x:]9))+$')


def probe(f):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
                        '-of', 'json', f], capture_output=True, text=True, encoding='utf-8')
    j = json.loads(r.stdout); s = j['streams'][0]; w, h = s['width'], s['height']
    size = '方' if abs(w - h) < 0.05 * max(w, h) else ('竖' if h > w else '横')
    return {'w': w, 'h': h, 'sec': round(float(j['format']['duration']), 2), 'size': size}


def stem_of(f):
    s = os.path.splitext(os.path.basename(f))[0]
    return SIZE_SUFFIX.sub('', s) or s


def load(d):
    return json.load(open(os.path.join(d, 'manifest.json'), encoding='utf-8'))


def save(d, m):
    json.dump(m, open(os.path.join(d, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def md5(f):
    h = hashlib.md5()
    with open(f, 'rb') as fp:
        for b in iter(lambda: fp.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def cmd_group(d=INBOX):
    files = [f for f in glob.glob(os.path.join(d, '*')) if f.lower().endswith(VIDEO) and not NAMED.match(os.path.basename(f))]
    groups = {}
    for f in files: groups.setdefault(stem_of(f), []).append(f)
    out = []
    for stem, fs in groups.items():
        info = {f: probe(f) for f in fs}
        by = {}
        for f, i in info.items(): by.setdefault(i['size'], []).append(f)
        issues = [f'同一尺寸「{k}」有 {len(v)} 个文件' for k, v in by.items() if len(v) > 1]
        secs = [i['sec'] for i in info.values()]
        if max(secs) - min(secs) > 0.5: issues.append(f'时长不一致 {secs}')
        for f, i in info.items():
            for k, word in (('竖', '竖'), ('方', '方'), ('横', '横')):
                if word in os.path.basename(f) and i['size'] != k: issues.append(f'文件名写「{word}」但分辨率是 {i["w"]}x{i["h"]}（{i["size"]}）')
        have = sorted(by, key='竖方横'.index)
        route = ('三尺寸齐全：跳过套版，直接命名' if len(have) == 3 else
                 '只有竖版：走套版出方/横' if have == ['竖'] else
                 f'只有 {"/".join(have)}：问用户要不要套版补出 {"/".join(k for k in "竖方横" if k not in have)}')
        out.append({'stem': stem, 'files': {k: v for k, v in by.items()}, 'info': info, 'route': route, 'issues': issues})
        print(f'■ {stem}\n  尺寸: ' + '  '.join(f'{k}={os.path.basename(v[0])}({info[v[0]]["w"]}x{info[v[0]]["h"]},{info[v[0]]["sec"]}s)' for k, v in by.items()))
        print(f'  路线: {route}')
        for x in issues: print(f'  ⚠ {x}')
    return out


def cmd_start(name, files):
    d = os.path.join(INBOX, '_处理中', name)
    if os.path.exists(d): raise SystemExit(f'任务目录已存在: {d}（续做请直接用它）')
    os.makedirs(d)
    src = {}
    for f in files:
        i = probe(f); dst = os.path.join(d, os.path.basename(f))
        shutil.move(f, dst); src[i['size']] = dst
    save(d, {'name': name, 'created': time.strftime('%Y-%m-%d %H:%M'), 'sources': src, 'wrapped': {}, 'named': [], 'dup': []})
    print('任务目录', d); print(json.dumps(src, ensure_ascii=False, indent=1))


def cmd_collect(d):
    m = load(d)
    m['wrapped'] = {k: f for k in ('方', '横') for f in glob.glob(os.path.join(d, f'*_{k}.mp4'))
                    if f not in m['sources'].values()}
    m['named'] = sorted(f for f in glob.glob(os.path.join(d, '*')) if NAMED.match(os.path.basename(f)))
    save(d, m); print(f'清单: 改名文件 {len(m["named"])} 个，套版成片 {list(m["wrapped"])}')
    for f in m['named']: print('  ', os.path.basename(f))


def xmp_list(pg, fid):
    from xmp import API, api_token
    r = pg.request.get(API + '/mediacenter/manage/searchList', headers={'authorization': api_token(pg)},
                       params={'page': 1, 'page_size': 500, 'folder_id': fid, 'show_deep': 0, 'show_stats': 0,
                               'column_list': 'id,name,file_md5', 'is_export': 0, 'media_source': 'local', 'is_global': 0})
    return r.json()['data']['list']


def cmd_dupcheck(d, drop=False):
    from playwright.sync_api import sync_playwright
    from xmp import get_page, logged_in, folder_id
    from upload import target
    m = load(d); dups = []
    with sync_playwright() as p:
        b, pg = get_page(p)
        if not logged_in(pg): raise SystemExit('NOT_LOGGED_IN：python xmp.py login')
        cache = {}
        for f in m['named']:
            path = target(f); fid = folder_id(pg, path)
            if fid not in cache: cache[fid] = xmp_list(pg, fid)
            h = md5(f); stem = os.path.splitext(os.path.basename(f))[0]
            hit = [x for x in cache[fid] if x.get('file_md5') == h or stem in x.get('name', '')]
            if hit:
                why = '同一视频(MD5)' if any(x.get('file_md5') == h for x in hit) else '同名'
                print(f'⚠ 重复[{why}] {path}  {os.path.basename(f)}  ← XMP 已有: {hit[0]["name"]}')
                dups.append(f)
            else:
                print(f'OK  {path}  {os.path.basename(f)}')
        # 素材编号：同一个编号不能被另一条素材（内容部分不同）用过
        from xmp import recent_names
        from naming import MID, content_key, scan_mids, local_names
        pool = recent_names(pg) + local_names()
        clash = 0
        for f in m['named']:
            n = os.path.basename(f); ids = MID.findall(n)
            if not ids: print(f'⚠ 没有新格式素材编号 {{T月日设计师序号}}: {n}'); clash += 1; continue
            md, des, s = ids[0]
            other = scan_mids(n[:2] + md, pool, des).get(int(s), set()) - {content_key(n)}
            if other: print(f'⚠ 编号冲突 {{T{md}{des}{s}}} 的序号 {s} 已被另一条素材用: {sorted(other)[0]}'); clash += 1
        if clash: sys.exit(4)
    if drop and dups:
        dd = os.path.join(d, '重复未传'); os.makedirs(dd, exist_ok=True)
        for f in dups: shutil.move(f, os.path.join(dd, os.path.basename(f)))
        m['named'] = [f for f in m['named'] if f not in dups]; m['dup'] += [os.path.join(dd, os.path.basename(f)) for f in dups]
        save(d, m); print(f'已移出 {len(dups)} 个重复文件到 {dd}')
    print(f'重复 {len(dups)} / {len(m["named"]) + (len(dups) if drop else 0)}')
    if dups and not drop: sys.exit(3)


def cmd_upload(d, dry=False):
    m = load(d)
    if not m['named']: raise SystemExit('清单里没有要上传的文件')
    r = subprocess.run([sys.executable, os.path.join(UP, 'upload.py'), *m['named']] + (['--dry'] if dry else []))
    sys.exit(r.returncode)


def cmd_show(d, dry=False):
    from upload import target
    m = load(d)
    folders = sorted({target(f) for f in m['named']})
    subprocess.run([sys.executable, os.path.join(UP, 'xmp.py'), 'show', *folders] + (['--print'] if dry else []))


def cmd_finish(d):
    from archive import week_dir, recycle
    m = load(d); dst = week_dir(); os.makedirs(dst, exist_ok=True)
    for f in m['named']:
        t = os.path.join(dst, os.path.basename(f))
        if os.path.exists(t): raise SystemExit(f'归档里已有同名文件: {t}')
    for f in m['named']:
        shutil.move(f, os.path.join(dst, os.path.basename(f))); print('归档', os.path.basename(f))
    for f in list(m['sources'].values()) + list(m['wrapped'].values()) + m.get('dup', []):
        if os.path.exists(f): recycle(f); print('回收站', os.path.basename(f))
    for x in glob.glob(os.path.join(d, '重复未传')):
        if not os.listdir(x): os.rmdir(x)
    left = [x for x in os.listdir(d) if x != 'manifest.json']
    if left: print('⚠ 任务目录还有文件，未删除:', left)
    else:
        shutil.rmtree(d); print('任务目录已清理', d)
        parent = os.path.dirname(os.path.normpath(d))
        if os.path.basename(parent) == '_处理中' and not os.listdir(parent):
            os.rmdir(parent); print('_处理中 已空，已删除')
    print('归档目录', dst)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit()
    c, rest = a[0], [x for x in a[1:] if not x.startswith('--')]
    if c == 'group': cmd_group(*(rest or [INBOX]))
    elif c == 'start': cmd_start(rest[0], rest[1:])
    elif c == 'collect': cmd_collect(rest[0])
    elif c == 'dupcheck': cmd_dupcheck(rest[0], '--drop' in a)
    elif c == 'upload': cmd_upload(rest[0], '--dry' in a)
    elif c == 'show': cmd_show(rest[0], '--print' in a)
    elif c == 'finish': cmd_finish(rest[0])
    else: print(__doc__)
