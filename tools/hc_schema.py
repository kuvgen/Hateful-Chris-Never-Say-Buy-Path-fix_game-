#!/usr/bin/env python3
"""hc_schema.py - модель данных игры (то, что хранится в syshcin1.ini): разделы, ключи, значения при новой игре,
где что читается и пишется.   Запуск (после hc_events.py):   python hc_schema.py out
Создаёт out/data/save_schema.json и out/data/SAVE_SCHEMA.md"""
import collections, json, os, re, sys

out = sys.argv[1] if len(sys.argv) > 1 else 'out'
ld = os.path.join(out, 'logic')
W = collections.OrderedDict()           # (раздел, ключ) -> {frame: set(значений)}
R = collections.defaultdict(set)         # (раздел, ключ) -> кадры, где читается
defaults = collections.OrderedDict()     # значения, выставляемые в кадре Training (новая игра)
lit = re.compile(r'expr == (.*)$')
rd = re.compile(r'\.f50 "([^"]*)" sys\.f-3 "([^"]*)" sys\.f-2')
for fn in sorted(os.listdir(ld)):
    if not re.match(r'\d+_', fn): continue
    frame = fn[:-4]; sec = key = None
    for line in open(os.path.join(ld, fn), encoding='utf-8'):
        if '[32 #44]' in line and '32:4' in line or '32:50' in line:
            m = lit.search(line)
            if '32:48' in line and m: sec = m.group(1).strip('"')
            elif '32:49' in line and m: key = m.group(1).strip('"')
            elif '32:50' in line and m and sec and key:
                v = m.group(1)
                W.setdefault((sec.lower(), key.lower()), collections.defaultdict(set))[frame].add(v)
                if frame.startswith('003_Training') and (sec.lower(), key.lower()) not in defaults: defaults[(sec.lower(), key.lower())] = v
        for s, k in rd.findall(line): R[(s.lower(), k.lower())].add(frame)
tree = collections.OrderedDict()
for (s, k) in list(W) + [x for x in R if x not in W]:
    tree.setdefault(s, collections.OrderedDict())[k] = dict(
        default=defaults.get((s, k)), written_in=sorted(W.get((s, k), {})), read_in=sorted(R.get((s, k), [])),
        values_written=sorted({v for fs in W.get((s, k), {}).values() for v in fs})[:12])
os.makedirs(os.path.join(out, 'data'), exist_ok=True)
json.dump(tree, open(os.path.join(out, 'data', 'save_schema.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
L = ['# Данные сохранения (syshcin1.ini)\n', 'Значение по умолчанию = то, что ставит кадр Training при новой игре.\n']
for s, ks in tree.items():
    L.append('## [%s]' % s)
    L.append('| ключ | при новой игре | пишется в кадрах | читается в кадрах | какие значения встречаются |\n|---|---|---|---|---|')
    for k, d in ks.items():
        L.append('| %s | %s | %d | %d | %s |' % (k, d['default'], len(d['written_in']), len(d['read_in']), ', '.join(d['values_written'])))
    L.append('')
open(os.path.join(out, 'data', 'SAVE_SCHEMA.md'), 'w', encoding='utf-8').write('\n'.join(L))
print('Готово: разделов %d, ключей %d. Смотрите %s' % (len(tree), sum(len(v) for v in tree.values()), os.path.join(out, 'data')))
