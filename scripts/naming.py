"""素材命名：规则全部实时读取自 F:\\钟海明\\素材命名上传\\素材命名台.html 里的 `const D = {...}`。

2026-10-22 新规则（素材命名台_20261022_T编号_保留画风）：
  视频 V: 日期-地区-V-类型-面向-时长｜画风｜【标签】｜{T月日设计师序号}｜-渠道-设计师-尺寸-版本
  图片 P: 日期-地区-P-类型-面向-画风｜【标签】｜{T月日AI序号}｜-GG-AI-尺寸-版本   （图片渠道固定 GG、设计师固定 AI）
  板式 / 勾子 / 短标题 已删除。画风 真人/2D/3D（「二次元」自动转 2D；用户规定无角色素材可写「无」）。
  例：261021-JP-V-原创-男性向-30秒｜2D｜【562,247,493,456】｜{T1021ZHM1}｜-FB-ZHM-竖-1.mp4

用法（Python 打印中文需 PYTHONIOENCODING=utf-8）:
  python naming.py rules                         # 打印类型/画风/渠道等可选值
  python naming.py probe <视频>                   # 时长档位 + 尺寸
  python naming.py tags <地区> <关键词...>         # 按中文/日文关键词搜标签 id
  python naming.py build <视频> --region JP --type 原创 --gender 男性向 --style 2D --tags 159,46,414
      --seq 1 --channels FB,GG,TT [--form V] [--designer ZHM] [--version 1] [--date 261019] [--duration 40秒] [--size 竖] [--apply]
  不加 --apply 只预览命名；加 --apply 才在原文件所在文件夹里按渠道复制出改名文件（原文件保留）。
  --seq = 素材编号里的序号：该设计师当天第几条素材（10-22 起编号带设计师代码，同事实际也按人各自从 1 数）。
          默认值用 `python xmp.py seq [YYMMDD] [设计师]` 查（XMP + 本地里该设计师当天已用最大序号 + 1，新旧编号格式都算）。
          已经用过的序号不改。
  python naming.py mids <YYMMDD> <文件夹...>      # 列出文件名里当天已用的素材编号
  python naming.py convert <旧文件名>             # 旧规则文件名 -> 新规则文件名（批量改名用，见 rename_v3.py）
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys

ROOT = r'F:\钟海明\素材命名上传'
HTML = os.path.join(ROOT, '素材命名台.html')
STYLES = ['真人', '2D', '3D', '无']   # 命名台 artstyles + 用户规定的「无」（如欲求金字塔这类无角色素材）
STYLE_ALIAS = {'二次元': '2D', '二维': '2D', '2d': '2D', '三维': '3D', '3d': '3D', '真人风格': '真人', '写实真人': '真人'}
DUR_SECS = {'6秒': 6, '15秒': 15, '30秒': 30, '40秒': 40}
GENDERS_EXTRA = ['全性向']            # 命名台只有男/女性向；XMP 有全性向文件夹，用户确认继续支持
MID_OLD = re.compile(r'\{material20(\d{6})[MFA]([A-Z]{2,4})(\d+)\}')   # 10-22 前旧格式，只用于识别
MID = re.compile(r'\{T(\d{4})([A-Z]{2,4})(\d+)\}')                    # 新格式 {T + 月日4位 + 设计师 + 序号}


def material_id(date6, designer, seq):
    return f'{{T{date6[2:]}{designer}{int(seq)}}}'


def parse_mids(name):
    """文件名里的素材编号 -> [(月日4位, 设计师, 序号int)]，新旧格式都认。"""
    out = [(d[2:], des, int(s)) for d, des, s in MID_OLD.findall(name)]
    return out + [(d, des, int(s)) for d, des, s in MID.findall(name)]


def content_key(name):
    """同一条素材的不同尺寸/渠道/版本，这部分相同（从开头截到标签【】为止）。"""
    m = re.search(r'^(.*?【[^】]*】)', name)
    return m.group(1) if m else name


def scan_mids(date6, names, designer=None):
    """返回 {序号: set(content_key)}，只算该日期（且该设计师，若给了 designer）的编号。"""
    out = {}
    for n in names:
        for md, des, s in parse_mids(n):
            if md == date6[2:] and (designer is None or des == designer): out.setdefault(s, set()).add(content_key(n))
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
    sec = float(j['format'].get('duration') or 0)
    dur = min(DUR_SECS, key=lambda k: abs(DUR_SECS[k] - sec))
    size = '竖' if h > w else '横' if w > h else '方'
    return {'w': w, 'h': h, 'sec': round(sec, 2), 'duration': dur, 'size': size}


def codes(lst):
    return [x['code'] if isinstance(x, dict) else x for x in lst]


def genders(D):
    return list(D['genders']) + [g for g in GENDERS_EXTRA if g not in D['genders']]


def build(D, a, info):
    errs = []
    a.form = a.form.upper()
    a.style = STYLE_ALIAS.get(a.style, a.style)
    if a.form == 'P': a.channels, a.designer = 'GG', 'AI'   # 命名台规定：图片渠道固定 GG、设计师固定 AI
    if a.form not in ('V', 'P'): errs.append('--form 只能是 V(视频) 或 P(图片)')
    if a.region not in codes(D['regions']): errs.append(f'地区 {a.region} 不在 {codes(D["regions"])}')
    if a.type not in D['mtypes']: errs.append(f'素材类型 {a.type} 不在 {D["mtypes"]}')
    if a.gender not in genders(D): errs.append(f'面向 {a.gender} 不在 {genders(D)}')
    if a.style not in STYLES: errs.append(f'画风只能是 {STYLES}')
    ids = [int(x) for x in re.split(r'[,，\s]+', a.tags.strip()) if x]
    valid = {t['id']: t for t in D['tags'].get(a.region, [])}
    if not 1 <= len(ids) <= 5: errs.append('标签需 1–5 个')
    for i in ids:
        if i not in valid: errs.append(f'标签 {i} 不在 {a.region} 标签表')
    chans = [c.strip().upper() for c in a.channels.split(',') if c.strip()]
    for c in chans:
        if c not in codes(D['channels']): errs.append(f'渠道 {c} 不在 {codes(D["channels"])}')
    if not re.fullmatch(r'[A-Z]{2,4}', a.designer) or (a.designer in D['blacklist'] and a.designer != 'AI'):
        errs.append(f'设计师代号非法: {a.designer}')
    if a.seq is None or a.seq < 1: errs.append('素材编号序号 --seq 必填，1 以上整数（当天全组第几条，用 xmp.py seq 查默认值）')
    dur = a.duration or info['duration']
    size = a.size or info['size']
    if errs:
        sys.exit('命名校验失败:\n- ' + '\n- '.join(errs))
    parts = ([] if a.form == 'P' else [dur]) + [a.style, '【' + ','.join(map(str, ids)) + '】', material_id(a.date, a.designer, a.seq)]
    mid = '｜'.join(parts) + '｜'
    names = [(c, '-'.join([a.date, a.region, a.form, a.type, a.gender, mid, c, a.designer, size, str(a.version)])) for c in chans]
    return names, [(i, valid[i].get('g') or valid[i].get('n')) for i in ids]


OLD_NAME = re.compile(r'^(\d{6}-[A-Z]+-V-[^-]+-[^-]+-)(\d+秒)｜[^｜]*｜[^｜]*｜([^｜]*)｜[^｜]*｜(【[^】]*】)(?:｜\{material20\d{6}[MFA]([A-Z]{2,4})(\d+)\})?｜?(-.*)$')


def convert(name, fill=None):
    """旧规则文件名 -> 新规则。fill=(月日4位, 设计师, 序号) 给没有编号的旧文件补编号。"""
    m = OLD_NAME.match(name)
    if not m: return None
    head, dur, style, tags, des, seq, tail = m.groups()
    style = STYLE_ALIAS.get(style, style)
    if style not in STYLES: raise SystemExit(f'画风 {style} 不在 {STYLES}: {name}')
    if seq: mid = '{T%s%s%s}' % (re.search(r'material20\d\d(\d{4})', name).group(1), des, seq)
    elif fill: mid = '{T%s%s%s}' % fill
    else: raise SystemExit(f'旧文件没有素材编号，需要 fill: {name}')
    return f'{head}{dur}｜{style}｜{tags}｜{mid}｜{tail}'


def main():
    D = load_D()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'rules':
        print('构建于', D['builtAt'], '标签抓取', D.get('tagsFetchedAt'))
        for k in ['regions', 'forms', 'mtypes', 'durations', 'channels', 'sizes']: print(k, D.get(k))
        print('面向', genders(D)); print('画风', STYLES, '别名', STYLE_ALIAS); print('设计师', D['roster'], '+ AI（图片）')
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
    elif cmd == 'convert':
        print(convert(sys.argv[2]))
    elif cmd == 'build':
        ap = argparse.ArgumentParser()
        ap.add_argument('video'); ap.add_argument('--region', required=True); ap.add_argument('--type', required=True)
        ap.add_argument('--gender', required=True); ap.add_argument('--form', default='V')
        ap.add_argument('--style', required=True); ap.add_argument('--tags', required=True)
        ap.add_argument('--channels', default='GG'); ap.add_argument('--designer', default='ZHM'); ap.add_argument('--version', type=int, default=1)
        ap.add_argument('--seq', type=int)
        ap.add_argument('--date', default=datetime.date.today().strftime('%y%m%d'))
        ap.add_argument('--duration'); ap.add_argument('--size'); ap.add_argument('--apply', action='store_true')
        a = ap.parse_args(sys.argv[2:])
        info = probe(a.video)
        names, tagnames = build(D, a, info)
        print('文件:', info); print('标签:', tagnames); print('素材编号:', material_id(a.date, a.designer, a.seq))
        used = scan_mids(a.date, local_names(), a.designer).get(a.seq, set()) - {content_key(names[0][1])}
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
