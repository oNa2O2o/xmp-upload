"""素材命名：规则全部实时读取自 F:\\钟海明\\素材命名上传\\素材命名台.html 里的 `const D = {...}`。

用法（Python 打印中文需 PYTHONIOENCODING=utf-8）:
  python naming.py rules                         # 打印板式/勾子/类型等可选值
  python naming.py probe <视频>                   # 时长档位 + 尺寸
  python naming.py tags <地区> <关键词...>         # 按中文/日文关键词搜标签 id
  python naming.py build <视频> --region JP --type 原创 --gender 男性向 --layout 气泡对话 \
      --hook D --style 二次元 --title 深夜被女警官拦车 --tags 159,46,414 \
      --seq 1 --channels FB,GG,TT [--designer ZHM] [--version 1] [--date 261019] [--duration 40秒] [--size 竖] [--apply]
  不加 --apply 只预览命名；加 --apply 才在 输入 文件夹里按渠道复制出改名文件（原视频保留）。
  --seq = 素材编号里的序号：当天全组所有素材合在一起数（不分设计师、不分面向）。
          默认值用 `python xmp.py seq [YYMMDD]` 查（XMP + 本地归档里当天已用的最大序号 + 1）。
  python naming.py mids <YYMMDD> <文件夹...>      # 列出文件名里当天已用的素材编号
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys

ROOT = r'F:\钟海明\素材命名上传'
HTML = os.path.join(ROOT, '素材命名台.html')
STYLES = ['二次元', '真人']          # 用户规定：画风只分二次元/真人（命名台里的 男01 写法不用）
DUR_SECS = {'6秒': 6, '15秒': 15, '30秒': 30, '40秒': 40}
BAD = re.compile(r'[-｜|【】,，\s{}]')
GENDER_CODE = {'男性向': 'M', '女性向': 'F', '全性向': 'A'}   # 用户规定全性向用 A（网页命名台只写了 M/F）
MID = re.compile(r'\{material(\d{8})([MFA])([A-Z]{2,4})(\d+)\}')


def material_id(date6, gender, designer, seq):
    return f'{{material20{date6}{GENDER_CODE[gender]}{designer}{int(seq)}}}'   # 日期故意写 8 位


def content_key(name):
    """同一条素材的不同尺寸/渠道/版本，这部分相同（从开头截到标签【】为止）。"""
    m = re.search(r'^(.*?【[^】]*】)', name)
    return m.group(1) if m else name


def scan_mids(date6, names):
    """返回 {序号: set(content_key)}，只算该日期的编号。"""
    out = {}
    for n in names:
        for d8, g, des, s in MID.findall(n):
            if d8 == '20' + date6: out.setdefault(int(s), set()).add(content_key(n))
    return out


def local_names():
    names = []
    for base in (os.path.join(ROOT, '已上传'), os.path.join(ROOT, '输入')):
        for dp, _, fs in os.walk(base): names += fs
    return names


def load_D():
    with open(HTML, encoding='utf-8') as fh:
        for line in fh:
            s = line.strip()
            if s.startswith('const D = '):
                return json.loads(s[len('const D = '):].rstrip(';'))
    sys.exit('素材命名台.html 里找不到 const D')


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=width,height:format=duration', '-of', 'json', path],
                         capture_output=True, text=True, encoding='utf-8').stdout
    j = json.loads(out)
    w, h = j['streams'][0]['width'], j['streams'][0]['height']
    sec = float(j['format']['duration'])
    dur = min(DUR_SECS, key=lambda k: abs(DUR_SECS[k] - sec))
    size = '竖' if h > w else '横' if w > h else '方'
    return {'w': w, 'h': h, 'sec': round(sec, 2), 'duration': dur, 'size': size}


def codes(lst):
    return [x['code'] if isinstance(x, dict) else x for x in lst]


def hook_full(D, h):
    for x in D['hooks']:
        full = x['code'] + x['name']
        if h.upper() == x['code'] or h in (full, x['name']):
            return full
    sys.exit(f'勾子不认识: {h}；可选 {[x["code"] + x["name"] for x in D["hooks"]]}')


def genders(D):
    # 命名台只有男/女性向；XMP 有全性向文件夹，用户规定全性向编号字母 A，板式取男女并集
    return list(D['genders']) + [g for g in GENDER_CODE if g not in D['genders']]


def layouts(D, gender):
    if gender not in D['layouts']:
        return list(dict.fromkeys(x for g in D['genders'] for x in layouts(D, g)))
    v = D['layouts'][gender]
    return v if isinstance(v, list) else list(v)


def build(D, a, info):
    errs = []
    if a.region not in codes(D['regions']): errs.append(f'地区 {a.region} 不在 {codes(D["regions"])}')
    if a.type not in D['mtypes']: errs.append(f'素材类型 {a.type} 不在 {D["mtypes"]}')
    if a.gender not in genders(D): errs.append(f'面向 {a.gender} 不在 {genders(D)}')
    elif a.layout not in layouts(D, a.gender): errs.append(f'板式 {a.layout} 不在 {layouts(D, a.gender)}')
    if a.style not in STYLES: errs.append(f'画风只能是 {STYLES}')
    if not 6 <= len(a.title) <= 10 or BAD.search(a.title): errs.append(f'短标题需 6–10 字且不含 - ｜ | 【】 逗号 空格: {a.title}')
    ids = [int(x) for x in re.split(r'[,，\s]+', a.tags.strip()) if x]
    valid = {t['id']: t for t in D['tags'].get(a.region, [])}
    if not 1 <= len(ids) <= 5: errs.append('标签需 1–5 个')
    for i in ids:
        if i not in valid: errs.append(f'标签 {i} 不在 {a.region} 标签表')
    chans = [c.strip().upper() for c in a.channels.split(',') if c.strip()]
    for c in chans:
        if c not in codes(D['channels']): errs.append(f'渠道 {c} 不在 {codes(D["channels"])}')
    if not re.fullmatch(r'[A-Z]{2,4}', a.designer) or a.designer in D['blacklist']: errs.append(f'设计师代号非法: {a.designer}')
    if a.seq is None or a.seq < 1: errs.append('素材编号序号 --seq 必填，1 以上整数（当天全组第几条，用 xmp.py seq 查默认值）')
    if a.gender not in GENDER_CODE: errs.append(f'面向 {a.gender} 没有编号字母')
    dur = a.duration or info['duration']
    size = a.size or info['size']
    if errs:
        sys.exit('命名校验失败:\n- ' + '\n- '.join(errs))
    hook = hook_full(D, a.hook)
    mat = material_id(a.date, a.gender, a.designer, a.seq)
    mid = '｜'.join([dur, a.layout, hook, a.style, a.title, '【' + ','.join(map(str, ids)) + '】', mat]) + '｜'
    names = []
    for c in chans:
        names.append((c, '-'.join([a.date, a.region, 'V', a.type, a.gender, mid, c, a.designer, size, str(a.version)])))
    return names, [(i, valid[i].get('g') or valid[i].get('n')) for i in ids]


def main():
    D = load_D()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'rules':
        print('构建于', D['builtAt'], '标签抓取', D['tagsFetchedAt'])
        for k in ['regions', 'mtypes', 'genders', 'durations', 'hooks', 'channels', 'sizes']: print(k, D[k])
        for g in genders(D): print('板式', g, layouts(D, g))
        print('画风', STYLES); print('设计师', D['roster'])
    elif cmd == 'probe':
        print(json.dumps(probe(sys.argv[2]), ensure_ascii=False))
    elif cmd == 'tags':
        region, kws = sys.argv[2], sys.argv[3:]
        for t in D['tags'][region]:
            hay = ' '.join([str(t.get(k, '')) for k in ('n', 'g', 'k', 'jg')] + list(t.get('kw', [])))
            if any(k in hay for k in kws):
                print(t['id'], t.get('n'), '/', t.get('g'), '| kw:', ','.join(t.get('kw', [])[:6]), '| 消耗', t.get('em'))
    elif cmd == 'mids':
        date6, dirs = sys.argv[2], sys.argv[3:]
        names = local_names() if not dirs else [f for d in dirs for _, _, fs in os.walk(d) for f in fs]
        for s, keys in sorted(scan_mids(date6, names).items()):
            print(s, *keys, sep='\n   ')
    elif cmd == 'build':
        ap = argparse.ArgumentParser()
        ap.add_argument('video'); ap.add_argument('--region', required=True); ap.add_argument('--type', required=True)
        ap.add_argument('--gender', required=True); ap.add_argument('--layout', required=True); ap.add_argument('--hook', required=True)
        ap.add_argument('--style', required=True); ap.add_argument('--title', required=True); ap.add_argument('--tags', required=True)
        ap.add_argument('--channels', required=True); ap.add_argument('--designer', default='ZHM'); ap.add_argument('--version', type=int, default=1)
        ap.add_argument('--seq', type=int)
        ap.add_argument('--date', default=datetime.date.today().strftime('%y%m%d'))
        ap.add_argument('--duration'); ap.add_argument('--size'); ap.add_argument('--apply', action='store_true')
        a = ap.parse_args(sys.argv[2:])
        info = probe(a.video)
        names, tagnames = build(D, a, info)
        print('视频:', info); print('标签:', tagnames); print('素材编号:', material_id(a.date, a.gender, a.designer, a.seq))
        used = scan_mids(a.date, local_names()).get(a.seq, set()) - {content_key(names[0][1])}
        if used:
            print(f'⚠ 序号 {a.seq} 本地已被另一条素材用过: {used}')
            if a.apply: sys.exit('序号冲突，未改名；用 xmp.py seq 重查')
        ext = os.path.splitext(a.video)[1]
        for c, n in names:
            print(f'[{c}] {n}{ext}')
            if a.apply:
                dst = os.path.join(os.path.dirname(os.path.abspath(a.video)), n + ext)
                if os.path.exists(dst): sys.exit(f'已存在，换版本号: {dst}')
                shutil.copy2(a.video, dst)
        if a.apply: print('已复制到', os.path.dirname(os.path.abspath(a.video)))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
