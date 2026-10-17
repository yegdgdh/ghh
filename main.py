
import pygame
import math
import random
import array


# Инициализация систем
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=1)

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600  # Стандартный размер под экраны смартфонов
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Cyber Shooter Mobile")
clock = pygame.time.Clock()
FPS = 60

# Цветовая палитра
BG_COLOR = (20, 20, 25)
WALL_COLOR = (70, 70, 80)
BULLET_COLOR = (0, 255, 255)
PLAYER_COLOR = (0, 255, 150)
STAMINA_COLOR = (255, 200, 0)
AMMO_COLOR = (200, 200, 200)
BTN_COLOR = (50, 50, 60)
BTN_TEXT_COLOR = (240, 240, 240)

ENEMY_REGULAR_COLOR = (255, 50, 50)
ENEMY_FAST_COLOR = (255, 120, 0)
ENEMY_TANK_COLOR = (180, 0, 255)
ENEMY_BOSS_COLOR = (255, 0, 50)
MEDKIT_COLOR = (255, 0, 100)


# --- ПРОГРАММНЫЙ СИНТЕЗАТОР ЗВУКОВ ---
def generate_sound(sound_type):
    sample_rate = 22050
    duration = 0.12 if sound_type == "pistol" else (0.25 if sound_type == "shotgun" else 0.15)
    if sound_type in ["explosion", "click"]: duration = 0.3 if sound_type == "explosion" else 0.05

    num_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * num_samples)

    for i in range(num_samples):
        t = i / sample_rate
        if sound_type == "pistol":
            val = math.sin(2 * math.pi * 700 * math.exp(-30 * t)) * 0.4
        elif sound_type == "shotgun":
            val = (math.sin(2 * math.pi * 250 * math.exp(-12 * t)) + random.uniform(-0.9, 0.9)) * 0.5
        elif sound_type == "explosion":
            val = random.uniform(-0.8, 0.8) * math.exp(-8 * t)
        elif sound_type == "heal":
            val = math.sin(2 * math.pi * (300 + 800 * t) * t) * 0.3
        elif sound_type == "click":
            val = random.uniform(-0.2, 0.2) if i < 200 else 0
        buf[i] = int(max(-32768, min(32767, val * 32767)))
    return pygame.mixer.Sound(buffer=buf)


snd_pistol = generate_sound("pistol")
snd_shotgun = generate_sound("shotgun")
snd_explosion = generate_sound("explosion")
snd_heal = generate_sound("heal")
snd_click = generate_sound("click")


# --- ИГРОВЫЕ КЛАССЫ ---
class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(WALL_COLOR)
        pygame.draw.rect(self.image, (50, 50, 60), (0, 0, width, height), 2)
        self.rect = self.image.get_rect(topleft=(x, y))


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, walls_group):
        super().__init__()
        self.radius = 20
        self.base_image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.base_image, PLAYER_COLOR, (self.radius, self.radius), self.radius)
        pygame.draw.ellipse(self.base_image, (0, 255, 255), (self.radius + 2, self.radius - 6, 12, 12))

        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(x, y))
        self.walls = walls_group

        # Характеристики (можно качать в магазине)
        self.speed = 3.8
        self.max_hp = 5
        self.hp = self.max_hp
        self.max_ammo = 12

        # Внутреннее состояние
        self.ammo = self.max_ammo
        self.is_reloading = False
        self.reload_timer = 0
        self.reload_duration = 1200
        self.invulnerable_dur, self.last_hit_time = 1000, 0
        self.shotgun_cooldown, self.last_shotgun_time = 900, 0
        self.angle = 0

    def take_damage(self):
        now = pygame.time.get_ticks()
        if now - self.last_hit_time > self.invulnerable_dur:
            self.hp -= 1
            self.last_hit_time = now
            return True
        return False

    def is_invulnerable(self):
        return pygame.time.get_ticks() - self.last_hit_time < self.invulnerable_dur

    def move(self, dx, dy, target_angle):
        self.angle = target_angle
        self.image = pygame.transform.rotate(self.base_image, -math.degrees(self.angle))
        old_center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = old_center

        self.rect.x += dx
        for wall in pygame.sprite.spritecollide(self, self.walls, False):
            if dx > 0: self.rect.right = wall.rect.left
            if dx < 0: self.rect.left = wall.rect.right

        self.rect.y += dy
        for wall in pygame.sprite.spritecollide(self, self.walls, False):
            if dy > 0: self.rect.bottom = wall.rect.top
            if dy < 0: self.rect.top = wall.rect.bottom
        self.rect.clamp_ip(screen.get_rect())


