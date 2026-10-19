class_name HCSprite
extends Node2D
# Спрайт объекта Clickteam: анимации по направлениям, точка привязки (hot spot) каждого кадра.

signal finished

var obj := 0
var anim := 0
var dir := 0
var frame_f := 0.0
var loop := true
var done := false
var paused := false
var frozen_image := -1        # если >=0, рисуется именно эта картинка (для предметов)
var _entry: Dictionary = {}


func setup(h: int) -> HCSprite:
	obj = h
	_entry = HC.anims.get(str(h), {})
	return self


func has_anim(a: int) -> bool:
	return _entry.get("anims", {}).has(str(a))


func play(a: int, d: int, looped := true, restart := false) -> void:
	if not restart and a == anim and d == dir and not done:
		return
	anim = a
	dir = d
	loop = looped
	done = false
	frame_f = 0.0
	queue_redraw()


func _dir_entry() -> Dictionary:
	var an: Dictionary = _entry.get("anims", {})
	var a: Dictionary = an.get(str(anim), an.get("0", {}))
	var dirs: Dictionary = a.get("dirs", {})
	if dirs.is_empty():
		return {}
	if dirs.has(str(dir)):
		return dirs[str(dir)]
	if dir >= 8 and dir < 24 and dirs.has("16"):
		return dirs["16"]
	if dirs.has("0"):
		return dirs["0"]
	return dirs[dirs.keys()[0]]


func frames() -> Array:
	return _dir_entry().get("frames", [])


func frame_index() -> int:
	return int(frame_f)


func current_image() -> int:
	if frozen_image >= 0:
		return frozen_image
	var f := frames()
	if f.is_empty():
		return -1
	return int(f[min(frame_index(), f.size() - 1)])


func _process(delta: float) -> void:
	if paused or frozen_image >= 0:
		return
	var d := _dir_entry()
	var f: Array = d.get("frames", [])
	if f.size() <= 1:
		if not loop and not done:
			done = true
			finished.emit()
		return
	frame_f += max(1.0, float(d.get("speed_max", 10)) * HC.FPS_PER_SPEED) * delta
	if frame_f >= f.size():
		if loop:
			frame_f = fmod(frame_f, float(f.size()))
		else:
			frame_f = float(f.size()) - 0.001
			if not done:
				done = true
				finished.emit()
	queue_redraw()


func _draw() -> void:
	var h := current_image()
	if h < 0:
		return
	var t := HC.tex(h)
	var info := HC.img(h)
	if t == null or info.is_empty():
		return
	draw_texture(t, -Vector2(info["hot"][0], info["hot"][1]))


func image_rect() -> Rect2:
	# прямоугольник текущей картинки в мировых координатах
	var h := current_image()
	var info := HC.img(h)
	if info.is_empty():
		return Rect2(global_position, Vector2.ZERO)
	return Rect2(global_position - Vector2(info["hot"][0], info["hot"][1]), Vector2(info["w"], info["h"]))
