#!/usr/bin/env python3
"""hc_objects.py - параметры объектов и уровней игры (всё, что нужно для пересборки с нуля).

Запуск (после hc_extract.py):   python hc_objects.py out
Создаёт папку out/data:
  objects.json   - все объекты: тип, имя, движение (параметры), анимации (кадры, скорость, повтор)
  frames.json    - все кадры (уровни/экраны): размер, фон, расстановка объектов (x, y, порядок)
  OBJECTS.md     - то же в читаемом виде (по объектам)
Номера кадров анимации - это handle картинок из out/banks/images/_index.csv (колонка handle).
"""
import csv, json, os, struct, sys

OBJ_TYPES = {0: 'QuickBackdrop', 1: 'Backdrop', 2: 'Active', 3: 'Text', 4: 'Question', 5: 'Score', 6: 'Lives',
             7: 'Counter', 8: 'Rtf', 9: 'SubApp'}
MOVE_TYPES = {0: 'Static', 1: 'Mouse', 2: 'Race', 3: 'EightDirections', 4: 'Ball', 5: 'Path', 9: 'Platform', 14: 'Extension'}
ANIM_NAMES = ['Stopped', 'Walking', 'Running', 'Appearing', 'Disappearing', 'Bouncing', 'Shooting', 'Jumping',
              'Falling', 'Climbing', 'Crouch down', 'Stand up', 'Skidding']
DIRS = 32


def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def i16(b, o): return struct.unpack_from('<h', b, o)[0]
def i32(b, o): return struct.unpack_from('<i', b, o)[0]


def anim_name(i):
    return ANIM_NAMES[i] if i < len(ANIM_NAMES) else 'Anim%d' % i


def parse_movement(b, o):
    """старый формат: player u16, type u16, movingAtStart u8, 3 байта, direction i32, затем параметры"""
    m = {'player': u16(b, o), 'type': u16(b, o + 2)}
    m['type_name'] = MOVE_TYPES.get(m['type'], str(m['type']))
    m['moving_at_start'] = b[o + 4]
    m['direction_at_start'] = i32(b, o + 8)
    p = o + 12
    if m['type'] == 3:
        m.update(speed=i16(b, p), acceleration=i16(b, p + 2), deceleration=i16(b, p + 4), bounce=i16(b, p + 6), directions=i32(b, p + 8))
    elif m['type'] == 4:
        m.update(speed=i16(b, p), randomizer=i16(b, p + 2), angles=i16(b, p + 4), security=i16(b, p + 6), deceleration=i16(b, p + 8))
    elif m['type'] == 2:
        m.update(speed=i16(b, p), acceleration=i16(b, p + 2), deceleration=i16(b, p + 4), rotation=i16(b, p + 6),
                 bounce=i16(b, p + 8), angles=i16(b, p + 10), reverse=i16(b, p + 12))
    elif m['type'] == 9:
        m.update(speed=i16(b, p), acceleration=i16(b, p + 2), deceleration=i16(b, p + 4), control=i16(b, p + 6),
                 gravity=i16(b, p + 8), jump=i16(b, p + 10))
    elif m['type'] == 1:
        m.update(x1=i16(b, p), x2=i16(b, p + 2), y1=i16(b, p + 4), y2=i16(b, p + 6))
    elif m['type'] == 5:
        n = i16(b, p); m.update(steps=n, min_speed=i16(b, p + 2), max_speed=i16(b, p + 4), loop=b[p + 6], reposition=b[p + 7], reverse=b[p + 8])
        q = p + 10; steps = []
        for _ in range(n):
            sz = b[q + 1]
            steps.append(dict(flags=b[q], speed=b[q + 2], direction=b[q + 3], dx=i16(b, q + 4), dy=i16(b, q + 6), length=i16(b, q + 12), pause=i16(b, q + 14)))
            q += sz if sz else 16
        m['path'] = steps
    return m


def parse_animations(b, base):
    size = u16(b, base); count = u16(b, base + 2)
    offs = [u16(b, base + 4 + 2 * i) for i in range(count)]
    res = {}
    for i, ao in enumerate(offs):
        if not ao: continue
        dirs = {}
        for d in range(DIRS):
            do = u16(b, base + ao + 2 * d)
            if not do: continue
            q = base + ao + do
            mn, mx = struct.unpack_from('<bb', b, q)
            rep, back, cnt = struct.unpack_from('<hhH', b, q + 2)
            frames = list(struct.unpack_from('<%dH' % cnt, b, q + 8))
            dirs[d] = dict(min_speed=mn, max_speed=mx, repeat=rep, back_to=back, frames=frames)
        res[i] = dict(name=anim_name(i), directions=dirs)
    return res


