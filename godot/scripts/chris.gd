class_name Chris
extends Node2D
# Крис: платформенное движение, прыжок, удар ножом (Z), здоровье. Числа движения - из игры (скорость 28, гравитация 30, прыжок 100).

signal died
signal door_pressed

var cfg: Dictionary
var level: Node
var body: HCSprite
var melee: HCSprite
var vel := Vector2.ZERO
var facing := 0
var on_ground := false
var hp := 80
var max_hp := 80
var money := 0
var attacking := false
var hurt_t := 0.0
var hit_ids := {}
var dead := false
var weapon := {"name": "Knife", "anim": 19, "damage": 6, "body_anim": 14, "hit_frame": 4}


func setup(c: Dictionary, lvl: Node) -> Chris:
	cfg = c
	level = lvl
	hp = c["hp"]
	max_hp = c["hp"]
	body = HCSprite.new().setup(c["obj"])
	add_child(body)
	melee = HCSprite.new().setup(c["melee_obj"])
	melee.visible = false
	add_child(melee)
	melee.finished.connect(_on_melee_done)
	var k: Dictionary = HC.slice.get("knife", {})
	for key in k:
		weapon[key] = k[key]
	body.play(0, 0)
	return self


func _on_melee_done() -> void:
	attacking = false
	melee.visible = false
	hit_ids.clear()


func rect() -> Rect2:
	return Rect2(position + Vector2(-18, -120), Vector2(36, 120))


func hurt(dmg: int, sound := "chrisGrunt") -> void:
	if dead:
		return
	hp = max(0, hp - dmg)
	hurt_t = 0.35
	HC.play(sound)
	if hp <= 0:
		dead = true
		HC.play("chrisDies")
		died.emit()


func heal(v: int) -> void:
	hp = min(max_hp, hp + v)


func start_attack() -> void:
	if attacking or dead or hurt_t > 0.0:
		return
	attacking = true
	hit_ids.clear()
	melee.visible = true
	melee.play(weapon["anim"], facing, false, true)
	body.play(weapon["body_anim"], facing, false, true)
	HC.play("whoosh11kh")


func _physics_process(delta: float) -> void:
	if dead:
		body.play(0, facing)
		return
	var sp: float = float(cfg["speed"]) * HC.PX_PER_SPEED
	var dx := Input.get_axis("left", "right")
	if attacking or hurt_t > 0.0:
		dx = 0.0
	hurt_t = max(0.0, hurt_t - delta)
	vel.x = dx * sp
	if dx > 0.0:
		facing = 0
	elif dx < 0.0:
		facing = 16
	if Input.is_action_just_pressed("up"):
		if on_ground and level.in_door(position.x):
			door_pressed.emit()
		elif on_ground and not attacking and hurt_t <= 0.0:
			vel.y = -float(cfg["jump"]) * HC.JUMP_PER_UNIT
			on_ground = false
			HC.play("chrisJump")
	if Input.is_action_just_pressed("slot_z"):
		start_attack()
	vel.y += float(cfg["gravity"]) * HC.GRAVITY_PER_UNIT * delta
	position += vel * delta
	var fy: float = level.floor_y
	if position.y >= fy:
		position.y = fy
		vel.y = 0.0
		on_ground = true
	else:
		on_ground = false
	position.x = clamp(position.x, 30.0, level.level_w - 30.0)
	# анимация
	if attacking:
		body.play(weapon["body_anim"], facing, false)
		melee.play(weapon["anim"], facing, false)
		_hit_enemies()
	elif hurt_t > 0.0:
		body.play(13, facing)
	elif not on_ground:
		body.play(7 if vel.y < 0.0 else 8, facing)
	elif dx != 0.0:
		body.play(1, facing)
	else:
		body.play(0, facing)


func _hit_enemies() -> void:
	if melee.frame_index() < int(weapon.get("hit_frame", 4)):    # в игре удар засчитывается на 4-м кадре анимации
		return
	var r := melee.image_rect()
	for e in level.enemies:
		if e.dead or hit_ids.has(e.get_instance_id()):
			continue
		if r.intersects(e.rect()):
			hit_ids[e.get_instance_id()] = true
			e.take_hit(weapon["damage"], facing)
