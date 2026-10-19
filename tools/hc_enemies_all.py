#!/usr/bin/env python3
"""hc_enemies_all.py - враги, их HP и атаки по ВСЕМ уровням.
Запуск (после hc_events.py):  python hc_enemies_all.py out
Создаёт out/data/ENEMIES_ALL.md и enemies_all.json
HP = значение, которым враг инициализируется (Active:31 altvalue #0); 0/1 - служебные значения, отброшены.
Атака = группа, где Life Meter уменьшается; источник и анимация берутся из условий группы.
"""
import glob, json, os, re, sys

out = sys.argv[1] if len(sys.argv) > 1 else 'out'
res = {}
for f in sorted(glob.glob(os.path.join(out, 'logic', '0*.txt'))):
    name = os.path.basename(f)[:-4]
    groups = [x for x in open(f, encoding='utf-8').read().split('\n\n') if x.startswith('[#')]
    atk, hp, env = {}, {}, {}
    for x in groups:
        d = re.search(r'Life Meter\[Counter #167\]  Counter:50  expr == (\S+)', x)
        if d:
            a = re.search(r'IF  (?!Chris)(.+?)\[Active #\d+\]  Active:-3  short (\d+)', x)
            m = re.search(r'IF  Chris\[Active #66\]  Active:-(?:4|14)  obj (.+?)\[', x)
            s = re.search(r'sample #\d+ "([^"]+)"', x)
            snd = s.group(1) if s else ''
            if a: atk[a.group(1)] = dict(anim=int(a.group(2)), damage=d.group(1), sound=snd)
            else: env[m.group(1) if m else '(условие не определено)'] = dict(damage=d.group(1), sound=snd)
        for h in re.finditer(r'DO  (.+?)\[Active #\d+\]  Active:31  altvalue #0 \| expr == (\d+)', x):
            if int(h.group(2)) > 1: hp[h.group(1)] = int(h.group(2))
    if atk or hp or env: res[name] = dict(hp=hp, attacks=atk, other_damage=env)
json.dump(res, open(os.path.join(out, 'data', 'enemies_all.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
L = ['# Враги по уровням\n']
for n, r in res.items():
    L.append('## ' + n)
    L.append('| Враг | HP | Анимация атаки | Урон | Звук |\n|---|---|---|---|---|')
    for e in sorted(set(r['hp']) | set(r['attacks'])):
        a = r['attacks'].get(e)
        L.append('| %s | %s | %s | %s | %s |' % (e, r['hp'].get(e, '?'), a['anim'] if a else '—', a['damage'] if a else '—', a['sound'] if a else ''))
    if r['other_damage']:
        L.append('Прочий урон/штрафы: ' + '; '.join('%s: %s %s' % (k, v['damage'], v['sound']) for k, v in r['other_damage'].items()))
    L.append('')
open(os.path.join(out, 'data', 'ENEMIES_ALL.md'), 'w', encoding='utf-8').write('\n'.join(L))
print('готово:', len(res), 'уровней')
