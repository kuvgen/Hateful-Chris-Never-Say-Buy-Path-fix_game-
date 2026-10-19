class_name Enemy
extends Node2D
# Враг/прохожий по логике оригинала:
#  - по умолчанию НЕЙТРАЛЕН: бродит (состояния 0..3, новое раз в 10 с) и Криса не трогает;
#  - каждый удар добавляет «злость» (+2), она спадает на 1 раз в 2 с;
#  - злость >= 5: бежит к Крису (если он рядом) и атакует при касании, за каждую атаку злость -1;
#  - HP <= 2: оглушён (анимация 12, стоит); HP <= 0: смерть - куски тела, кровь, предмет.
#  Goth не злится никогда; Bum и Goth в Downtown урона не наносят.

var cfg: Dictionary
var level: Node
var spr: HCSprite
var hp := 20
var state := 0
var state_t := 0.0
var facing := 0
var anger := 0.0
var anger_t := 0.0
var atk_cd := 0.0
var atk_t := 0.0
var pain_t := 0.0
var bar_t := 0.0
var dead := false
var A: Dictionary


func setup(c: Dictionary, lvl: Node) -> Enemy:
	cfg = c
	level = lvl
	A = HC.slice.get("anger", {})
	hp = c["hp"]
	spr = HCSprite.new().setup(c["obj"])
	add_child(spr)
	state = randi() % 4
	state_t = 10.0
	return self


func rect() -> Rect2:
	return Rect2(position + Vector2(-25, -115), Vector2(50, 115))


func hostile() -> bool:
	return anger >= float(A.get("hostile_at", 5)) and hp > int(A.get("stun_hp", 2))


func take_hit(dmg: int, _from_dir: int) -> void:
	if dead:
		return
	hp -= dmg
	if cfg.get("angers", true):
		anger += float(A.get("per_hit", 2))
	pain_t = 0.35
	bar_t = 0.4
	HC.play("goodSplatHit")
	level.blood_burst(position + Vector2(0, -100), 6)
	level.fx_once("Small Splat", position + Vector2(0, -100))
	if hp <= 0:
		die()


func die() -> void:
	if dead:
		return
	dead = true
	HC.play("splatterSlow1")
	level.gibs(position + Vector2(0, -100), 3)
	level.blood_burst(position + Vector2(0, -100), 4)
	level.on_enemy_died(self)
	queue_free()


func _process(delta: float) -> void:
	if dead:
		return
	bar_t = max(0.0, bar_t - delta)
	pain_t = max(0.0, pain_t - delta)
	atk_cd = max(0.0, atk_cd - delta)
	atk_t = max(0.0, atk_t - delta)
	anger_t += delta
	if anger_t >= float(A.get("decay_every_s", 2.0)):
		anger_t = 0.0
		anger = max(0.0, anger - 1.0)
	state_t -= delta
	if state_t <= 0.0:
		state_t = 10.0
		state = randi() % 5
	var ch: Chris = level.chris
	var dx: float = ch.position.x - position.x
	var speed := float(cfg.get("walk", 10))
	var move := 0.0
	var stunned := hp <= int(A.get("stun_hp", 2))
	if stunned:
		anger = 0.0
	else:
		match state:
			0, 2: move = 1.0
			1: move = -1.0
			_: move = 0.0
		if hostile() and not ch.dead and absf(dx) < float(A.get("chase_range", 260)):
			move = signf(dx)
			speed = float(cfg.get("run", 12))
	if pain_t > 0.0 or atk_t > 0.0:
		move = 0.0
	position.x += move * speed * HC.PX_PER_SPEED * delta
	if position.x < 40.0:
		position.x = 40.0
		state = 0
	elif position.x > level.level_w - 40.0:
		position.x = level.level_w - 40.0
		state = 1
	if move != 0.0:
		facing = 0 if move > 0.0 else 16
	elif hostile() and absf(dx) < 300.0 and atk_t <= 0.0:
		facing = 0 if dx > 0.0 else 16
	# атака только в злом состоянии и при касании
	if hostile() and not ch.dead and atk_cd <= 0.0 and pain_t <= 0.0 and rect().intersects(ch.rect()):
		atk_cd = float(A.get("attack_cooldown_s", 1.0))
		atk_t = 0.4
		anger = max(0.0, anger - 1.0)
		HC.play(str(cfg.get("sound", "")))
		if int(cfg["damage"]) > 0 and not ch.attacking:    # пока Крис бьёт (анимация 14/15), урон не проходит
			ch.hurt(int(cfg["damage"]), "chrisGrunt")
	# анимация
	var pa := int(cfg.get("pain_anim", 15))
	var aa := int(cfg.get("attack_anim", 13))
	if pain_t > 0.0 and spr.has_anim(pa):
		spr.play(pa, facing)
	elif atk_t > 0.0 and aa > 0 and spr.has_anim(aa):
		spr.play(aa, facing)
	elif stunned and spr.has_anim(12):
		spr.play(12, facing)
	elif move != 0.0 and spr.has_anim(1):
		spr.play(1, facing)
	elif move != 0.0 and spr.has_anim(2):
		spr.play(2, facing)
	else:
		spr.play(0, facing)
	queue_redraw()


func _draw() -> void:
	if bar_t > 0.0 or hp < int(cfg["hp"]):
		var w := 50.0
		var f := clampf(float(hp) / float(cfg["hp"]), 0.0, 1.0)
		draw_rect(Rect2(-25, -135, w, 6), Color(0, 0, 0, 0.7))
		draw_rect(Rect2(-25, -135, w * f, 6), Color(0.85, 0.15, 0.1))
	if hostile():                          # злой - красный маркер над головой (временная подсказка)
		draw_circle(Vector2(0, -145), 4.0, Color(1, 0.2, 0.1))
