extends Node2D
# Уровень. Сцена уровня (levels/NNN_Имя.tscn, строится tools/make_scenes.py) содержит фоны, декор, маркеры и двери -
# их видно и можно двигать в редакторе. Этот скрипт при запуске добавляет Криса, врагов, предметы и HUD.

@export var level_index := 4

var data: Dictionary
var level_w := 3030.0
var level_h := 600.0
var floor_y := 573.0
var chris: Chris
var enemies: Array = []
var items: Array = []
var doors: Array = []          # [{x0, x1, to}]
var makers: Array = []         # x координаты точек появления
var layer_items: Node2D
var layer_enemies: Node2D
var hud_label: Label
var msg_label: Label
var msg_t := 0.0
var spawn_t: Dictionary = {}
var kills := 0
var test_mode := false
var test_t := 0.0


func _ready() -> void:
	randomize()
	data = HC.slice
	if data.is_empty() or HC.levels.size() <= level_index:
		HC.errors.append("нет данных уровня (slice.json / levels.json)")
	if not HC.errors.is_empty():
		_show_errors()
		return
	var lv: Dictionary = HC.levels[level_index]
	level_w = lv["width"]
	level_h = lv["height"]
	var bgr: Array = lv.get("background_bgr", [0, 0, 0])
	RenderingServer.set_default_clear_color(Color8(int(bgr[2]), int(bgr[1]), int(bgr[0])))
	var start := Vector2(data["chris"]["start"][0], data["chris"]["start"][1])
	if has_node("Background"):
		_read_scene()
		if has_node("Markers/ChrisStart"):
			start = get_node("Markers/ChrisStart").position
	else:
		_build_level(lv)        # старый вариант без сцены уровня
		floor_y = float(data["floor_y"])
		for d in data["doors"]:
			doors.append(d)
		for mx in data["makers"]:
			makers.append(float(mx))
	layer_items = Node2D.new()
	layer_items.z_index = 1
	add_child(layer_items)
	layer_enemies = Node2D.new()
	layer_enemies.z_index = 2
	add_child(layer_enemies)
	chris = Chris.new().setup(data["chris"], self)
	chris.z_index = 3
	chris.position = start
	add_child(chris)
	chris.died.connect(_on_chris_died)
	chris.door_pressed.connect(_on_door)
	var cam := Camera2D.new()
	cam.limit_left = 0
	cam.limit_right = int(level_w)
	cam.limit_top = 0
	cam.limit_bottom = int(level_h)
	cam.position = Vector2(0, -150)
	chris.add_child(cam)
	for e in data["enemies"]:
		spawn_t[e["name"]] = float(e["every_ms"]) / 1000.0 - randf_range(2.0, 6.0)   # первый враг появится быстро
	_build_hud()
	test_mode = OS.get_environment("HC_TEST") != ""


func _read_scene() -> void:
	# позиции берутся из сцены - их можно менять в редакторе
	if has_node("Markers/Floor"):
		floor_y = get_node("Markers/Floor").position.y
	for m in get_node("Markers/Makers").get_children():
		makers.append(m.position.x)
	for d in get_node("Doors").get_children():
		if d is Control:
			doors.append({"x0": d.position.x, "x1": d.position.x + d.size.x, "to": d.get_meta("to", "?")})
	get_node("Doors").visible = false
	for n in find_children("Preview", "", true, false):
		n.queue_free()
	# декор оживает: картинка из сцены заменяется анимированным спрайтом того же объекта
	for s in get_node("Decor").get_children():
		if s is Sprite2D and s.has_meta("hc_obj"):
			var a := HCSprite.new().setup(int(s.get_meta("hc_obj")))
			a.position = s.position
			a.play(0, 0)
			get_node("Decor").add_child(a)
			s.visible = false


func _show_errors() -> void:
	var cl := CanvasLayer.new()
	add_child(cl)
	var l := Label.new()
	l.position = Vector2(20, 20)
	l.size = Vector2(760, 560)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD
	l.add_theme_font_size_override("font_size", 18)
	l.text = "Срез не запустился:\n\n- " + "\n- ".join(HC.errors) + "\n\nПроверьте папку res://hc/: в ней должны быть data/ (с slice.json), sprites/, sounds/."
	cl.add_child(l)
	set_process(false)
	print(l.text)


