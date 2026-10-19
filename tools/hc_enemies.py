#!/usr/bin/env python3
"""hc_enemies.py - профиль каждого врага: скорость, анимации, звуки, создаваемые объекты/снаряды, урон Крису, HP.
Запуск (после hc_events.py):  python hc_enemies.py out [номер кадра, по умолчанию 4]   -> out/data/ENEMIES_<кадр>.md, enemies_<кадр>.json
Врагами считаются объекты, которые появляются из 'baddie maker' (см. SPAWNS.md) плюс Cop."""
import collections, json, os, re, sys
out = sys.argv[1] if len(sys.argv) > 1 else 'out'
fr = int(sys.argv[2]) if len(sys.argv) > 2 else 4
ld = os.path.join(out, 'logic')
fn = [f for f in os.listdir(ld) if f.startswith('%03d_' % fr)][0]
groups = [x for x in open(os.path.join(ld, fn), encoding='utf-8').read().split('\n\n') if x.startswith('[#')]
enemies = collections.OrderedDict()
for x in groups:
    if 'baddie maker' in x:
        m = re.search(r'create (.+?)\[Active #(\d+)\]', x)
        if m: enemies[m.group(1)] = int(m.group(2))
for x in groups:
    for m in re.finditer(r'IF  (Cop)\[Active #(\d+)\]', x): enemies.setdefault(m.group(1), int(m.group(2)))
prof = collections.OrderedDict()
for name, h in enemies.items():
    def own_group(x):
        # группа считается «собственной», если по условиям это сам враг (а не удар оружия/снаряд Криса по нему)
        ifs = [l.strip()[4:] for l in x.split('\n') if l.strip().startswith('IF')]
        if not any(re.match(r'%s\[Active #%d\]' % (re.escape(name), h), l) for l in ifs) and not any(re.match(r'(Sensor|Timer)', l.strip()) for l in ifs): return False
        bad = r'(Melee Chris|Beserker|Chris Mech|Throwing Chris|Ammo Chris|Mech\[|sickman|Tnt|Gerbil|Bullet|rocket|Flame|Nail\[|Throwing star|bottle|Molotov|donut|Tomahawk|Syringe|Popsicle|minibomb|lasergun|eggs|milk)'
        return not any(re.search(bad, l) for l in ifs)
    own = [x for x in groups if re.search(r'(IF|DO)  %s\[Active #%d\]' % (re.escape(name), h), x) and own_group(x)]
    p = dict(handle=h, groups=len(own))
    p['speeds'] = sorted({int(v) for x in own for v in re.findall(r'DO  %s\[Active #%d\]  Active:6  expr == (\d+)' % (re.escape(name), h), x)})
    p['animations_used'] = sorted({int(v) for x in own for v in re.findall(r'DO  %s\[Active #%d\]  Active:17  short (\d+)' % (re.escape(name), h), x)})
    p['sounds'] = sorted({s for x in own for s in re.findall(r'sample #\d+ "([^"]+)"', x)})
    p['creates'] = sorted({c for x in own for c in re.findall(r'create (.+?)\[Active #\d+\]', x) if not re.match(r'(Blood|part\d|Small Splat|Big splat|Item mover)', c)})
    dmg = collections.Counter()
    for x in groups:
        if not re.search(r'DO  Life Meter\[Counter #\d+\]  Counter:50  expr == (\d+)', x): continue
        if re.search(r'IF  (Chris|Mech)\[Active #\d+\]  Active:-(?:14|4)  obj %s\[Active' % re.escape(name), x) or re.search(r'IF  %s\[Active #\d+\]  Active:-(?:14|4)  obj (Chris|Mech)\[Active' % re.escape(name), x):
            dmg[int(re.search(r'DO  Life Meter\[Counter #\d+\]  Counter:50  expr == (\d+)', x).group(1))] += 1
    p['damage_to_chris'] = sorted(dmg)
    # атаки: условие на анимацию врага + создание снаряда
    atk = []
    for x in own:
        a = re.search(r'IF  %s\[Active #%d\]  Active:-[23]  short (\d+)' % (re.escape(name), h), x)
        cr = [c for c in re.findall(r'create (.+?)\[Active #\d+\]', x) if not re.match(r'(Blood|part\d|Small Splat|Big splat|Item mover)', c)]
        if a and cr: atk.append('анимация %s -> создаёт %s' % (a.group(1), ', '.join(sorted(set(cr)))))
    p['attacks'] = sorted(set(atk))
    prof[name] = p
os.makedirs(os.path.join(out, 'data'), exist_ok=True)
json.dump(prof, open(os.path.join(out, 'data', 'enemies_%03d.json' % fr), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
L = ['# Профили врагов (кадр %s)\n' % fn[:-4]]
for n, p in prof.items():
    L += ['## %s (объект #%d, групп событий %d)' % (n, p['handle'], p['groups']),
          '- скорости: %s' % (p['speeds'] or '—'), '- анимации: %s' % (p['animations_used'] or '—'),
          '- звуки: %s' % (', '.join(p['sounds']) or '—'), '- создаёт: %s' % (', '.join(p['creates']) or '—'),
          '- урон Крису при касании: %s' % (p['damage_to_chris'] or '—'), '- атаки: %s' % ('; '.join(p['attacks']) or '—'), '']
open(os.path.join(out, 'data', 'ENEMIES_%03d.md' % fr), 'w', encoding='utf-8').write('\n'.join(L))
print('Готово: врагов %d. Смотрите %s' % (len(prof), os.path.join(out, 'data')))
