#!/usr/bin/env python3
"""hc_godot_export.py - собирает из результата hc_extract.py / hc_objects.py готовую папку ресурсов для Godot 4.

Запуск:   python hc_godot_export.py out hc_godot
   out       - папка, куда ранее запускали hc_extract.py (там banks/, objects/, frames/, data/objects.json, data/frames.json)
   hc_godot  - куда положить результат; его целиком копируют в проект Godot как res://hc/

Результат:
   sprites/<handle>.png          все картинки игры (прозрачность уже учтена)
   sounds/<handle>_<имя>.wav     все звуки
   data/images.json              handle -> размер, точка привязки (hot), точка действия (act)
   data/anims.json               объекты: имя, тип, движение, анимации -> направления -> кадры (handle картинок), скорость
   data/levels.json              уровни: размер, фон, расстановка объектов (с картинкой для Backdrop)
   data/sounds.json              handle -> имя -> файл
   data/flags.json               handle -> видим ли объект при старте уровня
   data/atlas_report.txt         сколько картинок/звуков найдено, чего не хватает
   import_hc.gd                  EditorScript для Godot: строит SpriteFrames (.tres) для всех анимированных объектов
"""
import csv, json, os, shutil, struct, sys

DIRS = {0: 'right', 8: 'up', 16: 'left', 24: 'down'}      # 32 направления Clickteam; остальные - диагонали/промежуточные


def main():
    if len(sys.argv) < 3: print(__doc__); sys.exit(1)
    out, dst = sys.argv[1], sys.argv[2]
    for sub in ('sprites', 'sounds', 'data'): os.makedirs(os.path.join(dst, sub), exist_ok=True)
    rep = []
    # --- картинки
    imgs = {}
    idx = os.path.join(out, 'banks', 'images', '_index.csv')
    if os.path.exists(idx):
        for r in csv.DictReader(open(idx, encoding='utf-8'), delimiter=';'):
            fn = r['file']
            if not fn.endswith('.png'): continue
            shutil.copyfile(os.path.join(out, 'banks', 'images', fn), os.path.join(dst, 'sprites', fn))
            imgs[int(r['handle'])] = dict(w=int(r['width']), h=int(r['height']), hot=[int(r['hot_x']), int(r['hot_y'])],
                                         act=[int(r['act_x']), int(r['act_y'])], file=fn)
    json.dump(imgs, open(os.path.join(dst, 'data', 'images.json'), 'w'), indent=1)
    rep.append('картинок (png): %d' % len(imgs))
    # --- звуки
    snd = {}
    idx = os.path.join(out, 'banks', 'sounds', '_index.csv')
    if os.path.exists(idx):
        for r in csv.DictReader(open(idx, encoding='utf-8'), delimiter=';'):
            fn = r['file']
            if not fn.endswith('.wav'): continue
            shutil.copyfile(os.path.join(out, 'banks', 'sounds', fn), os.path.join(dst, 'sounds', fn))
            nm = fn[6:-4]
            snd[int(r['handle'])] = dict(name=nm, file=fn)
    json.dump(snd, open(os.path.join(dst, 'data', 'sounds.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rep.append('звуков (wav): %d' % len(snd))
    # --- объекты и анимации
    objs = json.load(open(os.path.join(out, 'data', 'objects.json'), encoding='utf-8'))
    anims = {}; missing = set(); nanim = 0
    for h, o in objs.items():
        if o['type_name'] not in ('Active', 'Backdrop', 'QuickBackdrop'): continue
        e = dict(name=o['name'], type=o['type_name'], movement=o.get('movement'), anims={})
        if o['type_name'] == 'Backdrop':
            ph = bytes.fromhex(o['props_hex'])
            e['image'] = struct.unpack_from('<H', ph, 8)[0]
            if e['image'] not in imgs: missing.add(e['image'])
        elif o['type_name'] == 'QuickBackdrop':
            e['props_hex'] = o['props_hex']
        for ai, a in (o.get('animations') or {}).items():
            dd = {}
            for d, v in a['directions'].items():
                di = int(d)
                dd[d] = dict(label=DIRS.get(di, 'dir%d' % di), frames=v['frames'], speed_min=v['min_speed'],
                             speed_max=v['max_speed'], repeat=v['repeat'], back_to=v['back_to'])
                for f in v['frames']:
                    if f not in imgs: missing.add(f)
                nanim += 1
            e['anims'][ai] = dict(name=a['name'], dirs=dd)
        anims[h] = e
    json.dump(anims, open(os.path.join(dst, 'data', 'anims.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rep.append('объектов в anims.json: %d, направленных анимаций: %d' % (len(anims), nanim))
    rep.append('кадров анимаций без картинки: %d (если картинок ожидается ~4000, а есть мало - запускайте на ПОЛНОМ HCNSB.exe)' % len(missing))
    # --- флаги видимости объектов (байт 19 свойств: бит 0x08 = скрыт при старте)
    fl = {}
    od = os.path.join(out, 'objects')
    for fn in os.listdir(od) if os.path.isdir(od) else []:
        if fn.endswith('_4446.bin'):
            r = open(os.path.join(od, fn), 'rb').read()
            if len(r) > 19: fl[str(int(fn[:4]))] = dict(b19=r[19], visible=(r[19] & 8) == 0)
    json.dump(fl, open(os.path.join(dst, 'data', 'flags.json'), 'w'))
    # --- уровни
    fr = json.load(open(os.path.join(out, 'data', 'frames.json'), encoding='utf-8'))
    lv = []
    for f in fr:
        ins = []
        for i in f['instances']:
            a = anims.get(str(i['object']))
            d = dict(object=i['object'], type=i['type'], name=i['name'], x=i['x'], y=i['y'], parent=i['parent'])
            if a and a.get('image') is not None: d['image'] = a['image']
            ins.append(d)
        lv.append(dict(index=f['index'], name=f['name'], width=f['width'], height=f['height'],
                       background_bgr=f.get('background_bgr'), instances=ins))
    json.dump(lv, open(os.path.join(dst, 'data', 'levels.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rep.append('уровней: %d' % len(lv))
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, 'import_hc.gd'), os.path.join(here, 'godot', 'import_hc.gd')):
        if os.path.exists(cand):
            shutil.copyfile(cand, os.path.join(dst, 'import_hc.gd')); break
    else:
        rep.append('ВНИМАНИЕ: import_hc.gd не найден рядом со скриптом - скопируйте его в hc_godot вручную')
    open(os.path.join(dst, 'data', 'atlas_report.txt'), 'w', encoding='utf-8').write('\n'.join(rep))
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
