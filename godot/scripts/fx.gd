class_name Fx
extends Node2D
# Эффект: кровь, брызги, куски тела. Летит, падает под гравитацией, исчезает на полу или по времени.

var spr: HCSprite
var vel := Vector2.ZERO
var gravity := 900.0
var life := 2.0
var floor_y := 1e9
var on_floor := "die"       # что делать на полу: "die" - исчезнуть, "stop" - лечь и доиграть, "bounce" - отскочить
var loop := true
var fade := 0.4


func setup(obj: int, anim_loop := true) -> Fx:
	spr = HCSprite.new().setup(obj)
	add_child(spr)
	loop = anim_loop
	spr.play(0, 0, anim_loop, true)
	if not anim_loop:
		spr.finished.connect(queue_free)
	return self


func _process(delta: float) -> void:
	life -= delta
	if life <= 0.0:
		queue_free()
		return
	if life < fade:
		modulate.a = life / fade
	if vel == Vector2.ZERO and gravity == 0.0:
		return
	vel.y += gravity * delta
	position += vel * delta
	if position.y >= floor_y:
		position.y = floor_y
		match on_floor:
			"die":
				queue_free()
			"stop":
				vel = Vector2.ZERO
				gravity = 0.0
			"bounce":
				vel.y = -vel.y * 0.35
				vel.x *= 0.6
				if absf(vel.y) < 40.0:
					vel = Vector2.ZERO
					gravity = 0.0
