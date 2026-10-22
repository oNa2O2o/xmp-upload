"""rename_xmp.py <对照表.json> [--only 关键字] [--apply]
按「旧名 -> 新名」对照表批量改 XMP 素材库里的素材名（接口 POST /mediacenter/manage/updateName {id, name}，
保留素材 ID / 投放数据，不重传）。目标文件夹由新文件名推出（upload.target）。
不加 --apply 只打印将要改的条目；改完逐个用 searchList 核对新名存在、旧名消失。
对照表格式：[[旧文件名, 新文件名(, 备注)], ...]；同一新名可有多行旧名（云端名与本地不同时补一行）（含扩展名；XMP 里名字带不带扩展名都能匹配）。"""
import sys, os, json
from xmp import *
from upload import target


def folder_items(pg, tok, fid):
    out = []
    for page in range(1, 41):
        r = pg.request.get(API + '/mediacenter/manage/searchList', headers={'authorization': tok},
                           params={'page': page, 'page_size': 500, 'folder_id': fid, 'show_deep': 0, 'show_stats': 0,
                                   'column_list': 'id,name', 'is_export': 0, 'media_source': 'local', 'is_global': 0})
        lst = r.json()['data']['list']; out += lst
        if len(lst) < 500: break
    return out


def main():
    args = sys.argv[1:]
    apply = '--apply' in args; args = [a for a in args if a != '--apply']
    only = None
    if '--only' in args:
        i = args.index('--only'); only = args[i + 1]; del args[i:i + 2]
    rows = json.load(open(args[0], encoding='utf-8'))
    if only: rows = [r for r in rows if only in r[0]]
    with sync_playwright() as p:
        b, pg = get_page(p)
        tok = api_token(pg); cache = {}; plan = []; bad = 0
        for old, new, *_ in rows:
            fid = folder_id(pg, target(new))
            if fid not in cache: cache[fid] = folder_items(pg, tok, fid)
            so, sn = os.path.splitext(old)[0], os.path.splitext(new)[0]
            hit = [x for x in cache[fid] if x['name'] in (old, so)]
            done = [x for x in cache[fid] if x['name'] in (new, sn)]
            if done and not hit: print('已是新名', target(new), new); continue
            if not hit and sum(r[1] == new for r in rows) > 1: continue   # 同一新名的另一行（云端别名）会处理
            if len(hit) != 1: print(f'✗ 找不到或不唯一({len(hit)}) {target(new)} {old}'); bad += 1; continue
            x = hit[0]; nn = new if x['name'].endswith(os.path.splitext(old)[1]) else sn
            plan.append((fid, x['id'], x['name'], nn, target(new)))
        for fid, mid, on, nn, t in plan:
            print(('改 ' if apply else '将改 ') + t + f'  id={mid}\n   {on}\n → {nn}')
            if apply:
                r = pg.request.post(API + '/mediacenter/manage/updateName', headers={'authorization': tok},
                                    data={'id': mid, 'name': nn})
                j = r.json()
                if j.get('code') not in (0, 200) and not j.get('success', False) and 'data' not in j:
                    print('   ✗ 接口返回', j); bad += 1
        if apply and plan:
            pg.wait_for_timeout(3000)
            for fid in {x[0] for x in plan}:
                names = {x['name'] for x in folder_items(pg, tok, fid)}
                for f, mid, on, nn, t in [x for x in plan if x[0] == fid]:
                    ok = nn in names and on not in names
                    print(('VERIFIED ' if ok else '✗ 核对失败 ') + t + ' ' + nn); bad += (not ok)
        print(f'计划 {len(plan)} 个，问题 {bad} 个')
        sys.exit(2 if bad else 0)


if __name__ == '__main__':
    main()
