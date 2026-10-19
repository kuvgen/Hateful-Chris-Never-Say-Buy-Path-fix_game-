#!/usr/bin/env python3
"""hc_damage.py - таблица урона по врагам: кто (оружие/снаряд/анимация) -> кого -> сколько снимает HP.
Запуск (после hc_events.py):  python hc_damage.py out [номер кадра, по умолчанию 4 = Downtown]
Создаёт out/data/damage_<кадр>.json и DAMAGE_<кадр>.md"""
import collections, json, os, re, sys
out = sys.argv[1] if len(sys.argv) > 1 else 'out'
fr = int(sys.argv[2]) if len(sys.argv) > 2 else 4
ld = os.path.join(out, 'logic')
fn = [f for f in os.listdir(ld) if f.startswith('%03d_' % fr)][0]
groups = [x for x in open(os.path.join(ld, fn), encoding='utf-8').read().split('\n\n') if x.startswith('[#')]
rx_do = re.compile(r'DO  (.+?)\[Active #(\d+)\]  Active:33  altvalue #0 \| expr == (-?\d+)')
rx_if_anim = re.compile(r'IF  (.+?)\[Active #(\d+)\]  Active:-3  short (\d+)')
rx_if_col = re.compile(r'IF  (.+?)\[Active #(\d+)\]  Active:-(?:14|4)  obj (.+?)\[Active #(\d+)\]')
rx_if_frame = re.compile(r'Active:-1  expr == (\d+)')
rows = collections.OrderedDict()
for x in groups:
    dos = rx_do.findall(x)
    if not dos: continue
    cols = rx_if_col.findall(x)
    anim = rx_if_anim.search(x)
    frame = rx_if_frame.search(x)
    for (en, eh, dmg) in dos:
        src = cols[0][0] if cols else '?'
        key = (src, int(anim.group(3)) if anim and anim.group(1) == src else None, en)
        rows.setdefault(key, set()).add(int(dmg))
data = [dict(source=k[0], source_animation=k[1], target=k[2], damage=sorted(v)) for k, v in rows.items()]
os.makedirs(os.path.join(out, 'data'), exist_ok=True)
json.dump(data, open(os.path.join(out, 'data', 'damage_%03d.json' % fr), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
by = collections.OrderedDict()
for d in data: by.setdefault((d['source'], d['source_animation'], tuple(d['damage'])), []).append(d['target'])
L = ['# Урон по врагам (кадр %s)\n' % fn[:-4], 'Урон = число, которое событие вычитает из HP врага. Одинаковые для нескольких врагов строки объединены.\n', '| источник | анимация | урон | кому (врагов) |', '|---|---|---|---|']
for (src, an, dm), ts in by.items():
    L.append('| %s | %s | %s | %s |' % (src, an if an is not None else '', '/'.join(map(str, dm)), 'все (%d)' % len(ts) if len(ts) >= 8 else ', '.join(ts)))
open(os.path.join(out, 'data', 'DAMAGE_%03d.md' % fr), 'w', encoding='utf-8').write('\n'.join(L))
print('Готово: записей %d. Смотрите %s' % (len(data), os.path.join(out, 'data')))
