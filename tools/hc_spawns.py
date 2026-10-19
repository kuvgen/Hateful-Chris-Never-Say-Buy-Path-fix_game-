#!/usr/bin/env python3
"""hc_spawns.py - появление врагов: тип, HP, интервал, лимиты по кадрам.
Запуск (после hc_events.py):  python hc_spawns.py out      -> out/data/SPAWNS.md, spawns.json (все кадры)"""
import json, os, re, sys
out = sys.argv[1] if len(sys.argv) > 1 else 'out'
ld = os.path.join(out, 'logic'); res = []
for fn in sorted(os.listdir(ld)):
    if not re.match(r'\d+_', fn): continue
    for x in open(os.path.join(ld, fn), encoding='utf-8').read().split('\n\n'):
        if not x.startswith('[#') or 'baddie maker' not in x or 'create ' not in x: continue
        cr = re.search(r'create (.+?)\[Active #(\d+)\]', x)
        if not cr: continue
        name = cr.group(1)
        hp = re.search(r'%s\[Active #\d+\]  Active:31  altvalue #0 \| expr == (-?\d+)' % re.escape(name), x)
        tm = re.search(r'Timer:-4  every (\d+)ms', x)
        cnt = re.findall(r'IF  (Count .+?)\[Counter #\d+\]  Counter:-49  expr (<=|==|<|>=|>) (\d+)', x)
        mx = re.search(r'Maximum baddie counter\[Counter #\d+\]  Counter:-49  expr <= (\d+)', x)
        res.append(dict(frame=fn[:-4], enemy=name, hp=int(hp.group(1)) if hp else None, every_ms=int(tm.group(1)) if tm else None,
                        type_limit=cnt[0][2] if cnt else None, total_limit=int(mx.group(1)) if mx else None))
os.makedirs(os.path.join(out, 'data'), exist_ok=True)
json.dump(res, open(os.path.join(out, 'data', 'spawns.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
L = ['# Появление врагов\n', '| кадр | враг | HP | раз в (мс) | лимит этого типа | лимит всех |', '|---|---|---|---|---|---|']
for r in res: L.append('| %s | %s | %s | %s | %s | %s |' % (r['frame'], r['enemy'], r['hp'], r['every_ms'], r['type_limit'], r['total_limit']))
open(os.path.join(out, 'data', 'SPAWNS.md'), 'w', encoding='utf-8').write('\n'.join(L))
print('Готово: записей %d. Смотрите %s' % (len(res), os.path.join(out, 'data')))
