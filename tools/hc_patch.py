#!/usr/bin/env python3
"""hc_patch.py - патчер HCNSB.exe (Злобный Крис 2). Исходный файл НЕ меняется: результат пишется в новый файл.

Запуск (hcinflate.py должен лежать рядом; всегда на ОРИГИНАЛЬНОМ exe, не на уже пропатченном):
  cd "path\\to\\repo\\tools"
  python hc_patch.py "D:\\Games\\Hateful Chris\\HCNSB.exe" "D:\\Games\\Hateful Chris\\HCNSB_patched.exe" --knife-bonus 5 --inventory --hud --fix-story --windowed
Параметры (любое сочетание):
  --knife-bonus N   добавить N к урону ножа (Knife, анимация 19 героя "Melee Chris"); по умолчанию 0
  --inventory       пока открыт инвентарь: игра на паузе, объекты уровня скрыты
  --hud             (с --inventory) прятать и верхнюю панель: шкалы, слоты оружия, патроны
  --no-pause        (с --inventory) только прятать объекты, логику не останавливать (для отладки)
  --hide-name ИМЯ   (с --inventory) дополнительно прятать объект с этим именем; можно несколько раз
  --fix-story       сюжет: выдавать Liposuction при взятии миссии Убера; похищение Трикси при 4..8 миссиях (было 4..5)
  --windowed        запуск в окне 800x600 с рамкой, Alt+Enter - полный экран
  --dry-run         только показать, что будет изменено, файл не писать
Ожидаемый вывод: «Liposuction добавлена в 2 событий», «исправлено в 1», «Окно: флаги заголовка 0xAC9A -> 0xB498».
Результат положите в папку игры рядом с inventory.ccn (под другим именем, например HCNSB_patched.exe) и запустите.
Как это работает: события каждого кадра хранятся в сжатом блоке 0x333D. Патчер распаковывает его, меняет группы событий,
записывает блок без сжатия (так хранит свои блоки и inventory.ccn) и пересобирает контейнер. Таблицы смещений картинок
и звуков относительные внутри своих банков, поэтому смена размера блоков событий им не мешает.
"""
import argparse, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hcinflate import inflate

LAST = 0x7F7F


def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def i16(b, o): return struct.unpack_from('<h', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]
def i32(b, o): return struct.unpack_from('<i', b, o)[0]


def find_pame(data):
    import re
    for m in re.finditer(b'PAME\x00\x03', data):
        o = m.start()
        if o + 18 <= len(data) and u16(data, o + 16) == 0x2223:
            return o
    return 0 if data[:4] == b'PAME' else -1


def read_chunks(buf, off, end):
    """[(cid, flags, body)] до 0x7F7F включительно (для вложенных - до конца)"""
    res = []
    while off + 8 <= end:
        cid, fl, sz = struct.unpack_from('<HHI', buf, off)
        res.append((cid, fl, buf[off + 8: off + 8 + sz]))
        off += 8 + sz
        if cid == LAST: break
    return res, off


def pack_chunk(cid, fl, body):
    return struct.pack('<HHI', cid, fl, len(body)) + body


def decode(fl, body):
    if fl & 1:
        size = u32(body, 0)
        raw = inflate(body[4:])
        if len(raw) != size: raise ValueError('размер после распаковки не совпал')
        return raw
    return body


# ---------------------------------------------------------------- события
class Item:
    """условие или действие; raw - байты целиком"""
    def __init__(self, raw, is_cond):
        self.raw = bytearray(raw); self.is_cond = is_cond
    type = property(lambda s: struct.unpack_from('<b', s.raw, 2)[0])
    num = property(lambda s: struct.unpack_from('<b', s.raw, 3)[0])
    info = property(lambda s: u16(s.raw, 4))
    np = property(lambda s: s.raw[10])
    def set_info(self, v): struct.pack_into('<H', self.raw, 4, v)
    def set_num(self, v): struct.pack_into('<b', self.raw, 3, v)
    def params(self):
        pos = 14 if self.is_cond else 12; res = []
        for _ in range(self.np):
            psz = u16(self.raw, pos); code = i16(self.raw, pos + 2)
            res.append((code, pos, psz)); pos += psz
        return res


