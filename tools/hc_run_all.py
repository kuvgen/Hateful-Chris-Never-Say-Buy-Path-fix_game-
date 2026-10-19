#!/usr/bin/env python3
"""hc_run_all.py - запускает всю цепочку извлечения одной командой и собирает ресурсы для Godot.

Запуск:   python hc_run_all.py "D:\\Games\\Hateful Chris\\HCNSB.exe" work
Результат: папка work/ (сырые данные и логика) и work/hc_godot/ (готовые ресурсы для Godot).
Все .py файлы проекта должны лежать рядом с этим скриптом.
"""
import os, subprocess, sys

here = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) < 3: print(__doc__); sys.exit(1)
exe, out = sys.argv[1], sys.argv[2]
steps = [['hc_extract.py', exe, out], ['hc_events.py', out], ['hc_objects.py', out], ['hc_map.py', out],
         ['hc_schema.py', out], ['hc_godot_export.py', out, os.path.join(out, 'hc_godot')]]
for s in steps:
    print('\n=== %s ===' % s[0]); sys.stdout.flush()
    r = subprocess.run([sys.executable, os.path.join(here, s[0])] + s[1:])
    if r.returncode: print('Шаг %s завершился с ошибкой (код %d). Смотрите вывод выше.' % (s[0], r.returncode)); sys.exit(r.returncode)
print('\nГотово. Папка для Godot: %s' % os.path.join(out, 'hc_godot'))
