"""revoke.py <关键字> [--apply] — 撤回误传：从 XMP 删除名字含关键字的素材（如 {T1029ZHM），删后复查远端无残留。
默认只列出要删的素材（MiraiMind素材库全部子文件夹最新 2000 条里匹配的）；确认后加 --apply 才删除。
删除走接口 POST /mediacenter/manage/delete，body id=<逗号分隔>&zone=company&show_deep=0&is_global=0。
只撤回 XMP；本地改名件 / 归档 / 回收站另行处理。运行前 export PYTHONIOENCODING=utf-8。"""
import sys
from xmp import API, ROOT_FOLDER, LIB, get_page, api_token, sync_playwright


def find(pg, key, n=2000):
    tok, out = api_token(pg), []
    for page in range(1, n // 500 + 1):
        r = pg.request.get(API + '/mediacenter/manage/searchList', headers={'authorization': tok}, timeout=60000,
                           params={'page': page, 'page_size': 500, 'folder_id': ROOT_FOLDER, 'show_deep': 1, 'show_stats': 0,
                                   'column_list': 'id,name', 'is_export': 0, 'media_source': 'local', 'is_global': 0})
        lst = r.json()['data']['list']; out += [x for x in lst if key in x['name']]
        if len(lst) < 500: break
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args or len(args[0]) < 6: raise SystemExit('需要一个足够具体的关键字（≥6 个字符），如 {T1029ZHM')
    key = args[0]
    with sync_playwright() as p:
        b, pg = get_page(p)
        hits = find(pg, key)
        for x in hits: print(x['id'], x['name'])
        print(f'匹配 {len(hits)} 条（{LIB} 最新 2000 条内）')
        if '--apply' not in sys.argv or not hits: sys.exit()
        ids = ','.join(str(x['id']) for x in hits)
        r = pg.request.post(API + '/mediacenter/manage/delete', headers={'authorization': api_token(pg)},
                            form={'id': ids, 'zone': 'company', 'show_deep': '0', 'is_global': '0'})
        print('delete', r.status, r.text()[:200])
        left = find(pg, key)
        print('REMAINING', len(left)); [print('  ', x['name']) for x in left]
        sys.exit(0 if not left else 2)
