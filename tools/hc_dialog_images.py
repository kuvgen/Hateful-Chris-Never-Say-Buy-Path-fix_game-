#!/usr/bin/env python3
"""hc_dialog_images.py - собирает картинки диалогов в одну папку с понятными именами.
Запуск (из папки со скриптами):
  cd "path\\to\\repo\\tools"
  python hc_dialog_images.py work\\hc_godot\\sprites dialogs
Результат: папка dialogs с 34 картинками (01_Intro_1.png ... 99_good_end.png) в порядке сюжета."""
import os, shutil, sys
D = [('01_Intro_1', 367), ('02_Intro_2', 1890), ('03_Intro_3', 1891), ('10_sailor_1', 3831), ('11_sailor_2', 3832),
     ('12_sailor_3', 3833), ('20_uber_1', 3847), ('21_uber_2', 3848), ('22_uber_3', 3862), ('30_Spa', 3868),
     ('31_spa_1', 3836), ('32_spa_2', 2909), ('40_hockey_1', 2604), ('41_hockey_2', 3525), ('50_mall1', 3825),
     ('51_mall2', 3827), ('60_nstep_1', 3830), ('61_nstep_2', 3828), ('70_pier_1', 3838), ('71_pier_2', 3840),
     ('80_trix_1', 3864), ('81_trix_2', 3863), ('82_sensei_1', 3834), ('83_sensei_2', 3835), ('90_trix_abduct', 3841),
     ('91_cuzin_les', 3357), ('92_cuz_les_gerbil_upgrade', 2416), ('93_Before_last_last', 3095),
     ('94_before_last_battle', 3405), ('95_end_1', 3387), ('96_end_2', 3414), ('97_bad_end', 3438),
     ('98_okay_end', 2992), ('99_good_end', 3439)]
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for name, h in D:
    shutil.copyfile(os.path.join(src, '%05d.png' % h), os.path.join(dst, name + '.png'))
print('Скопировано %d картинок в %s' % (len(D), dst))