func _build_level(lv: Dictionary) -> void:
	var z := -1000
	for ins in lv["instances"]:
		z += 1
		var t: String = ins["type"]
		if t == "Backdrop":
			var image: int = int(ins.get("image", -1))
			if image < 0:
				continue
			var s := HCSprite.new()
			s.frozen_image = image
			s.position = Vector2(ins["x"], ins["y"]) + _hot(image)   # у фона x,y - левый верхний угол
			s.z_index = z
			add_child(s)
		elif t == "Active" and float(ins["object"]) in data["decor"]:
			var s2 := HCSprite.new().setup(int(ins["object"]))
			s2.position = Vector2(ins["x"], ins["y"])
			s2.play(0, 0)
			add_child(s2)


func _hot(image: int) -> Vector2:
	var info := HC.img(image)
	if info.is_empty():
		return Vector2.ZERO
	return Vector2(info["hot"][0], info["hot"][1])


func _build_hud() -> void:
	var cl := CanvasLayer.new()
	add_child(cl)
	hud_label = Label.new()
	hud_label.position = Vector2(12, 8)
	hud_label.add_theme_font_size_override("font_size", 20)
	hud_label.add_theme_color_override("font_color", Color.WHITE)
	hud_label.add_theme_color_override("font_outline_color", Color.BLACK)
	hud_label.add_theme_constant_override("outline_size", 5)
	cl.add_child(hud_label)
	msg_label = Label.new()
	msg_label.position = Vector2(12, 560)
	msg_label.add_theme_font_size_override("font_size", 18)
	msg_label.add_theme_color_override("font_outline_color", Color.BLACK)
	msg_label.add_theme_constant_override("outline_size", 5)
	cl.add_child(msg_label)


func say(text: String) -> void:
	msg_label.text = text
	msg_t = 2.5


func in_door(x: float) -> bool:
	return _door_at(x) != ""


func _door_at(x: float) -> String:
	for d in doors:
		if x >= float(d["x0"]) and x <= float(d["x1"]):
			return str(d["to"])
	return ""


func _on_door() -> void:
	say("Дверь в «%s»: другие уровни в срезе ещё не подключены" % _door_at(chris.position.x))


func _on_chris_died() -> void:
	say("Крис погиб. Нажмите R, чтобы начать заново")


func on_enemy_died(e: Enemy) -> void:
	enemies.erase(e)
	kills += 1
	if randf() < float(data["drop_chance"]):
		var total := 0.0
		for l in data["loot"]:
			total += float(l["weight"])
		var r := randf() * total
		for l in data["loot"]:
			r -= float(l["weight"])
			if r <= 0.0:
				var it := Item.new().setup(l, int(data["item_obj"]))
				it.position = e.position
				layer_items.add_child(it)
				items.append(it)
				break


# ---- эффекты (объекты из игры: Blood Left/Right, Small Splat, part1..9)
func _fx(name: String) -> int:
	return int(data.get("fx", {}).get(name, -1))


func fx_once(name: String, at: Vector2) -> void:
	var h := _fx(name)
	if h < 0:
		return
	var f := Fx.new().setup(h, false)
	f.position = at
	f.gravity = 0.0
	f.life = 3.0
	f.z_index = 4
	add_child(f)


func blood_burst(at: Vector2, n: int) -> void:
	# капли летят веером вверх-в стороны и падают (в игре: Blood Left/Right, разворот вниз каждые 150 мс)
	for i in n:
		var left := i % 2 == 0
		var h := _fx("Blood Left" if left else "Blood Right")
		if h < 0:
			return
		var f := Fx.new().setup(h)
		var ang := deg_to_rad(randf_range(20.0, 70.0))
		var sp := randf_range(180.0, 320.0)
		f.vel = Vector2((-1.0 if left else 1.0) * cos(ang) * sp, -sin(ang) * sp)
		f.position = at + Vector2(0, randf_range(-10.0, 0.0))
		f.gravity = 1100.0
		f.floor_y = floor_y
		f.life = 1.5
		f.z_index = 4
		add_child(f)