class Group:
    def __init__(self, raw):
        gs = abs(i16(raw, 0)); self.neg = i16(raw, 0) < 0
        nc, na = raw[2], raw[3]
        self.head = bytearray(raw[:14]); p = 14
        self.conds, self.acts = [], []
        for k in range(nc + na):
            sz = u16(raw, p)
            it = Item(raw[p:p + sz], k < nc); (self.conds if k < nc else self.acts).append(it); p += sz
        if p != gs: raise ValueError('размер группы не сходится')
        self.changed = False
    def ident_value(self): return i16(self.head, 10)
    def to_bytes(self):
        body = b''.join(bytes(i.raw) for i in self.conds + self.acts)
        n = 14 + len(body)
        if n > 32767: raise ValueError('группа слишком большая')
        h = bytearray(self.head)
        struct.pack_into('<h', h, 0, -n if self.neg else n)
        h[2] = len(self.conds); h[3] = len(self.acts)
        return bytes(h) + body


class Events:
    def __init__(self, b):
        if b[:4] != b'ER>>': raise ValueError('нет ER>>')
        qc = i16(b, 44); pos = 46 + 4 * qc
        self.head = b[:pos]; self.parts = []   # ('raw', bytes) | ('ev', [Group])
        while pos + 4 <= len(b):
            tag = b[pos:pos + 4]
            if tag == b'<<ER':
                self.tail = b[pos:]; break
            if tag in (b'ERes', b'ERop'):
                self.parts.append(('raw', b[pos:pos + 8])); pos += 8; continue
            if tag != b'ERev': raise ValueError('неизвестный тег')
            size = i32(b, pos + 4); end = pos + 8 + size; p = pos + 8; groups = []
            while p < end:
                gs = abs(i16(b, p)); groups.append(Group(b[p:p + gs])); p += gs
            if p != end: raise ValueError('размер ERev')
            self.parts.append(('ev', groups)); pos = end
        else:
            raise ValueError('нет <<ER')
    def groups(self):
        for k, v in self.parts:
            if k == 'ev':
                for g in v: yield g
    def to_bytes(self):
        out = [self.head]; blocks = []
        for k, v in self.parts:
            if k == 'raw': out.append(v)
            else:
                body = b''.join(g.to_bytes() for g in v)
                out.append(b'ERev' + struct.pack('<i', len(body)) + body); blocks.append(len(body))
        # 'ERes' хранит суммарный размер всех блоков ERev (проверено на всех 68 кадрах) - движок выделяет под него память
        for i, x in enumerate(out):
            if x[:4] == b'ERes' and len(x) == 8: out[i] = b'ERes' + struct.pack('<i', sum(blocks))
        out.append(self.tail)
        return b''.join(out)


def expr_const_offset(it, param_index):
    """смещение i32-константы в выражении параметра (если выражение - одна константа), иначе None"""
    code, pos, psz = it.params()[param_index]
    d = pos + 4
    e = d + 2                       # после оператора сравнения
    t, n = struct.unpack_from('<bb', it.raw, e)
    if t != -1 or n != 0: return None
    size = u16(it.raw, e + 2)
    nxt = e + size
    if it.raw[nxt:nxt + 2] != b'\0\0': return None
    return e + 4


NAMES = {}


def patch_knife(groups, bonus, ids, rep):
    """урон ножа: группа с условием Melee Chris(78) анимация == 19; действие Active:33 altvalue #0 expr == N -> N+bonus"""
    n = 0
    for g in groups:
        if not any(c.type == 2 and c.num == -3 and c.info == ids['Melee Chris'] and c.np == 1 and
                   i16(c.raw, 14 + 4) == 19 for c in g.conds):
            continue
        for a in g.acts:
            if a.type == 2 and a.num == 33 and a.np == 2:
                p = a.params()
                if p[0][0] != 50 or i16(a.raw, p[0][1] + 4) != 0: continue
                off = expr_const_offset(a, 1)
                if off is None: continue
                old = i32(a.raw, off)
                struct.pack_into('<i', a.raw, off, old + bonus); g.changed = True; n += 1
    rep['knife'] = rep.get('knife', 0) + n


# Видимые при старте Active-объекты кадра (NPC, вывески, стрелки), которые прячем на время инвентаря.
# Служебные зоны, сенсоры, снаряды и эффекты не трогаем: их игра рисует прозрачными или уничтожает при открытии.
import re
ZONE_RE = re.compile(r'sensor|wall|zone|killer|maker|gutter|pylon|window|hole|locator|scroller|backdrop|splat|part\d|blood|'
                     r'smoke|flame|puff|explosion|bullet|projectile|rocket|bomb|bottle|star|nail|syringe|popsicle|tomahawk|egg|milk|'
                     r'trail|impact|gerbil|skeleton|puke|virus|pill|item|dollar|loading|berserk|chris|mech|tnt|colorcopy|label', re.I)