class Enemy(pygame.sprite.Sprite):
    def __init__(self, player_obj, walls_group, wave, is_boss=False):
        super().__init__()
        self.player = player_obj
        self.walls = walls_group
        self.is_boss = is_boss

        if self.is_boss:
            self.radius, self.speed, self.hp, self.color = 45, 1.2, 25 + (wave * 5), ENEMY_BOSS_COLOR
            self.max_hp = self.hp
        else:
            types = ['regular']
            if wave >= 2: types.append('fast')
            if wave >= 3: types.append('tank')
            self.type = random.choice(types)
            if self.type == 'regular':
                self.radius, self.speed, self.hp, self.color = 16, 2.0, 1, ENEMY_REGULAR_COLOR
            elif self.type == 'fast':
                self.radius, self.speed, self.hp, self.color = 13, 3.5, 1, ENEMY_FAST_COLOR
            elif self.type == 'tank':
                self.radius, self.speed, self.hp, self.color = 24, 1.0, 3, ENEMY_TANK_COLOR

        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)
        pygame.draw.circle(self.image, (30, 0, 0), (self.radius, self.radius), self.radius, 3)

        if self.is_boss:
            x, y = SCREEN_WIDTH // 2, -self.radius * 2
        else:
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top':
                x, y = random.randint(0, SCREEN_WIDTH), -self.radius * 2
            elif side == 'bottom':
                x, y = random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + self.radius * 2
            elif side == 'left':
                x, y = -self.radius * 2, random.randint(0, SCREEN_HEIGHT)
            else:
                x, y = SCREEN_WIDTH + self.radius * 2, random.randint(0, SCREEN_HEIGHT)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        px, py = self.player.rect.center
        ex, ey = self.rect.center
        rel_x, rel_y = px - ex, py - ey
        dist = math.hypot(rel_x, rel_y)
        if dist != 0:
            dx, dy = (rel_x / dist) * self.speed, (rel_y / dist) * self.speed
            self.rect.x += dx
            if pygame.sprite.spritecollideany(self, self.walls) and not self.is_boss: self.rect.x -= dx
            self.rect.y += dy
            if pygame.sprite.spritecollideany(self, self.walls) and not self.is_boss: self.rect.y -= dy


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle):
        super().__init__()
        self.image = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(self.image, BULLET_COLOR, (5, 5), 5)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 14
        self.dx, self.dy = math.cos(angle) * self.speed, math.sin(angle) * self.speed

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        if not screen.get_rect().contains(self.rect): self.kill()


class Medkit(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.rect(self.image, MEDKIT_COLOR, (0, 0, 20, 20), border_radius=4)
        pygame.draw.rect(self.image, (255, 255, 255), (9, 3, 2, 14))
        pygame.draw.rect(self.image, (255, 255, 255), (3, 9, 14, 2))
        self.rect = self.image.get_rect(center=(x, y))


class TouchButton:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text

    def draw(self, surface, font_obj, active=True):
        color = BTN_COLOR if active else (35, 35, 40)
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, (100, 100, 120) if active else (60, 60, 70), self.rect, 2, border_radius=10)
        txt = font_obj.render(self.text, True, BTN_TEXT_COLOR if active else (100, 100, 100))
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def is_pressed(self, pos_list):
        return any(self.rect.collidepoint(pos) for pos in pos_list)


# --- СБОРКА МИРА ---
all_sprites = pygame.sprite.Group()
walls = pygame.sprite.Group()
enemies = pygame.sprite.Group()
bullets_group = pygame.sprite.Group()
medkits = pygame.sprite.Group()

map_walls = [Wall(180, 130, 40, 200), Wall(580, 130, 40, 200), Wall(300, 380, 200, 40)]
for w in map_walls: walls.add(w); all_sprites.add(w)

player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3, walls)
all_sprites.add(player)

font = pygame.font.SysFont("Arial", 20, bold=True)
btn_font = pygame.font.SysFont("Arial", 22, bold=True)

# Кнопки тач-скрина
btn_up, btn_down = TouchButton(70, 410, 50, 50, "^"), TouchButton(70, 510, 50, 50, "v")
btn_left, btn_right = TouchButton(10, 460, 50, 50, "<"), TouchButton(130, 460, 50, 50, ">")
btn_pistol = TouchButton(510, 490, 85, 55, "ПИСТ"), TouchButton(605, 490, 85, 55, "ДРОБ")
btn_shotgun = btn_pistol[1];
btn_pistol = btn_pistol[0]
btn_reload_mob = TouchButton(700, 490, 90, 55, "ПЕРЕЗ")

