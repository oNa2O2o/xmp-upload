"""upload.py <改名文件1> [改名文件2 ...] [--dry] [--parallel 4]
目标文件夹由文件名推出：地区 / FB→Facebook GG→Google TT→Tiktok / 男性向|女性向|全性向。
多个文件并行上传（每个文件一个后台标签页），全部在无窗口的 Chrome 里进行。
每个文件：直接打开上传页(folder_id) -> CDP 设文件一次 -> 等传完且卡片数=1 -> 确定 -> 去文件夹列表核对文件名。
输出每行 `VERIFIED <路径> <文件名>`；有任何失败 exit 2。--dry 只打印映射不上传。"""
import sys, os, re, time
from xmp import *

CH = {'FB': 'Facebook', 'GG': 'Google', 'TT': 'Tiktok'}


def target(path):
    n = os.path.basename(path)
    m = re.match(r'\d{6}-([A-Z]+)-[VP]-[^-]+-(男性向|女性向|全性向)-.*-(FB|GG|TT)-[A-Z]{2,4}-[竖横方]-\d+\.\w+$', n)
    if not m: raise SystemExit(f'文件名不符合命名规则，推不出文件夹: {n}')
    return f'{m.group(1)}/{CH[m.group(3)]}/{m.group(2)}'


def count(pg):
    m = re.search(r'(?:已上传素材数|Number of uploaded materials)\s*[:：]\s*(\d+)', pg.evaluate('()=>document.body.innerText'))   # 中英文界面都认
    return int(m.group(1)) if m else -1


def set_file(pg, f):
    cdp = pg.context.new_cdp_session(pg)
    root = cdp.send('DOM.getDocument', {'depth': -1, 'pierce': True})['root']['nodeId']
    nid = cdp.send('DOM.querySelector', {'nodeId': root, 'selector': 'input[type=file]'})['nodeId']
    cdp.send('DOM.setFileInputFiles', {'nodeId': nid, 'files': [os.path.abspath(f)]})
    cdp.detach()


def verify(pg, fid, name, tries=20):
    stem = os.path.splitext(name)[0]
    for _ in range(tries):
        if any(stem in n for n in list_names(pg, fid)): return True
        pg.wait_for_timeout(3000)
    return False


def main():
    args = sys.argv[1:]
    dry = '--dry' in args
    par = int(args[args.index('--parallel') + 1]) if '--parallel' in args else 4
    files = [a for a in args if not a.startswith('--') and os.path.isfile(a)]
    bad = [a for a in args if not a.startswith('--') and not a.isdigit() and not os.path.isfile(a)]
    if bad: raise SystemExit(f'文件不存在: {bad}')
    resume = '--resume' in args
    jobs = [{'f': f, 'name': os.path.basename(f), 'path': target(f)} for f in files]
    with sync_playwright() as p:
        b, main_pg = get_page(p)
        if not logged_in(main_pg): raise SystemExit('NOT_LOGGED_IN：运行 python xmp.py login 让用户登录一次')
        names, keep = {}, []
        for j in jobs:
            stem = os.path.splitext(j['name'])[0]
            j['fid'] = folder_id(main_pg, j['path'])
            if j['fid'] not in names: names[j['fid']] = list_names(main_pg, j['fid'])
            if any(stem in n for n in names[j['fid']]):
                if not resume: raise SystemExit(f'XMP 该文件夹已有同名素材，先改版本号: {j["name"]}')
                print('SKIP 已在 XMP', j['name'], flush=True); continue
            keep.append(j)
        jobs = keep
        for j in jobs:
            j['fid'] = folder_id(main_pg, j['path'])
            print('→', j['path'], j['fid'], j['name'], flush=True)
        if dry: return
        ctx = main_pg.context
        pending, active, done = list(jobs), [], []
        t0 = time.time()
        while pending or active:
            while pending and len(active) < par:
                j = pending.pop(0)
                pg = ctx.new_page()
                pg.goto(f'{BASE}/creative/upload?folder_id={j["fid"]}&upload_type=1')
                pg.wait_for_selector('input[type=file]', state='attached', timeout=60000); pg.wait_for_timeout(1500)
                clean(pg); set_file(pg, j['f'])
                j.update(pg=pg, start=time.time()); active.append(j)
            time.sleep(3)
            for j in list(active):
                pg = j['pg']; txt = pg.evaluate('()=>document.body.innerText').replace('素材上传中', '')
                n = count(pg)
                uploading = '上传中' in txt or 'Uploading' in txt or re.search(r'\d+%', txt)   # 中英文界面都认（新登录配置默认英文界面）
                if n >= 1 and not uploading:
                    active.remove(j)
                    stem = os.path.splitext(j['name'])[0]
                    if n != 1 or stem[:20] not in txt:
                        j['ok'] = False; j['err'] = f'上传页异常 n={n}'; pg.close(); done.append(j); continue
                    clean(pg); pg.get_by_role('button', name=re.compile(r'^\s*(确定|OK)\s*$')).last.click(); pg.wait_for_timeout(4000)
                    pg.close()
                    j['ok'] = verify(main_pg, j['fid'], j['name']); j['err'] = '' if j['ok'] else '列表里找不到'
                    done.append(j)
                    print(('VERIFIED ' if j['ok'] else 'FAILED ') + j['path'] + ' ' + j['name'] + f'  ({time.time()-j["start"]:.0f}s)', flush=True)
                elif time.time() - j['start'] > 1200:
                    active.remove(j); j['ok'] = False
                    j['err'] = '超时（可能被「过滤重复素材」过滤：XMP 已有同一视频）'; pg.close(); done.append(j)
        # tidy: keep only one tab
        for x in ctx.pages[1:]:
            try: x.close()
            except Exception: pass
        fails = [j for j in done if not j['ok']]
        print(f'完成 {len(done) - len(fails)}/{len(done)}，用时 {time.time()-t0:.0f}s')
        for j in fails: print('FAILED', j['path'], j['name'], j['err'])
        if fails: sys.exit(2)


if __name__ == '__main__':
    main()
