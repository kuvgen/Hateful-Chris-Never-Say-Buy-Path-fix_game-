#!/usr/bin/env python3
"""hc_sounds.py - переводит звуки из out/banks/sounds/*.rec в обычные .wav
Запуск:  python hc_sounds.py out
Формат записи звука (выяснен по summary.txt):
   0  u32 метка, 6 u32 размер остатка, 18 u32 длина имени (с нулями)
  22  имя, затем WAVEFORMATEX (18 байт + cbSize доп. байт), u32 длина данных, данные
"""
import os, re, struct, sys

def rec_to_wav(rec):
    nl = struct.unpack_from('<I', rec, 18)[0]
    name = rec[22:22 + nl].split(b'\0')[0].decode('cp1251', 'replace')
    p = 22 + nl
    tag, ch, rate, avg, align, bits, cb = struct.unpack_from('<HHIIHHH', rec, p)
    fmt = rec[p:p + 18 + cb]
    dl = struct.unpack_from('<I', rec, p + 18 + cb)[0]
    data = rec[p + 18 + cb + 4: p + 18 + cb + 4 + dl]
    fmt_chunk = b'fmt ' + struct.pack('<I', len(fmt)) + fmt
    if len(fmt) & 1: fmt_chunk += b'\0'
    body = b'WAVE' + fmt_chunk + b'data' + struct.pack('<I', len(data)) + data + (b'\0' if len(data) & 1 else b'')
    return name, (tag, ch, rate, bits), b'RIFF' + struct.pack('<I', len(body)) + body

def main():
    out = sys.argv[1]; d = os.path.join(out, 'banks', 'sounds'); n = 0
    lines = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.rec'): continue
        try:
            name, info, wav = rec_to_wav(open(os.path.join(d, fn), 'rb').read())
        except Exception as e:
            print(fn, 'ошибка', e); continue
        safe = re.sub(r'[^\w\-. ]', '_', name) or 'noname'
        path = os.path.join(d, '%s_%s.wav' % (fn[:-4], safe))
        open(path, 'wb').write(wav); n += 1
        lines.append('%s  %s  fmt=%d ch=%d rate=%d bits=%d  %d байт' % (fn, name, info[0], info[1], info[2], info[3], len(wav)))
    open(os.path.join(d, '_sounds.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('готово, wav-файлов:', n)

if __name__ == '__main__':
    main()