def load_objects(out):
    d = os.path.join(out, 'objects'); res = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('_4444.bin'): continue
        h = int(fn[:4]); hd = open(os.path.join(d, fn), 'rb').read()
        o = {'handle': h, 'type': i16(hd, 2)}
        o['type_name'] = OBJ_TYPES.get(o['type'], str(o['type']))
        p = os.path.join(d, '%04d_4445.bin' % h)
        o['name'] = open(p, 'rb').read().split(b'\0')[0].decode('cp1251', 'replace') if os.path.exists(p) else ''
        p = os.path.join(d, '%04d_4446.bin' % h)
        if os.path.exists(p):
            b = open(p, 'rb').read()
            o['props_size'] = len(b)
            try:
                if o['type'] == 2 and len(b) > 0x40:
                    mo, ao = u16(b, 4), u16(b, 6)
                    for key, fn, off in (('movement', parse_movement, mo), ('animations', parse_animations, ao)):
                        if not off: continue
                        try: o[key] = fn(b, off)
                        except Exception as e: o['error'] = '%s %s: %s' % (o.get('error', ''), key, e); o['props_hex'] = b.hex()
                else:
                    o['props_hex'] = b.hex()
            except Exception as e:
                o['error'] = str(e); o['props_hex'] = b.hex()
        res[h] = o
    return res


def load_frames(out, objs):
    base = os.path.join(out, 'frames'); frames = []
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        f = {'index': int(name[:3]), 'name': name[4:]}
        h = open(os.path.join(d, 'header.bin'), 'rb').read()
        if len(h) >= 10:
            f.update(width=u16(h, 0), height=u16(h, 2), background_bgr=list(h[4:7]), flags=u16(h, 8))
        p = os.path.join(d, 'objects.bin')
        inst = []
        if os.path.exists(p):
            o = open(p, 'rb').read()
            n = struct.unpack_from('<I', o, 0)[0]
            for k in range(n):
                iid, info, x, y, pt, ph = struct.unpack_from('<HHhhhh', o, 4 + 12 * k)
                ob = objs.get(info, {})
                inst.append(dict(id=iid, object=info, name=ob.get('name', ''), type=ob.get('type_name', ''), x=x, y=y, parent_type=pt, parent=ph))
        f['instances'] = inst
        frames.append(f)
    return frames


def write_md(path, objs):
    L = ['# Объекты игры\n']
    for h, o in objs.items():
        if o['type'] != 2: continue
        L.append('## #%d %s' % (h, o['name']))
        m = o.get('movement')
        if m: L.append('Движение: ' + ', '.join('%s=%s' % kv for kv in m.items() if kv[0] != 'path'))
        for ai, a in o.get('animations', {}).items():
            ds = a['directions']
            if not ds: continue
            parts = []
            for di, dr in ds.items():
                parts.append('напр.%d: %d кадр., скорость %d-%d, повтор %d, назад к %d' % (di, len(dr['frames']), dr['min_speed'], dr['max_speed'], dr['repeat'], dr['back_to']))
            L.append('- анимация %d (%s): %s' % (ai, a['name'], '; '.join(parts)))
        L.append('')
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'out'
    objs = load_objects(out); frames = load_frames(out, objs)
    dd = os.path.join(out, 'data'); os.makedirs(dd, exist_ok=True)
    json.dump(objs, open(os.path.join(dd, 'objects.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(frames, open(os.path.join(dd, 'frames.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_md(os.path.join(dd, 'OBJECTS.md'), objs)
    err = [h for h, o in objs.items() if 'error' in o]
    na = sum(1 for o in objs.values() if o.get('animations'))
    print('Готово: объектов %d (с анимациями %d, ошибок разбора %d), кадров %d, объектов на уровнях %d. Смотрите %s' %
          (len(objs), na, len(err), len(frames), sum(len(f['instances']) for f in frames), dd))
    if err: print('ошибки у объектов:', err[:20])


if __name__ == '__main__':
    main()
