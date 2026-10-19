"""Декодер картинок банка Clickteam (формат из Cncs232.dll sub_10014393 + exe sub_409850).
Запись картинки в банке (после распаковки блока): 24-байтный заголовок + пиксели.
  0  u32 handle/метка
  4  u16 ?
  6  u32 размер пикселей
 10  u16 ширина, 12 u16 высота
 14  u16 флаги: бит0-3 формат пикселя (4=24бит, 6=15бит RGB555, 7=16бит RGB565, 8=32бит...), старший байт = режим RLE
 16  hotspot x,y (u16), 20 action point x,y (i16)
RLE (режимы 1/2/4 = 8/16/24 бит на пиксель): байт cmd; 0 = конец; бит7=0 -> повтор одного пикселя cmd раз;
бит7=1 -> (cmd&0x7F) пикселей идут подряд как есть.
"""
import struct, zlib

def rle(src, bpp):
    out = bytearray(); i = 0; n = len(src)
    while i < n:
        c = src[i]; i += 1
        if c == 0: break
        cnt = c & 0x7F
        if c & 0x80:
            out += src[i:i + cnt * bpp]; i += cnt * bpp
        else:
            out += src[i:i + bpp] * cnt; i += bpp
    return bytes(out)

def parse(rec):
    w, h, flags = struct.unpack_from('<HHH', rec, 10)
    hx, hy, ax, ay = struct.unpack_from('<HHhh', rec, 16)
    return dict(w=w, h=h, flags=flags, hot=(hx, hy), act=(ax, ay), size=struct.unpack_from('<I', rec, 6)[0], data=rec[24:])

def to_rgb(im):
    w, h, fl = im['w'], im['h'], im['flags']; fmt = fl & 15; mode = fl >> 8
    raw = im['data']
    bpp = {1: 1, 2: 2, 4: 3}.get(mode & 7)
    if bpp: raw = rle(raw, bpp)
    return raw

def png(path, w, h, rgb):
    def ch(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    rows = b''.join(b'\0' + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(rows)) + ch(b'IEND', b''))


_T555 = [bytes((((p >> 10) & 31) * 255 // 31, ((p >> 5) & 31) * 255 // 31, (p & 31) * 255 // 31, 0 if p == 0 else 255)) for p in range(32768)]
_T565 = [bytes((((p >> 11) & 31) * 255 // 31, ((p >> 5) & 63) * 255 // 63, (p & 31) * 255 // 31, 0 if p == 0 else 255)) for p in range(65536)]

def to_rgba(im):
    """-> (w, h, RGBA bytes) или None, если формат не поддержан. Чёрный (0) считается прозрачным - это догадка."""
    w, h, fl = im['w'], im['h'], im['flags']; fmt = fl & 15; mode = (fl >> 8) & 7
    raw = im['data']
    bpp = {1: 1, 2: 2, 4: 3}.get(mode)
    if bpp: raw = rle(raw, bpp)
    else:
        bpp = {6: 2, 7: 2, 4: 3, 8: 4}.get(fmt, None)
        if bpp is None: return None
    if len(raw) < w * h * bpp: return None
    if bpp == 2:
        px = struct.unpack_from('<%dH' % (w * h), raw, 0)
        t = _T565 if fmt == 7 else _T555
        return w, h, b''.join(map(t.__getitem__, px))
    if bpp == 3:
        return w, h, b''.join(bytes((raw[3 * i + 2], raw[3 * i + 1], raw[3 * i], 255)) for i in range(w * h))
    if bpp == 1:
        return w, h, b''.join(bytes((v, v, v, 255)) for v in raw[:w * h])
    return None

def png_rgba(path, w, h, rgba):
    def ch(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    rows = b''.join(b'\0' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) + ch(b'IDAT', zlib.compress(rows, 6)) + ch(b'IEND', b''))