func gibs(at: Vector2, n: int) -> void:
	var parts := range(1, 10)
	parts.shuffle()
	for i in min(n, 9):
		var h := _fx("part%d" % parts[i])
		if h < 0:
			return
		var f := Fx.new().setup(h)
		var ang := deg_to_rad(randf_range(200.0, 340.0))
		var sp := randf_range(250.0, 420.0)
		f.vel = Vector2(cos(ang) * sp, sin(ang) * sp)
		f.position = at
		f.gravity = 1000.0
		f.floor_y = floor_y
		f.on_floor = "bounce"
		f.life = 2.5
		f.fade = 0.8
		f.z_index = 4
		add_child(f)


func _spawn(c: Dictionary) -> void:
	var xs: Array = []
	for mx in makers:
		if absf(float(mx) - chris.position.x) > 450.0:
			xs.append(float(mx))
	if xs.is_empty():
		xs = makers.duplicate()
	if xs.is_empty():
		return
	var e := Enemy.new().setup(c, self)
	e.position = Vector2(xs[randi() % xs.size()], floor_y)
	layer_enemies.add_child(e)
	enemies.append(e)


func _process(delta: float) -> void:
	if chris == null:
		return
	if Input.is_action_just_pressed("restart"):
		get_tree().reload_current_scene()
		return
	msg_t = max(0.0, msg_t - delta)
	if msg_t <= 0.0:
		msg_label.text = ""
	# появление врагов: раз в N секунд, не больше одного каждого типа и восьми всего
	if not chris.dead:
		for c in data["enemies"]:
			spawn_t[c["name"]] += delta
			if spawn_t[c["name"]] >= float(c["every_ms"]) / 1000.0:
				spawn_t[c["name"]] = 0.0
				var same := 0
				for e in enemies:
					if e.cfg["name"] == c["name"]:
						same += 1
				if same < 1 and enemies.size() < int(data["max_enemies"]):
					_spawn(c)
	# подбор предметов
	for it in items.duplicate():
		if not is_instance_valid(it):
			items.erase(it)
			continue
		if not chris.dead and it.rect().intersects(chris.rect()):
			match it.kind:
				"cash": chris.money += it.value
				"hp": chris.heal(it.value)
				"trap": chris.hurt(it.value, "boxGet")
			HC.play(it.snd)
			items.erase(it)
			it.queue_free()
	hud_label.text = "HP %d/%d    $%d    %s    убито %d" % [chris.hp, chris.max_hp, chris.money, chris.weapon["name"], kills]
	if test_mode:
		_test(delta)


func _test(delta: float) -> void:
	# автопилот для проверки без экрана: идёт к ближайшему врагу, бьёт, печатает состояние
	test_t += delta
	if OS.get_environment("HC_TEST") == "passive":      # стоять на месте: нейтральные прохожие не должны нападать
		if int(test_t * 10.0) % 50 == 0 and int(test_t * 10.0) != int((test_t - delta) * 10.0):
			var host := 0
			for e in enemies:
				if e.hostile():
					host += 1
			print("passive t=%.1f hp=%d enemies=%d hostile=%d" % [test_t, chris.hp, enemies.size(), host])
		if test_t > 40.0:
			get_tree().quit()
		return
	Input.action_release("right")
	Input.action_release("left")
	if OS.get_environment("HC_TEST") == "provoke":      # разозлить одного прохожего и стоять: он должен напасть
		var angry := false
		for e in enemies:
			if e.hostile():
				angry = true
		if angry and test_t > 1.0:
			if int(test_t * 10.0) % 10 == 0 and int(test_t * 10.0) != int((test_t - delta) * 10.0):
				print("provoke t=%.1f hp=%d hostile=yes" % [test_t, chris.hp])
			if test_t > 40.0:
				get_tree().quit()
			return
	var target: Enemy = null
	for e in enemies:
		if target == null or absf(e.position.x - chris.position.x) < absf(target.position.x - chris.position.x):
			target = e
	if target != null:
		var d := target.position.x - chris.position.x
		if absf(d) > 60.0:
			Input.action_press("right" if d > 0.0 else "left")
		else:
			Input.action_press("slot_z")
			Input.action_release("slot_z")
	else:
		Input.action_press("right")
	if int(test_t * 10.0) % 20 == 0 and int(test_t * 10.0) != int((test_t - delta) * 10.0):
		print("t=%.1f chris=(%.0f,%.0f) hp=%d $%d enemies=%d kills=%d" % [test_t, chris.position.x, chris.position.y, chris.hp, chris.money, enemies.size(), kills])
	if test_t > 30.0:
		get_tree().quit()
