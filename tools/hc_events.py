#!/usr/bin/env python3
"""hc_events.py - читаемый дамп событий (логики) игры Clickteam формата PAME 0x0300.

Запуск (после hc_extract.py):   python hc_events.py out
Создаёт:  out/logic/_objects.txt     - все объекты: номер, тип, имя, в скольких событиях встречается
          out/logic/NNN_<кадр>.txt   - события каждого кадра (условия IF / действия DO)
Формат разобран по данным игры (условия/действия: object type и num - знаковые байты; у условия в конце
ещё i16-идентификатор). Названий условий/действий в игре нет (они живут в редакторе), поэтому они
показаны числами тип:номер; для известных есть подсказки в NAMES (можно дополнять).
"""
import os, re, struct, sys, collections

OBJ_TYPES = {-7: 'Player', -6: 'Keyboard', -5: 'Create', -4: 'Timer', -3: 'Game', -2: 'Speaker', -1: 'System',
             0: 'QuickBackdrop', 1: 'Backdrop', 2: 'Active', 3: 'Text', 4: 'Question', 5: 'Score', 6: 'Lives',
             7: 'Counter', 8: 'Rtf', 9: 'SubApp'}
CMP = {0: '==', 1: '!=', 2: '<=', 3: '<', 4: '>=', 5: '>'}
# (тип объекта, номер) -> имя. Сюда можно вписывать расшифрованные условия/действия.
COND_NAMES = {}
ACT_NAMES = {}

def i8(b, o): return struct.unpack_from('<b', b, o)[0]
def u8(b, o): return b[o]
def i16(b, o): return struct.unpack_from('<h', b, o)[0]
def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def i32(b, o): return struct.unpack_from('<i', b, o)[0]

class Objects:
    def __init__(self, d):
        self.d = d; self.info = {}
        if not os.path.isdir(d): return
        for fn in sorted(os.listdir(d)):
            m = re.match(r'(\d+)_4444\.bin$', fn)
            if not m: continue
            h = int(m.group(1)); r = open(os.path.join(d, fn), 'rb').read()
            typ = struct.unpack_from('<h', r, 2)[0]
            nm = os.path.join(d, '%04d_4445.bin' % h)
            name = open(nm, 'rb').read().split(b'\0')[0].decode('cp1251', 'replace') if os.path.exists(nm) else ''
            self.info[h] = (typ, name)
    def label(self, h):
        if h in self.info:
            t, n = self.info[h]
            return '%s[%s #%d]' % (n or '?', OBJ_TYPES.get(t, t), h)
        return 'obj#%d' % h

def cstr(b):
    return b.split(b'\0')[0].decode('cp1251', 'replace')

def parse_expr(b, objs):
    """список выражений: [type i8][num i8][size i16][payload]; конец - 00 00"""
    pos = 0; out = []
    while pos + 2 <= len(b):
        t, n = i8(b, pos), i8(b, pos + 1)
        if t == 0 and n == 0: break
        if pos + 4 > len(b): out.append('<обрезано>'); break
        size = u16(b, pos + 2)
        pl = b[pos + 4: pos + size]
        if t == -1:
            if n == 0 and len(pl) >= 4: out.append(str(i32(pl, 0)))
            elif n == 3: out.append('"%s"' % cstr(pl))
            elif n == 23 and len(pl) >= 8: out.append(repr(struct.unpack_from('<d', pl, 0)[0]))
            elif n in (24, 50) and len(pl) >= 8: out.append('global#%d' % i32(pl, 4))
            else: out.append('sys.f%d%s' % (n, ('(' + pl.hex() + ')') if pl else ''))
        elif t >= 2 or t == -7:
            if len(pl) >= 4: out.append('%s.f%d' % (objs.label(u16(pl, 0)), n))
            else: out.append('%s.f%d' % (OBJ_TYPES.get(t, t), n))
        else:
            out.append('%s.f%d' % (OBJ_TYPES.get(t, t), n))
        pos += max(size, 4)
    return ' '.join(out)

def parse_param(code, d, objs):
    try:
        if code == 1: return 'obj %s' % objs.label(u16(d, 2))
        if code in (2, 42): return 'time %dms loops=%d%s' % (i32(d, 0), i32(d, 4), (' cmp=' + CMP.get(i16(d, 8), '?')) if len(d) >= 10 else '')
        if code in (3, 4, 10, 11, 12, 17, 26, 31, 43, 57, 58, 60, 61): return 'short %d' % i16(d, 0)
        if code in (5, 25, 29, 34, 48, 56, 67, 70): return 'int %d' % i32(d, 0)
        if code in (6, 7, 35, 36): return 'sample #%d "%s"' % (i16(d, 0), cstr(d[4:]))
        if code == 13: return 'every %dms' % i32(d, 0)
        if code in (14, 44): return 'key %d' % u16(d, 0)
        if code in (15, 22, 23, 27, 28, 45, 46, 52, 53, 54, 59, 62):
            return 'expr %s %s' % (CMP.get(i16(d, 0), '?'), parse_expr(d[2:], objs))
        if code == 16: return 'pos x=%d y=%d dir=%d layer=%d parent=%s' % (i16(d, 4), i16(d, 6), i32(d, 12), i16(d, 20), objs.label(u16(d, 0)))
        if code in (9, 21):
            return 'create %s at x=%d y=%d layer=%d' % (objs.label(u16(d, 24)), i16(d, 4), i16(d, 6), i16(d, 20)) if len(d) >= 26 else 'create ' + d.hex()
        if code == 18: return 'shoot ' + d.hex()
        if code == 19: return 'zone (%d,%d)-(%d,%d)' % struct.unpack_from('<4h', d, 0)
        if code == 24: return 'color #%02x%02x%02x' % (d[0], d[1], d[2])
        if code == 50: return 'altvalue #%d' % i16(d, 0)
        if code == 49: return 'global #%d' % i16(d, 4)
        if code in (41, 64, 40): return 'str "%s"' % cstr(d)
        if code in (47, 51): return 'two %d,%d' % (i16(d, 0), i16(d, 2))
        if code == 32: return 'click btn=%d double=%d' % (d[0], d[1])
        if code == 38: return 'group id=%d' % u16(d, 2)
        if code == 39: return 'groupptr id=%d' % i16(d, 4)
    except Exception as e:
        return 'p%d?%s' % (code, d.hex())
    return 'p%d:%s' % (code, d.hex())

