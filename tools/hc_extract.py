#!/usr/bin/env python3
"""hc_extract.py - извлекатель данных игры Clickteam (Click & Create / TGF, формат PAME 0x0300).

Запуск:   python hc_extract.py "D:\\Games\\Hateful Chris\\HCNSB.exe" out
Результат (папка out):
   summary.txt            - сводка: все блоки верхнего уровня, кадры, банки
   header/                - служебные блоки (заголовок, название, строки, список расширений ...)
   frames/NNN_<имя>/      - кадры (уровни): header.bin, palette.pal(+png), objects.bin (расстановка), events.bin (события)
   objects/NNNN_*.bin     - банк объектов (определения героя, врагов и т.д.)
   banks/<имя>/NNNNN.bin  - элементы банков (картинки, звуки ...) в сыром виде + samples/
Распаковка блоков - hcinflate.py (должен лежать рядом).
"""
import os, re, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hcinflate import inflate, InflateError
import hcimage

BANK_NAMES = {0x6666: 'images', 0x6667: 'fonts', 0x6668: 'sounds', 0x6669: 'music'}
OFFS_NAMES = {0x5555: 'images', 0x5556: 'fonts', 0x5557: 'sounds', 0x5558: 'music'}
LAST = 0x7F7F

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def decode_chunk(fl, body):
    """flags bit0 = данные сжаты: u32 размер после распаковки + поток."""
    if fl & 1:
        size = u32(body, 0)
        raw = inflate(body[4:])
        if len(raw) != size:
            raise InflateError('размер %d != %d' % (len(raw), size))
        return raw
    return body

def chunks(buf, off, end, stop=True):
    while off + 8 <= end:
        cid, fl, sz = struct.unpack_from('<HHI', buf, off)
        if off + 8 + sz > end:
            yield off, cid, fl, sz, None      # обрезан
            return
        yield off, cid, fl, sz, buf[off + 8: off + 8 + sz]
        off += 8 + sz
        if stop and cid == LAST: return

def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f: f.write(data)

def safe(name):
    return re.sub(r'[^\w\-. ]', '_', name).strip() or 'noname'

def find_pame(data):
    for m in re.finditer(b'PAME\x00\x03', data):
        o = m.start()
        if o + 18 <= len(data) and u16(data, o + 16) == 0x2223:
            return o
    return 0 if data[:4] == b'PAME' else -1

def write_pal(path, entries):
    """entries: 256 x (r,g,b)"""
    with open(path, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', 4 + 8 + 4 + len(entries) * 4) + b'PAL data' +
                struct.pack('<IHH', 4 + len(entries) * 4, 0x300, len(entries)) +
                b''.join(bytes((r, g, b, 0)) for r, g, b in entries))

def sound_to_wav(rec):
    """Запись звука: 22-байтный заголовок (u32 размер имени на смещении 18), имя, затем WAVEFORMATEX(18+cbSize) + u32 длина + данные."""
    try:
        nl = u32(rec, 18); name = rec[22:22 + nl].split(b'\0')[0].decode('cp1251', 'replace')
        blob = rec[22 + nl:]
        cb = u16(blob, 16); fmt = blob[:18 + cb]; dlen = u32(blob, 18 + cb)
        data = blob[22 + cb: 22 + cb + dlen]
        if len(data) != dlen or u16(fmt, 0) not in (1, 2, 17): return None
        riff = b'WAVE' + b'fmt ' + struct.pack('<I', len(fmt)) + fmt + (b'\0' if len(fmt) & 1 else b'') + b'data' + struct.pack('<I', len(data)) + data
        return name, b'RIFF' + struct.pack('<I', len(riff)) + riff
    except Exception:
        return None