# Эффекты оружия (дым, вспышки, взрывы, кровь) создаются во время игры и остаются на экране замороженными - прячем и их.
EFFECT_RE = re.compile(r'smoke|puff|cloud|explosion|blast|flame|impact|splat|blood|puke|part\d|trail|skeleton|bullet|projectile', re.I)
SKIP_HIDE = {'Sublocator', 'subapp scroller', 'colorcopy', 'Melee Chris', 'Ammo Chris', 'Throwing Chris',
             'Beserker Chris', 'Chris Mech', 'Mech', 'chris angel', 'Item mover'}


EXTRA_HIDE = set()    # имена объектов, которые пользователь просит прятать принудительно (--hide-name)
HUD_COUNTERS = {'Life Bone', 'Life Meter', 'Equipped Weapon 4', 'Equipped Weapon 5', 'Equipped Weapon 6', 'Ammo Counter',
                "Beserk 'o' Meter", "Moon 'o' Meter"}


def make_counter_cond(src, obj, op, val):
    c = Item(src.raw, True); c.set_info(obj); struct.pack_into('<h', c.raw, 12, 0)    # ident
    code, pos, psz = c.params()[0]
    struct.pack_into('<h', c.raw, pos + 4, op)
    off = expr_const_offset(c, 0)
    if off is None: return None
    struct.pack_into('<i', c.raw, off, val)
    return c


# ---------------------------------------------------------------- исправления сюжета (v13)
def act_string(a):
    """строка в действии расширения ini (32:48 раздел / 32:49 ключ), иначе None"""
    try:
        if a.np != 1: return None
        code, pos, psz = a.params()[0]
        e = pos + 6
        if a.raw[e:e + 2] != b'\xff\x03': return None
        n = u16(a.raw, e + 2)
        return bytes(a.raw[e + 4:e + n]).split(b'\0')[0].decode('cp1251', 'replace')
    except (struct.error, IndexError):
        return None


def act_const(a):
    """целая константа в действии 32:50 (значение ключа), иначе None"""
    try:
        if a.np != 1: return None
        off = expr_const_offset(a, 0)
        return None if off is None else struct.unpack_from('<i', a.raw, off)[0]
    except (struct.error, IndexError):
        return None


def make_string_act(tmpl, text):
    """копия действия-шаблона (32:48/32:49) с другой строкой"""
    sb = text.encode('cp1251') + b'\0'
    if len(sb) & 1: sb += b'\0'
    item = b'\xff\x03' + struct.pack('<H', 4 + len(sb)) + sb
    expr = b'\0\0' + item + b'\0\0'
    code, pos, psz = tmpl.params()[0]
    param = struct.pack('<Hh', 4 + len(expr), code) + expr
    raw = bytearray(tmpl.raw[:pos]) + param
    struct.pack_into('<H', raw, 0, len(raw))
    return Item(bytes(raw), False)


def patch_lipo(groups, rep):
    """Миссия Убера: при взятии (ключ quest2 = 1 + переход в кадр диалога) выдать Liposuction (weapons/lipo = 1).
    В оригинале её не выдают нигде, а в BumVilla засчитываются только её удары."""
    for g in groups:
        acts = g.acts
        if not any(a.type == -3 and a.num == 2 for a in acts): continue
        if any(act_string(a) == 'lipo' for a in acts): continue
        hit = None
        for i in range(len(acts) - 1):
            a, b = acts[i], acts[i + 1]
            if a.type == 32 and a.num == 49 and act_string(a) == 'quest2' and b.type == 32 and b.num == 50 and act_const(b) == 1:
                hit = (a, b)
        if not hit: continue
        sec = next((a for a in acts if a.type == 32 and a.num == 48 and act_string(a) is not None), None)
        if sec is None: continue
        g.acts += [make_string_act(sec, 'weapons'), make_string_act(hit[0], 'lipo'), Item(bytes(hit[1].raw), False)]
        g.changed = True
        rep['lipo'] = rep.get('lipo', 0) + 1