# Кнопки магазина
btn_shop_speed = TouchButton(150, 200, 500, 60, "1. Скорость бега (+10%)  [Цена: 3]")
btn_shop_hp = TouchButton(150, 280, 500, 60, "2. Макс. здоровье (+1 HP) [Цена: 5]")
btn_shop_ammo = TouchButton(150, 360, 500, 60, "3. Объем магазина (+2 пат) [Цена: 4]")
btn_shop_next = TouchButton(250, 460, 300, 60, "НАЧАТЬ СЛЕДУЮЩУЮ ВОЛНУ")

score, wave, enemies_spawned, enemies_to_spawn = 0, 1, 0, 5
wave_in_progress, game_over, running, is_shop_open = True, False, True, False
wave_break_timer, active_boss = 0, None

SPAWN_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(SPAWN_EVENT, 1400)


def get_auto_aim_angle():
    closest, min_d = None, 999999
    for e in enemies:
        d = math.hypot(e.rect.centerx - player.rect.centerx, e.rect.centery - player.rect.centery)
        if d < min_d: min_d, closest = d, e
    return math.atan2(closest.rect.centery - player.rect.centery,
                      closest.rect.centerx - player.rect.centerx) if closest else player.angle


def reset_game():
    global score, wave, enemies_spawned, enemies_to_spawn, wave_in_progress, game_over, player, is_shop_open, active_boss
    all_sprites.empty();
    walls.empty();
    enemies.empty();
    bullets_group.empty();
    medkits.empty()
    for w in map_walls: walls.add(w); all_sprites.add(w)
    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3, walls)
    all_sprites.add(player)
    score, wave, enemies_spawned, enemies_to_spawn = 0, 1, 0, 5
    wave_in_progress, game_over, is_shop_open, active_boss = True, False, False, None