def process_bank(name, body, out, log):
    """Банк: u32 число элементов, затем элементы [u32 handle][u32 размер][сжатый поток]."""
    count = u32(body, 0); pos = 4; n = 0; okc = 0; fails = 0
    log('  банк %s: заявлено элементов=%d, байт=%d' % (name, count, len(body)))
    d = os.path.join(out, 'banks', name); os.makedirs(d, exist_ok=True)
    meta = open(os.path.join(d, '_index.csv'), 'w', encoding='utf-8')
    meta.write('handle;width;height;flags;hot_x;hot_y;act_x;act_y;file\n')
    fmts = {}
    while pos + 8 <= len(body) and n < count:
        handle, size = struct.unpack_from('<II', body, pos)
        if size > 64_000_000: log('    !! подозрительный размер %d на смещении %d' % (size, pos)); break
        try:
            rec, used = inflate(body[pos + 8: pos + 8 + size * 2 + 256], expected=size, want_pos=True)
            if len(rec) != size: raise InflateError('размер')
        except Exception as ex:
            log('    !! элемент %d (handle %d) не распакован: %s' % (n, handle, ex)); fails += 1; break
        pos += 8 + used; n += 1
        fn = '%05d' % handle
        if name == 'images':
            im = hcimage.parse(rec); fmts[hex(im['flags'])] = fmts.get(hex(im['flags']), 0) + 1
            res = hcimage.to_rgba(im)
            if res:
                hcimage.png_rgba(os.path.join(d, fn + '.png'), *res); okc += 1
                fn += '.png'
            else:
                save(os.path.join(d, fn + '.rec'), rec); fn += '.rec'
            meta.write('%d;%d;%d;0x%X;%d;%d;%d;%d;%s\n' % ((handle, im['w'], im['h'], im['flags']) + im['hot'] + im['act'] + (fn,)))
        elif name == 'sounds':
            wav = sound_to_wav(rec)
            if wav:
                sname, data = wav; fn = '%05d_%s.wav' % (handle, safe(sname)); save(os.path.join(d, fn), data); okc += 1
            else:
                save(os.path.join(d, fn + '.rec'), rec); fn += '.rec'
            meta.write('%d;;;;;;;;%s\n' % (handle, fn))
        else:
            save(os.path.join(d, fn + '.rec'), rec); fn += '.rec'
            if n <= 3: log('    элемент %d handle=%d: %d байт: %s' % (n, handle, len(rec), rec[:64].hex(' ')))
            meta.write('%d;;;;;;;;%s\n' % (handle, fn))
    meta.close()
    log('  банк %s: распаковано элементов=%d, преобразовано в png/wav=%d, ошибок=%d%s' % (name, n, okc, fails, (', форматы картинок: ' + str(fmts)) if fmts else ''))
    return n

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    exe, out = sys.argv[1], sys.argv[2]
    data = open(exe, 'rb').read()
    base = find_pame(data)
    if base < 0:
        print('Не найден заголовок PAME'); sys.exit(2)
    os.makedirs(out, exist_ok=True)
    S = []                       # строки summary
    def log(s=''):
        print(s); S.append(s)
    log('файл: %s  размер: %d  PAME на смещении 0x%X' % (os.path.basename(exe), len(data), base))
    log('заголовок: ' + data[base:base + 16].hex(' '))
    pos = base + 16
    log('\n== блоки верхнего уровня (смещение, id, флаги, размер) ==')
    frame_no = 0
    bank_start = {}              # id банка -> смещение начала данных
    top = []
    bad = 0
    for off, cid, fl, sz, body in chunks(data, pos, len(data)):
        top.append((off, cid, fl, sz))
        if body is None:
            log('  0x%08X id=%04X fl=%d size=%d  (ОБРЕЗАН)' % (off, cid, fl, sz)); break
        tag = ''
        try:
            if cid == 0x2229:                                    # банк объектов
                n = u32(body, 0); tag = 'банк объектов, объектов=%d' % n
                idx = -1; cur = {}
                for o2, c2, f2, s2, b2 in chunks(body, 4, len(body), stop=False):
                    if b2 is None: break
                    if c2 == 0x4444:
                        idx += 1
                    try:
                        r = decode_chunk(f2, b2)
                    except Exception as e:
                        r = b2; bad += 1
                    save(os.path.join(out, 'objects', '%04d_%04X.bin' % (max(idx, 0), c2)), r)
            elif cid == 0x3333:                                  # кадр
                name = 'frame'; w = h = None; items = []
                subs = {}
                for o2, c2, f2, s2, b2 in chunks(body, 0, len(body)):
                    if b2 is None: break
                    try: r = decode_chunk(f2, b2)
                    except Exception: r = b2; bad += 1
                    subs[c2] = r
                if 0x3335 in subs: name = subs[0x3335].split(b'\0')[0].decode('cp1251', 'replace')
                if 0x3334 in subs and len(subs[0x3334]) >= 4: w, h = u16(subs[0x3334], 0), u16(subs[0x3334], 2)
                d = os.path.join(out, 'frames', '%03d_%s' % (frame_no, safe(name)))
                names = {0x3334: 'header.bin', 0x3338: 'objects.bin', 0x333D: 'events.bin', 0x3337: 'palette.bin'}
                for c2, r in subs.items():
                    save(os.path.join(d, names.get(c2, '%04X.bin' % c2)), r)
                if 0x3337 in subs and len(subs[0x3337]) >= 1028:
                    p = subs[0x3337]; ent = [(p[4 + 4 * i], p[5 + 4 * i], p[6 + 4 * i]) for i in range(256)]
                    write_pal(os.path.join(d, 'palette.pal'), ent)
                tag = 'кадр #%d "%s" %sx%s, объекты=%d б, события=%d б' % (
                    frame_no, name, w, h, len(subs.get(0x3338, b'')), len(subs.get(0x333D, b'')))
                frame_no += 1
            elif cid in BANK_NAMES:
                bank_start[cid] = off + 8
                tag = 'БАНК %s, %d байт' % (BANK_NAMES[cid], sz)
                log('  0x%08X id=%04X fl=%d size=%d  %s' % (off, cid, fl, sz, tag))
                process_bank(BANK_NAMES[cid], body, out, log)
                continue
            elif cid in OFFS_NAMES:
                r = decode_chunk(fl, body)
                tag = 'таблица смещений %s: %d записей' % (OFFS_NAMES[cid], len(r) // 4)
                save(os.path.join(out, 'banks', OFFS_NAMES[cid] + '_offsets.bin'), r)
            else:
                r = decode_chunk(fl, body)
                save(os.path.join(out, 'header', '%04X_%d.bin' % (cid, len(top))), r)
                txt = r[:200]
                if re.fullmatch(rb'[\x20-\x7e\x00\x80-\xff\t\r\n]*', txt) and len(txt) > 1:
                    tag = 'текст: ' + txt.split(b'\0')[0].decode('cp1251', 'replace')[:60]
                else:
                    tag = 'данные %d байт: %s' % (len(r), r[:24].hex(' '))
        except Exception as e:
            tag = 'ОШИБКА: %s' % e; bad += 1
        log('  0x%08X id=%04X fl=%d size=%d  %s' % (off, cid, fl, sz, tag))
        if cid == LAST: break
    log('\nошибок распаковки: %d' % bad)
    with open(os.path.join(out, 'summary.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(S))
    print('\nГотово. Сводка: %s' % os.path.join(out, 'summary.txt'))

if __name__ == '__main__':
    main()
