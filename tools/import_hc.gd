# import_hc.gd - EditorScript для Godot 4.
# Папку hc_godot целиком копируют в проект как res://hc/. Затем: откройте этот скрипт в редакторе Godot,
# меню File -> Run (Ctrl+Shift+X). Для каждого объекта-анимации создаётся res://hc/frames/<имя>_<handle>.tres (SpriteFrames).
# Имена анимаций: "<номер анимации>_<направление>", например "1_right" (ходьба вправо). Скорость берётся из игры:
# fps = speed * FPS_PER_SPEED (подберите коэффициент под ощущения).
@tool
extends EditorScript

const FPS_PER_SPEED := 0.5

func _run() -> void:
	var anims: Dictionary = _read_json("res://hc/data/anims.json")
	DirAccess.make_dir_recursive_absolute("res://hc/frames")
	var made := 0
	for h in anims:
		var o: Dictionary = anims[h]
		if o["type"] != "Active" or o["anims"].is_empty():
			continue
		var sf := SpriteFrames.new()
		sf.remove_animation("default")
		for ai in o["anims"]:
			var a: Dictionary = o["anims"][ai]
			for d in a["dirs"]:
				var v: Dictionary = a["dirs"][d]
				var nm := "%s_%s" % [ai, v["label"]]
				sf.add_animation(nm)
				sf.set_animation_speed(nm, max(1.0, float(v["speed_max"]) * FPS_PER_SPEED))
				sf.set_animation_loop(nm, int(v["repeat"]) == 0)
				for img in v["frames"]:
					var p := "res://hc/sprites/%d.png" % int(img)
					if ResourceLoader.exists(p):
						sf.add_frame(nm, load(p))
		var safe: String = String(o["name"]).validate_filename().replace(" ", "_")
		ResourceSaver.save(sf, "res://hc/frames/%s_%s.tres" % [safe, h])
		made += 1
	print("SpriteFrames создано: ", made)

func _read_json(path: String) -> Variant:
	var f := FileAccess.open(path, FileAccess.READ)
	return JSON.parse_string(f.get_as_text())
