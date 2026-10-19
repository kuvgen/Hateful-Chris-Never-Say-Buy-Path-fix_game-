extends Node
# Автозагрузка HC: данные игры (из экспорта hc_godot), текстуры, звуки, управление.

const FPS_PER_SPEED := 0.5      # скорость анимации Clickteam -> кадров в секунду (подберите)
const PX_PER_SPEED := 8.0       # скорость движения Clickteam -> пикселей в секунду (подберите)
const GRAVITY_PER_UNIT := 60.0  # гравитация Clickteam (30) -> пикселей/с^2
const JUMP_PER_UNIT := 7.35     # сила прыжка Clickteam (100) -> начальная скорость, пикселей/с

var anims: Dictionary = {}
var images: Dictionary = {}
var levels: Array = []
var sounds: Dictionary = {}
var slice: Dictionary = {}
var sound_by_name: Dictionary = {}
var _tex: Dictionary = {}
var _snd: Dictionary = {}
var _players: Array = []
var errors: Array = []          # что не найдено при запуске - показывается прямо в окне игры


func _ready() -> void:
	anims = _json("res://hc/data/anims.json")
	images = _json("res://hc/data/images.json")
	levels = _json("res://hc/data/levels.json")
	sounds = _json("res://hc/data/sounds.json")
	slice = _json("res://hc/data/slice.json")
	if not FileAccess.file_exists("res://hc/sprites/01402.png") and not ResourceLoader.exists("res://hc/sprites/01402.png"):
		errors.append("нет картинок в res://hc/sprites/ (например 01402.png - Крис)")
	if typeof(levels) != TYPE_ARRAY:
		errors.append("levels.json должен быть списком уровней")
		levels = []
	for k in sounds:
		sound_by_name[sounds[k]["name"]] = sounds[k]["file"]
	_setup_input()
	for i in 8:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)


func _json(path: String) -> Variant:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		errors.append("нет файла " + path)
		return {}
	var v: Variant = JSON.parse_string(f.get_as_text())
	if v == null:
		errors.append("файл повреждён (не JSON) " + path)
		return {}
	return v


func _setup_input() -> void:
	var map := {"left": KEY_LEFT, "right": KEY_RIGHT, "up": KEY_UP, "down": KEY_DOWN, "slot_z": KEY_Z, "slot_x": KEY_X,
		"slot_c": KEY_C, "restart": KEY_R}
	for a in map:
		if not InputMap.has_action(a):
			InputMap.add_action(a)
		var ev := InputEventKey.new()
		ev.physical_keycode = map[a]
		InputMap.action_add_event(a, ev)


func tex(handle: int) -> Texture2D:
	if _tex.has(handle):
		return _tex[handle]
	var t: Texture2D = null
	var path := "res://hc/sprites/%05d.png" % handle
	if ResourceLoader.exists(path):          # картинка импортирована редактором - обычная загрузка
		t = load(path)
	elif FileAccess.file_exists(path):
		var image := Image.load_from_file(path)
		if image != null:
			t = ImageTexture.create_from_image(image)
	_tex[handle] = t
	return t


func img(handle: int) -> Dictionary:
	return images.get(str(handle), {})


func play(sound_name: String) -> void:
	if sound_name == "" or not sound_by_name.has(sound_name):
		return
	var s: AudioStream = _snd.get(sound_name)
	if s == null:
		s = _load_wav("res://hc/sounds/" + sound_by_name[sound_name])
		_snd[sound_name] = s
	if s == null:
		return
	for p in _players:
		if not p.playing:
			p.stream = s
			p.play()
			return


func _load_wav(path: String) -> AudioStream:
	if ResourceLoader.exists(path):
		return load(path)
	if not FileAccess.file_exists(path):
		return null
	var b := FileAccess.get_file_as_bytes(path)
	if b.size() < 44 or b.slice(0, 4).get_string_from_ascii() != "RIFF":
		return null
	var pos := 12
	var fmt := {}
	while pos + 8 <= b.size():
		var id := b.slice(pos, pos + 4).get_string_from_ascii()
		var sz := b.decode_u32(pos + 4)
		if id == "fmt ":
			fmt = {"tag": b.decode_u16(pos + 8), "ch": b.decode_u16(pos + 10), "rate": b.decode_u32(pos + 12), "bits": b.decode_u16(pos + 22)}
		elif id == "data":
			if fmt.get("tag", 0) != 1:
				return null
			var w := AudioStreamWAV.new()
			w.mix_rate = fmt["rate"]
			w.stereo = fmt["ch"] == 2
			w.format = AudioStreamWAV.FORMAT_16_BITS if fmt["bits"] == 16 else AudioStreamWAV.FORMAT_8_BITS
			w.data = b.slice(pos + 8, pos + 8 + sz)
			return w
		pos += 8 + sz + (sz & 1)
	return null