def patch_abduct(groups, info, rep, upto=8):
    """Klubkix: похищение Трикси срабатывает при quests 4..5 - расширяем до 4..upto, иначе с 6+ миссиями сюжет встаёт."""
    for g in groups:
        if not any(a.type == -3 and a.num == 2 for a in g.acts): continue
        qc = [c for c in g.conds if c.type == 7 and c.num == -49 and info.get(c.info, (0, ''))[1] == 'Quests']
        if len(qc) != 2: continue
        for c in qc:
            code, pos, psz = c.params()[0]
            op = i16(c.raw, pos + 4)
            off = expr_const_offset(c, 0)
            if off is None: continue
            if op == 2 and struct.unpack_from('<i', c.raw, off)[0] == 5:
                struct.pack_into('<i', c.raw, off, upto)
                g.changed = True
                rep['abduct'] = rep.get('abduct', 0) + 1


def patch_inventory(ev, groups, ids, info, instances, rep, pause=True, hud=False):
    """Пауза игры на время инвентаря:
    1) открытие (SubApp:1) - скрыть врагов и все статичные видимые объекты кадра, закрытие (SubApp:3) - показать их;
    2) все остальные группы событий получают условие "game or inv == 0" (логика стоит, пока инвентарь открыт)."""
    gi = ids.get('game or inv'); lm = ids.get('Life Meter'); me = ids.get('Mechenable')
    if gi is None: return
    open_g = close_g = None
    for g in groups:
        if any(a.type == 9 and a.num == 1 for a in g.acts) and any(a.type == 7 and a.info == gi and a.num == 48 for a in g.acts):
            open_g = g
        if any(a.type == 9 and a.num == 3 for a in g.acts) and any(a.type == 7 and a.info == gi and a.num == 48 for a in g.acts):
            close_g = g
    if open_g is None or close_g is None: rep['inv_skipped'] = rep.get('inv_skipped', 0) + 1; return
    # --- что скрывать
    toggled = {a.info for g in groups for a in g.acts if a.type == 2 and a.num in (26, 27)}
    hide = []
    for a in open_g.acts:                       # враги: те, кому при открытии задаётся altvalue #1
        if a.type == 2 and a.num == 31 and a.np == 2 and a.params()[0][0] == 50 and i16(a.raw, a.params()[0][1] + 4) == 1:
            if a.info not in hide: hide.append(a.info)
    # героя берём из условия открытия ("Chris: анимация 0"), т.к. объектов с именем Chris в игре несколько
    chris = next((c.info for c in open_g.conds if c.type == 2 and c.num == -3 and c.np == 1 and i16(c.raw, 18) == 0), None)
    if chris is not None and chris in instances and chris not in hide:
        hide.append(chris)               # сам Крис: прячется только на время атак, при открытии инвентаря он на виду
    for h in sorted(set(instances)):            # видимые при старте Active кадра: NPC, вывески, стрелки
        t, name, vis, psz = info.get(h, (None, '', None, 0))
        if t == 2 and name in EXTRA_HIDE and h not in hide: hide.append(h); continue
        if re.match(r'active', name, re.I) and psz <= 200: continue      # безымянные заготовки на 170 байт - служебные
        if t == 2 and vis is not None and (vis & 0x08) == 0 and h not in toggled and h not in hide and name not in SKIP_HIDE and (not ZONE_RE.search(name) or EFFECT_RE.search(name)):
            hide.append(h)
    src = None
    for g in groups:
        src = next((c for c in g.conds if c.type == 7 and c.num == -49 and c.info == me and c.np == 1), None)
        if src: break
    if src is None: rep['inv_skipped'] = rep.get('inv_skipped', 0) + 1; return
    tmpl = next(a for a in open_g.acts if a.type == 2 and a.num == 24 and a.np == 0)
    for who, num in ((open_g, 26), (close_g, 27)):
        for e in hide:
            it = Item(tmpl.raw, False); it.set_num(num); it.set_info(e); who.acts.append(it)
        who.changed = True
    if hud:                                     # панель HUD: подложка (Active) и счётчики (Counter:26 скрыть / 27 показать)
        for h in sorted(set(instances)):
            t, name, vis, psz = info.get(h, (None, '', None, 0))
            if (t == 2 and name == 'Console backdrop') or (t == 7 and name in HUD_COUNTERS):
                for who, num in ((open_g, 26), (close_g, 27)):
                    it = Item(tmpl.raw, False); it.set_num(num); it.set_info(h)
                    if t == 7: struct.pack_into('<b', it.raw, 2, 7)
                    who.acts.append(it)
                rep['inv_hud'] = rep.get('inv_hud', 0) + 1
    # мигающие по таймеру объекты (пар из люка в Suburbs): их показом/скрытием управляет сама игра (Active:37 "мигание"),
    # поэтому при открытии просто прячем, а при закрытии ничего не возвращаем - игра сама покажет их при следующем цикле
    blink = sorted({x.info for g in groups for x in g.acts if x.type == 2 and x.num == 37 and x.info in instances})
    for e in blink:
        it = Item(tmpl.raw, False); it.set_num(26); it.set_info(e); open_g.acts.append(it)
    if blink: rep['inv_blink'] = rep.get('inv_blink', 0) + len(blink); open_g.changed = True
    # индикатор BERSERK: прячем при открытии, при закрытии возвращаем только если берсерк "заряжен" (Berserk Trigger == 1)
    bz = bt = None                              # объекты берём из группы, где включается индикатор (имена в игре повторяются)
    for g in groups:
        sh = [a for a in g.acts if a.type == 2 and a.num == 27 and info.get(a.info, (0, ''))[1] == 'Berserk']
        tr = [a for a in g.acts if a.type == 7 and a.num == 48 and info.get(a.info, (0, ''))[1] == 'Berserk Trigger']
        if sh and tr: bz, bt = sh[0].info, tr[0].info; break
    if bz is not None and bz in instances and bt is not None:
        it = Item(tmpl.raw, False); it.set_num(26); it.set_info(bz); open_g.acts.append(it)
        c_off = make_counter_cond(src, bt, 1, 1); c_on = make_counter_cond(src, bt, 0, 1)
        if c_off and c_on:
            clone = Group(close_g.to_bytes())
            close_g.conds.append(c_off)
            clone.conds.append(c_on)
            it = Item(tmpl.raw, False); it.set_num(27); it.set_info(bz); clone.acts.append(it)
            new_id = max(abs(x.ident_value()) for x in groups) + 1
            struct.pack_into('<h', clone.head, 10, new_id); clone.changed = True
            for k, v in ev.parts:
                if k == 'ev' and close_g in v: v.insert(v.index(close_g) + 1, clone); break
            rep['inv_berserk'] = rep.get('inv_berserk', 0) + 1
    rep['inv_hidden_types'] = rep.get('inv_hidden_types', 0) + len(hide)
    if not pause: return
    # --- пауза логики
    cnt = 0
    for g in groups:
        if g is open_g or g is close_g: continue
        if any(c.type == 9 for c in g.conds) or any(a.type == 9 for a in g.acts): continue          # всё про инвентарь
        if any(c.info in (ids.get('Sublocator'), ids.get('subapp scroller')) and c.type == 2 for c in g.conds): continue
        if any(a.info in (ids.get('Sublocator'), ids.get('subapp scroller')) and a.type == 2 for a in g.acts): continue   # они выставляют флаги закрытия инвентаря
        if any(c.type == -3 and c.num == -1 for c in g.conds): continue                               # старт кадра
        if any(c.type == -1 and c.num in (-10, -11) for c in g.conds): continue                       # маркеры групп
        if any(c.type == 7 and c.num in (-49,) and c.info == gi for c in g.conds): continue
        if any(a.type == 7 and a.info == gi for a in g.acts): continue
        c = Item(src.raw, True); c.set_info(gi); struct.pack_into('<h', c.raw, 12, 0)   # ident
        g.conds.append(c); g.changed = True; cnt += 1
    rep['inv_gated'] = rep.get('inv_gated', 0) + cnt


