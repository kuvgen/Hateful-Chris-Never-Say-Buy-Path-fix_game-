#!/usr/bin/env python3
"""hc_map.py - карта переходов между кадрами (двери, меню, смерть и т.д.).
Запуск (после hc_events.py):  python hc_map.py out     -> out/data/MAP.md, map.json
'Game:2 short N' = перейти на кадр в позиции N списка порядка кадров (блок 0x222B в заголовке)."""
import json, os, re, struct, sys
out = sys.argv[1] if len(sys.argv) > 1 else 'out'
b = open(os.path.join(out, 'header', '222B_11.bin'), 'rb').read()
order = list(struct.unpack('<%dH' % (len(b) // 2), b))      # позиция -> номер кадра
fr = {int(d[:3]): d[4:] for d in os.listdir(os.path.join(out, 'frames'))}
ld = os.path.join(out, 'logic'); res = []
for fn in sorted(os.listdir(ld)):
    if not re.match(r'\d+_', fn): continue
    src = int(fn[:3])
    for x in open(os.path.join(ld, fn), encoding='utf-8').read().split('\n\n'):
        if not x.startswith('[#'): continue
        for n in re.findall(r'Game:2  short (\d+)', x):
            n = int(n); dst = order[n] if n < len(order) else None
            cond = []
            for l in x.split('\n'):
                l = l.strip()
                if not l.startswith('IF'): continue
                z = re.search(r'zone \((-?\d+),(-?\d+)\)-\((-?\d+),(-?\d+)\)', l)
                if z: cond.append('зона x%s..%s y%s..%s' % (z.group(1), z.group(3), z.group(2), z.group(4)))
                k = re.search(r'Keyboard:-1  key (\d+)', l)
                if k: cond.append('клавиша %s' % k.group(1))
                c = re.search(r'IF  (.+?)\[Active #\d+\]  Active:-29', l)
                if c: cond.append('клик по «%s»' % c.group(1))
            res.append(dict(from_frame=src, from_name=fr.get(src), position=n, to_frame=dst, to_name=fr.get(dst), when=cond))
os.makedirs(os.path.join(out, 'data'), exist_ok=True)
json.dump(dict(order=order, transitions=res), open(os.path.join(out, 'data', 'map.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
L = ['# Карта переходов\n', 'Позиция в списке порядка кадров → кадр: ' + ', '.join('%d→%s' % (i, fr.get(h)) for i, h in enumerate(order)), '']
cur = None
for r in res:
    if r['from_frame'] != cur: cur = r['from_frame']; L += ['', '## %03d %s' % (cur, r['from_name'])]
    L.append('- → %s (позиция %d): %s' % (r['to_name'], r['position'], '; '.join(r['when']) or 'без условия'))
open(os.path.join(out, 'data', 'MAP.md'), 'w', encoding='utf-8').write('\n'.join(L))
print('Готово: переходов %d. Смотрите %s' % (len(res), os.path.join(out, 'data')))