def parse_item(b, o, is_cond, objs):
    sz = u16(b, o)
    t, n = i8(b, o + 2), i8(b, o + 3)
    info, lst = u16(b, o + 4), i16(b, o + 6)
    fl, ofl, np_, dt = b[o + 8], b[o + 9], b[o + 10], b[o + 11]
    hdr = 14 if is_cond else 12
    ident = i16(b, o + 12) if is_cond else None
    pos = o + hdr; params = []
    for _ in range(np_):
        psz = u16(b, pos); code = i16(b, pos + 2)
        params.append(parse_param(code, b[pos + 4: pos + psz], objs)); pos += psz
    if pos != o + sz: raise ValueError('размер условия/действия: ожидалось %d, получено %d' % (sz, pos - o))
    return dict(type=t, num=n, info=info, lst=lst, flags=fl, oflags=ofl, dt=dt, ident=ident, params=params, size=sz)

def fmt_item(it, is_cond, objs):
    t = it['type']
    if t >= 2 or t == -7 and it['info'] != 0xFFFF:
        who = objs.label(it['info'])
    else:
        who = ''
    names = COND_NAMES if is_cond else ACT_NAMES
    nm = names.get((t, it['num']), '')
    neg = ' NOT' if is_cond and (it['flags'] & 1) else ''
    s = '%s%s %s:%d%s' % (who + ' ' if who else '', neg, OBJ_TYPES.get(t, t), it['num'], (' (' + nm + ')') if nm else '')
    if it['params']: s += '  ' + ' | '.join(it['params'])
    return s

def parse_events(b, objs):
    if b[:4] != b'ER>>': raise ValueError('нет ER>>')
    qc = i16(b, 44); pos = 46 + 4 * qc; groups = []
    hdr = dict(maxobj=i16(b, 4), maxinfo=i16(b, 6), players=i16(b, 8))
    while pos + 4 <= len(b):
        tag = b[pos:pos + 4]; pos += 4
        if tag == b'<<ER': break
        if tag in (b'ERes', b'ERop'): pos += 4; continue
        if tag != b'ERev': raise ValueError('неизвестный тег %r на %d' % (tag, pos - 4))
        size = i32(b, pos); pos += 4; end = pos + size
        while pos < end:
            g = pos; gs = abs(i16(b, g)); nc, na = b[g + 2], b[g + 3]; flags = u16(b, g + 4)
            ident = i16(b, g + 10); p = g + 14; conds = []; acts = []
            for _ in range(nc):
                it = parse_item(b, p, True, objs); conds.append(it); p += it['size']
            for _ in range(na):
                it = parse_item(b, p, False, objs); acts.append(it); p += it['size']
            if p != g + gs: raise ValueError('размер группы: ожидалось %d, получено %d' % (gs, p - g))
            groups.append(dict(flags=flags, ident=ident, conds=conds, acts=acts)); pos = g + gs
    return hdr, groups

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    out = sys.argv[1]
    objs = Objects(os.path.join(out, 'objects'))
    ld = os.path.join(out, 'logic'); os.makedirs(ld, exist_ok=True)
    refs = collections.Counter(); bad = 0; total_groups = 0
    fdir = os.path.join(out, 'frames')
    for fn in sorted(os.listdir(fdir)):
        p = os.path.join(fdir, fn, 'events.bin')
        if not os.path.exists(p): continue
        b = open(p, 'rb').read()
        try:
            hdr, groups = parse_events(b, objs)
        except Exception as e:
            print('!! %s: %s' % (fn, e)); bad += 1; continue
        total_groups += len(groups)
        lines = ['# кадр %s: групп событий=%d (объектов макс.=%d, инфо=%d, игроков=%d)' % (fn, len(groups), hdr['maxobj'], hdr['maxinfo'], hdr['players']), '']
        for i, g in enumerate(groups):
            lines.append('[#%d] flags=0x%04X id=%d' % (i, g['flags'], g['ident']))
            for c in g['conds']:
                lines.append('   IF  ' + fmt_item(c, True, objs))
                if c['type'] >= 2: refs[c['info']] += 1
            for a in g['acts']:
                lines.append('   DO  ' + fmt_item(a, False, objs))
                if a['type'] >= 2: refs[a['info']] += 1
            lines.append('')
        open(os.path.join(ld, fn + '.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    with open(os.path.join(ld, '_objects.txt'), 'w', encoding='utf-8') as f:
        f.write('# номер; тип; имя; сколько раз упомянут в условиях/действиях (по всем кадрам)\n')
        for h in sorted(objs.info):
            t, n = objs.info[h]
            f.write('%4d; %-9s; %-30s; %d\n' % (h, OBJ_TYPES.get(t, t), n, refs.get(h, 0)))
    print('Готово: групп событий %d, кадров с ошибками разбора %d. Смотрите %s' % (total_groups, bad, ld))

if __name__ == '__main__':
    main()
