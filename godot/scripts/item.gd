class_name Item
extends Node2D
# Выпавший предмет: живёт 6 секунд, подбирается касанием.

var kind := "cash"
var value := 0
var snd := ""
var spr: HCSprite
var life := 6.0


func setup(entry: Dictionary, obj: int) -> Item:
	kind = entry["kind"]
	value = int(entry["value"])
	snd = entry["sound"]
	spr = HCSprite.new().setup(obj)
	add_child(spr)
	spr.play(0, int(entry["dir"]))
	return self


func rect() -> Rect2:
	return Rect2(position + Vector2(-25, -60), Vector2(50, 60))


func _process(delta: float) -> void:
	life -= delta
	visible = life > 2.0 or int(life * 8.0) % 2 == 0
	if life <= 0.0:
		queue_free()