def objects_info(body):
    """номер объекта -> (тип, имя, байт 19 свойств (0x03 - объект виден при старте, 0xEB - скрыт)); имя -> номер"""
    ids = {}; info = {}; idx = -1; off = 4
    while off + 8 <= len(body):
        cid, fl, sz = struct.unpack_from('<HHI', body, off)
        b = body[off + 8: off + 8 + sz]
        try:
            if cid == 0x4444:
                idx += 1; info[idx] = [i16(decode(fl, b), 2), '', None, 0]
            elif cid == 0x4445:
                nm = decode(fl, b).split(b'\0')[0].decode('cp1251', 'replace'); ids.setdefault(nm, max(idx, 0)); info[max(idx, 0)][1] = nm
            elif cid == 0x4446:
                r = decode(fl, b)
                if len(r) > 19: info[max(idx, 0)][2] = r[19]
                info[max(idx, 0)][3] = len(r)
        except Exception:
            pass
        off += 8 + sz
    return ids, {k: tuple(v) for k, v in info.items()}


def frame_instances(b):
    """номера объектов, расставленных на кадре (блок 0x3338)"""
    n = u32(b, 0)
    return [u16(b, 4 + 12 * k + 2) for k in range(n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--knife-bonus', type=int, default=0)
    ap.add_argument('--inventory', action='store_true')
    ap.add_argument('--no-pause', action='store_true', help='с --inventory: только скрывать объекты, логику не останавливать')
    ap.add_argument('--hud', action='store_true', help='с --inventory: прятать и верхнюю панель HUD (шкалы, слоты оружия, патроны)')
    ap.add_argument('--hide-name', action='append', default=[], help='с --inventory: дополнительно прятать Active-объект с этим именем (можно несколько раз)')
    ap.add_argument('--fix-story', action='store_true', help='исправить сюжет: выдавать Liposuction в миссии Убера, похищение Трикси при 4..8 миссиях')
    ap.add_argument('--windowed', action='store_true', help='запускать игру в окне 800x600 (Alt+Enter - полный экран)')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    EXTRA_HIDE.update(a.hide_name)
    data = open(a.src, 'rb').read()
    base = find_pame(data)
    if base < 0: print('Не найден PAME'); sys.exit(2)
    top, end = read_chunks(data, base + 16, len(data))
    if end != len(data): print('Внимание: после 0x7F7F есть лишние данные (%d байт), они будут сохранены' % (len(data) - end))
    ids = {}; info = {}
    for cid, fl, body in top:
        if cid == 0x2229: ids, info = objects_info(body)
    need = ['Melee Chris', 'game or inv', 'Life Meter', 'Mechenable', 'Sublocator', 'subapp scroller']
    miss = [n for n in need if n not in ids]
    if miss: print('Не найдены объекты:', miss); sys.exit(3)
    rep = {}; out = [data[:base + 16]]; frames = 0
    for cid, fl, body in top:
        if cid == 0x3333:
            subs, _ = read_chunks(body, 0, len(body)); nb = []
            inst = []
            for c2, f2, b2 in subs:
                if c2 == 0x3338: inst = frame_instances(decode(f2, b2))
            for c2, f2, b2 in subs:
                if c2 == 0x333D:
                    ev = Events(decode(f2, b2)); gl = list(ev.groups())
                    if a.knife_bonus: patch_knife(gl, a.knife_bonus, ids, rep)
                    if a.inventory: patch_inventory(ev, gl, ids, info, inst, rep, not a.no_pause, a.hud)
                    if a.fix_story:
                        patch_lipo(gl, rep); patch_abduct(gl, info, rep)
                    if any(g.changed for g in gl):
                        b2 = ev.to_bytes(); f2 = 0; frames += 1
                    else:
                        nb.append(pack_chunk(c2, f2, b2)); continue
                nb.append(pack_chunk(c2, f2, b2))
            body = b''.join(nb)
        if cid == 0x2223 and a.windowed:
            # заголовок приложения: флаги u16 в начале. 0x0800 - полный экран при старте, 0x0002 - окно без заголовка,
            # 0x1000 - разрешить Alt+Enter (переключение окно/полный экран)
            hb = bytearray(decode(fl, body)); f0 = u16(hb, 0)
            f1 = (f0 & ~0x0800 & ~0x0002) | 0x1000
            struct.pack_into('<H', hb, 0, f1); body = bytes(hb); fl = 0
            print('Окно: флаги заголовка 0x%04X -> 0x%04X, размер %dx%d' % (f0, f1, u16(hb, 8), u16(hb, 10)))
        out.append(pack_chunk(cid, fl, body))
    out.append(data[end:])
    print('Изменено кадров: %d' % frames)
    print('Нож: изменено ударов в событиях: %d (бонус %+d)' % (rep.get('knife', 0), a.knife_bonus))
    if a.inventory:
        print('Инвентарь: объектов HUD %d, скрываемых типов объектов %d, групп событий с паузой %d, кадров пропущено %d' %
              (rep.get('inv_hud', 0), rep.get('inv_hidden_types', 0), rep.get('inv_gated', 0), rep.get('inv_skipped', 0)))
    if a.fix_story:
        print('Сюжет: Liposuction добавлена в %d событий (ожидается 2: Mall1 и Mall1a), условие похищения исправлено в %d (ожидается 1: Klubkix)' %
              (rep.get('lipo', 0), rep.get('abduct', 0)))
    if a.dry_run: return
    res = b''.join(out)
    open(a.dst, 'wb').write(res)
    print('Записано: %s (%d байт, было %d)' % (a.dst, len(res), len(data)))


if __name__ == '__main__':
    main()
