#!/usr/bin/env python3
"""make_scenes.py - строит сцены уровней Godot (.tscn) из данных игры, чтобы уровни было видно и можно было править в редакторе.

Запуск из папки проекта (где project.godot):   python tools/make_scenes.py            -> levels/004_Downtown.tscn
                                               python tools/make_scenes.py 4 11 12    -> несколько уровней
                                               python tools/make_scenes.py all        -> все уровни
Уже существующие сцены НЕ перезаписываются (ваши правки целы). Перезаписать: добавьте --force.
Сцена уровня:
  Background - фоны (Sprite2D) и сплошные полосы пола/потолка (ColorRect), в порядке игры
  Decor      - видимые на старте объекты уровня (окна, пилоны, стрелки ...); в игре они оживают (анимация)
  Markers    - Floor (высота пола), ChrisStart (старт Криса, с превью), Makers (точки появления врагов)
  Doors      - зоны дверей (жёлтые прямоугольники, metadata "to" = куда ведёт); в игре невидимы
Всё это можно двигать мышкой в редакторе - игра берёт позиции из сцены.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'hc', 'data')
SKIP = re.compile(r'sensor|maker|zone|scroller|chris|mech|wall|killer|locator|backdrop|dollar|label|loading|item|subapp|'
                  r'angel|gerbil|berserk|fuel', re.I)


def j(name, default=None):
    p = os.path.join(D, name)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else default


def first_frame(anims, h):
    a = anims.get(str(h), {}).get('anims', {})
    for ak in sorted(a, key=int):
        dirs = a[ak]['dirs']
        for dk in sorted(dirs, key=int):
            if dirs[dk]['frames']:
                return dirs[dk]['frames'][0]
    return None


def build(index, levels, anims, images, flags, sl, force=False):
    lv = levels[index]
    name = '%03d_%s' % (index, re.sub(r'[^\w]+', '_', lv['name']).strip('_'))
    target = os.path.join(ROOT, 'levels', name + '.tscn')
    if os.path.exists(target) and not force:
        print('%s: сцена уже есть (%s) - пропущена, чтобы не затереть ваши правки. Перезаписать: добавьте --force'
              % (lv['name'], os.path.relpath(target, ROOT)))
        return
    ext = {}                              # путь -> id
    nodes = []

    def tex(h):
        p = 'res://hc/sprites/%05d.png' % h
        if p not in ext: ext[p] = 't%d' % h
        return ext[p]

    def node(nm, typ, parent, props):
        nodes.append((nm, typ, parent, props))

    node('Background', 'Node2D', '.', {'z_index': '-100'})
    node('Decor', 'Node2D', '.', {})
    node('Markers', 'Node2D', '.', {})
    node('Makers', 'Node2D', 'Markers', {})
    node('Doors', 'Node2D', '.', {'z_index': '50'})
    floor_y = None
    is_slice = sl and int(sl.get('level_index', -1)) == index
    for k, ins in enumerate(lv['instances']):
        t, h, x, y = ins['type'], ins['object'], ins['x'], ins['y']
        a = anims.get(str(h), {})
        if t == 'Backdrop' and ins.get('image') is not None:
            node('bd_%d' % k, 'Sprite2D', 'Background', {'position': 'Vector2(%d, %d)' % (x, y),
                 'texture': 'ExtResource("%s")' % tex(ins['image']), 'centered': 'false'})
        elif t == 'QuickBackdrop':
            ph = bytes.fromhex(a.get('props_hex', ''))
            if len(ph) >= 26:
                w = int.from_bytes(ph[8:10], 'little'); hh = int.from_bytes(ph[10:12], 'little')
                c = int.from_bytes(ph[22:26], 'little')
                r, g, b = c & 255, (c >> 8) & 255, (c >> 16) & 255
                node('qb_%d' % k, 'ColorRect', 'Background', {'offset_left': str(x), 'offset_top': str(y),
                     'offset_right': str(x + w), 'offset_bottom': str(y + hh), 'mouse_filter': '2',
                     'color': 'Color(%.3f, %.3f, %.3f, 1)' % (r / 255, g / 255, b / 255)})
                if y > 0 and (floor_y is None or y < floor_y): floor_y = y
        elif t == 'Active':
            nm = ins['name']
            if is_slice and nm == 'Chris' and (x, y) != (0, 0) and not any(n[0] == 'ChrisStart' for n in nodes):
                node('ChrisStart', 'Marker2D', 'Markers', {'position': 'Vector2(%d, %d)' % (x, y)})
                f = first_frame(anims, h)
                if f is not None and str(f) in images:
                    hx, hy = images[str(f)]['hot']
                    node('Preview', 'Sprite2D', 'Markers/ChrisStart', {'texture': 'ExtResource("%s")' % tex(f),
                         'centered': 'false', 'offset': 'Vector2(%d, %d)' % (-hx, -hy), 'metadata/editor_only': 'true'})
                continue
            if nm == 'baddie maker' and y > 0:
                node('maker_%d' % k, 'Marker2D', 'Markers/Makers', {'position': 'Vector2(%d, %d)' % (x, y)})
                continue
            vis = flags.get(str(h), {}).get('visible', True)
            if not vis or (x, y) == (0, 0) or not (0 <= x < lv['width'] and 0 <= y < lv['height']) or SKIP.search(nm):
                continue
            f = first_frame(anims, h)
            if f is None or str(f) not in images: continue
            hx, hy = images[str(f)]['hot']
            node('%s_%d' % (re.sub(r'[^\w]+', '_', nm) or 'obj', k), 'Sprite2D', 'Decor',
                 {'position': 'Vector2(%d, %d)' % (x, y), 'texture': 'ExtResource("%s")' % tex(f), 'centered': 'false',
                  'offset': 'Vector2(%d, %d)' % (-hx, -hy), 'metadata/hc_obj': str(h)})
    # Линия, по которой ходят персонажи: в оригинале все стоящие на земле объекты (Крис, точки появления врагов, пилоны)
    # расставлены точкой привязки на ~531..537, а полоса пола (QuickBackdrop) лежит ниже - она лишь нижняя граница.
    # Берём минимальную y из стартовой позиции Криса и точек появления врагов (Downtown: 531 по замеру, получится 532).
    ground = [ins['y'] for ins in lv['instances'] if ins['type'] == 'Active' and ins['name'] in ('baddie maker', 'Chris')
              and ins['y'] > 0 and (ins['x'], ins['y']) != (0, 0)]
    walk_y = min(ground) if ground else (floor_y if floor_y is not None else lv['height'] - 27)
    node('Floor', 'Marker2D', 'Markers', {'position': 'Vector2(0, %d)' % walk_y})
    if is_slice:
        for i, d in enumerate(sl.get('doors', [])):
            node('door_%d_%s' % (i, re.sub(r'[^\w]+', '_', d['to'])), 'ColorRect', 'Doors',
                 {'offset_left': str(d['x0']), 'offset_top': '300', 'offset_right': str(d['x1']),
                  'offset_bottom': str(floor_y or 573), 'color': 'Color(1, 0.9, 0.1, 0.3)', 'mouse_filter': '2',
                  'metadata/to': '"%s"' % d['to']})
    L = ['[gd_scene load_steps=%d format=3]' % (len(ext) + 2), '',
         '[ext_resource type="Script" path="res://scripts/level.gd" id="s1"]']
    for p, i in ext.items():
        L.append('[ext_resource type="Texture2D" path="%s" id="%s"]' % (p, i))
    L += ['', '[node name="%s" type="Node2D"]' % name, 'script = ExtResource("s1")', 'level_index = %d' % index]
    for nm, typ, parent, props in nodes:
        L += ['', '[node name="%s" type="%s" parent="%s"]' % (nm, typ, parent)]
        L += ['%s = %s' % (k, v) for k, v in props.items()]
    os.makedirs(os.path.join(ROOT, 'levels'), exist_ok=True)
    out = os.path.join(ROOT, 'levels', name + '.tscn')
    open(out, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('%s: фонов/полос/декора/маркеров %d -> %s' % (lv['name'], len(nodes), os.path.relpath(out, ROOT)))


def main():
    levels, anims, images = j('levels.json'), j('anims.json'), j('images.json')
    flags, sl = j('flags.json', {}), j('slice.json', {})
    force = '--force' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--force'] or ['4']
    idx = range(len(levels)) if args == ['all'] else [int(a) for a in args]
    for i in idx:
        build(i, levels, anims, images, flags, sl, force)


if __name__ == '__main__':
    main()