# --- ИГРОВОЙ ЦИКЛ ---
while running:
    clock.tick(FPS)
    now = pygame.time.get_ticks()

    t_pos = [pygame.mouse.get_pos()] if pygame.mouse.get_pressed() else []

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if game_over and event.type == pygame.MOUSEBUTTONDOWN: reset_game()

        if not game_over and not is_shop_open and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            click = [event.pos]
            px, py = player.rect.center
            angle = get_auto_aim_angle()

            if btn_reload_mob.is_pressed(click) and not player.is_reloading and player.ammo < player.max_ammo:
                player.is_reloading = True
                player.reload_timer = now + player.reload_duration
                snd_click.play()

            if not player.is_reloading and player.ammo > 0:
                if btn_pistol.is_pressed(click):
                    snd_pistol.play();
                    player.ammo -= 1
                    b = Bullet(px, py, angle);
                    bullets_group.add(b);
                    all_sprites.add(b)
                elif btn_shotgun.is_pressed(click) and now - player.last_shotgun_time > player.shotgun_cooldown:
                    snd_shotgun.play();
                    player.ammo = max(0, player.ammo - 2)
                    for a in [angle, angle - math.radians(12), angle + math.radians(12)]:
                        b = Bullet(px, py, a);
                        bullets_group.add(b);
                        all_sprites.add(b)
                    player.last_shotgun_time = now

        elif is_shop_open and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            click = [event.pos]
            if btn_shop_speed.is_pressed(click) and score >= 3:
                score -= 3;
                player.speed += 0.4;
                snd_heal.play()
            elif btn_shop_hp.is_pressed(click) and score >= 5:
                score -= 5;
                player.max_hp += 1;
                player.hp = player.max_hp;
                snd_heal.play()
            elif btn_shop_ammo.is_pressed(click) and score >= 4:
                score -= 4;
                player.max_ammo += 2;
                player.ammo = player.max_ammo;
                snd_heal.play()
            elif btn_shop_next.is_pressed(click):
                is_shop_open = False
                wave += 1
                enemies_spawned = 0
                if wave % 5 == 0:
                    enemies_to_spawn = 1
                    active_boss = Enemy(player, walls, wave, is_boss=True)
                    enemies.add(active_boss);
                    all_sprites.add(active_boss)
                else:
                    enemies_to_spawn = 5 + (wave * 2)
                wave_in_progress = True

        if event.type == SPAWN_EVENT and wave_in_progress and not game_over and not is_shop_open:
            if wave % 5 != 0 and enemies_spawned < enemies_to_spawn:
                e = Enemy(player, walls, wave);
                enemies.add(e);
                all_sprites.add(e);
                enemies_spawned += 1

    if not game_over and not is_shop_open and running:
        if player.is_reloading and now > player.reload_timer:
            player.ammo = player.max_ammo
            player.is_reloading = False

        dx, dy = 0, 0
        if btn_left.is_pressed(t_pos): dx = -player.speed
        if btn_right.is_pressed(t_pos): dx = player.speed
        if btn_up.is_pressed(t_pos): dy = -player.speed
        if btn_down.is_pressed(t_pos): dy = player.speed
        player.move(dx, dy, get_auto_aim_angle())

        all_sprites.update()

        if ((wave % 5 != 0 and enemies_spawned >= enemies_to_spawn) or (
                wave % 5 == 0 and active_boss and not active_boss.alive())) and len(enemies) == 0 and wave_in_progress:
            wave_in_progress = False
            is_shop_open = True

        pygame.sprite.groupcollide(bullets_group, walls, True, False)

        for e in pygame.sprite.groupcollide(enemies, bullets_group, False, True):
            e.hp -= 1
            if e.hp <= 0:
                snd_explosion.play();
                e.kill()
                if e.is_boss:
                    score += 15; active_boss = None
                else:
                    score += 1
                    if random.random() < 0.20:
                        m = Medkit(e.rect.centerx, e.rect.centery);
                        medkits.add(m);
                        all_sprites.add(m)

        for m in pygame.sprite.spritecollide(player, medkits, True):
            if player.hp < player.max_hp: snd_heal.play(); player.hp += 1

        if not player.is_invulnerable():
            for e in pygame.sprite.spritecollide(player, enemies, False):
                player.take_damage();
                snd_explosion.play()
                if not e.is_boss: e.kill()
                if player.hp <= 0: game_over = True

    # --- ОТРИСОВКА ЭКРАНА ---
    screen.fill(BG_COLOR)

    if is_shop_open:
        screen.blit(btn_font.render(f"МАГАЗИН УЛУЧШЕНИЙ (ДОСТУПНО ОЧКОВ: {score})", True, (255, 255, 255)), (180, 80))
        screen.blit(font.render(
            f"Текущая скорость: {player.speed:.1f} | Текущее HP: {player.max_hp} | Магазин: {player.max_ammo} пат.",
            True, (160, 160, 170)), (130, 130))
        btn_shop_speed.draw(screen, font, score >= 3)
        btn_shop_hp.draw(screen, font, score >= 5)
        btn_shop_ammo.draw(screen, font, score >= 4)
        btn_shop_next.draw(screen, font, True)
    else:
        if not (player.is_invulnerable() and (now // 100) % 2 == 0):
            all_sprites.draw(screen)
        else:
            for s in all_sprites:
                if s != player: screen.blit(s.image, s.rect)

        for btn in [btn_up, btn_down, btn_left, btn_right, btn_pistol, btn_shotgun, btn_reload_mob]:
            btn.draw(screen, btn_font)

        pygame.draw.rect(screen, (50, 50, 50), (10, 15, 150, 15), border_radius=4)
        if player.hp > 0: pygame.draw.rect(screen, PLAYER_COLOR, (10, 15, int(150 * (player.hp / player.max_hp)), 15),
                                           border_radius=4)

        ammo_txt = "ПЕРЕЗАРЯДКА..." if player.is_reloading else f"ПАТРОНЫ: {player.ammo}/{player.max_ammo}"
        screen.blit(font.render(ammo_txt, True, AMMO_COLOR), (175, 12))
        screen.blit(font.render(f"ОЧКИ: {score} | ВОЛНА: {wave}", True, (255, 255, 255)), (SCREEN_WIDTH - 220, 12))

        if wave % 5 == 0 and active_boss and active_boss.alive():
            pygame.draw.rect(screen, (50, 50, 50), (200, 45, 400, 16), border_radius=4)
            pygame.draw.rect(screen, ENEMY_BOSS_COLOR, (200, 45, int(400 * (active_boss.hp / active_boss.max_hp)), 16),
                             border_radius=4)
            screen.blit(font.render("ЗДОРОВЬЕ СУПЕР-БОССА", True, (255, 255, 255)), (320, 43))

    if game_over:
        go_surf = btn_font.render("ИГРА ОКОНЧЕНА! Нажмите на экран для рестарта", True, (255, 70, 70))
        screen.blit(go_surf, go_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)))

    pygame.display.flip()

pygame.quit()
sys.exit()
