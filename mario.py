#pose runner
import pygame
import sys
import math
import random

#env
SKY = (107, 187, 255)
SUN_COL = (255, 230, 80)
CLOUD_COL = (255, 255, 255)
GRASS_TOP = (92, 184, 92)
GRASS_BOT = (68, 148, 68)
DIRT_COL = (181, 130, 77)
COIN_COL = (255, 210, 0)
ENEMY_COL = (210, 80, 60)
ENEMY_EYE = (255, 255, 255)
HUD_COL = (255, 255, 255)
FLAG_COL = (255, 60, 60)

# ── tuneable ──────────────────────────────────────────────────────────────────
GRAVITY = 0.55
JUMP_SPEED = -13.0
MOVE_SPEED = 4.5
SCREEN_W = 960
SCREEN_H = 540
TILE = 40
FPS = 60
WORLD_W = 80  # tiles wide
DUCK_SPEED = 1.8


# ─────────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════════
#  Sprites
# ═══════════════════════════════════════════════════════════════════════════════

class Player(pygame.sprite.Sprite):
    W, H = 34, 42

    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._draw_idle()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1  # 1=right, -1=left
        self.ducking = False
        self.alive = True
        self.score = 0
        self._anim_t = 0
        self._walk_frame = 0

    # ── drawing ──────────────────────────────────────────────────────────────



    def _draw_idle(self, duck=False):
        s = self.image
        s.fill((0, 0, 0, 0))
        w, h = self.W, self.H
        body_h = h // 2 if duck else h

        # hat
        pygame.draw.rect(s, (200, 50, 50), (4, 0, w - 8, 10), border_radius=4)
        # face
        pygame.draw.ellipse(s, (255, 205, 148), (6, 6, w - 12, 16))
        # eyes
        pygame.draw.circle(s, (30, 30, 30), (12, 12), 2)
        pygame.draw.circle(s, (30, 30, 30), (w - 12, 12), 2)
        # body
        body_top = 20 if not duck else 26
        body_bot = body_h
        pygame.draw.rect(s, (60, 100, 200), (4, body_top, w - 8, body_bot - body_top), border_radius=5)
        # overalls stripe
        pygame.draw.rect(s, (50, 80, 180), (w // 2 - 5, body_top + 3, 10, 6), border_radius=2)
        if not duck:
            # legs
            pygame.draw.rect(s, (200, 50, 50), (4, h - 14, 12, 14), border_radius=3)
            pygame.draw.rect(s, (200, 50, 50), (w - 16, h - 14, 12, 14), border_radius=3)

    def _draw_walk(self, frame):
        s = self.image
        s.fill((0, 0, 0, 0))
        w, h = self.W, self.H
        # base
        self._draw_idle()
        # animate legs
        leg_offset = int(math.sin(frame * 0.7) * 6)
        pygame.draw.rect(s, (200, 50, 50), (4, h - 14 - leg_offset, 12, 14), border_radius=3)
        pygame.draw.rect(s, (200, 50, 50), (w - 16, h - 14 + leg_offset, 12, 14), border_radius=3)

    def _draw_jump(self):
        self._draw_idle()




    def _draw_duck(self):
        s = self.image
        s.fill((0, 0, 0, 0))
        self._draw_idle(duck=True)










    # ── update ───────────────────────────────────────────────────────────────

    def update(self, platforms, enemies, coins, pose_state, kb):
        if not self.alive:
            return

        self._handle_input(pose_state, kb)
        self._apply_physics(platforms)
        self._check_enemies(enemies)
        self._check_coins(coins)
        self._animate()

    def _handle_input(self, ps, kb):
        # keyboard fallback
        keys = pygame.key.get_pressed()
        move_left = keys[pygame.K_LEFT] or keys[pygame.K_a] or (ps and ps.get("left"))
        move_right = keys[pygame.K_RIGHT] or keys[pygame.K_d] or (ps and ps.get("right"))
        jump = keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE] or (ps and ps.get("jump"))
        duck = keys[pygame.K_DOWN] or keys[pygame.K_s] or (ps and ps.get("duck"))

        speed = DUCK_SPEED if duck else MOVE_SPEED
        if move_left:
            self.vx = -speed
            self.facing = -1
        elif move_right:
            self.vx = speed
            self.facing = 1
        else:
            self.vx *= 0.75  # friction

        if jump and self.on_ground:
            self.vy = JUMP_SPEED
            self.on_ground = False

        self.ducking = duck and self.on_ground

    def _apply_physics(self, platforms):
        self.vy += GRAVITY
        self.rect.x += int(self.vx)
        self._collide_x(platforms)
        self.rect.y += int(self.vy)
        self._collide_y(platforms)

        # world bounds
        if self.rect.left < 0:
            self.rect.left = 0
            self.vx = 0

    def _collide_x(self, platforms):
        for p in pygame.sprite.spritecollide(self, platforms, False):
            if self.vx > 0:
                self.rect.right = p.rect.left
            elif self.vx < 0:
                self.rect.left = p.rect.right
            self.vx = 0

    def _collide_y(self, platforms):
        self.on_ground = False
        for p in pygame.sprite.spritecollide(self, platforms, False):
            if self.vy > 0:
                self.rect.bottom = p.rect.top
                self.on_ground = True
            elif self.vy < 0:
                self.rect.top = p.rect.bottom
            self.vy = 0

    def _check_enemies(self, enemies):
        for e in pygame.sprite.spritecollide(self, enemies, False):
            if self.vy > 0 and self.rect.bottom < e.rect.centery + 10:
                e.kill()
                self.vy = -8
                self.score += 100
            else:
                self.alive = False

    def _check_coins(self, coins):
        for c in pygame.sprite.spritecollide(self, coins, True):
            self.score += 10

    def _animate(self):
        self._anim_t += 1
        if self.ducking:
            self._draw_duck()
        elif not self.on_ground:
            self._draw_jump()
        elif abs(self.vx) > 0.5:
            self._walk_frame += 1
            self._draw_walk(self._walk_frame)
        else:
            self._draw_idle()

        if self.facing == -1:
            self.image = pygame.transform.flip(self.image, True, False)





class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h=TILE, floating=False):
        super().__init__()
        self.image = pygame.Surface((w, h))
        if floating:
            # question-block style
            self.image.fill((220, 180, 50))
            pygame.draw.rect(self.image, (180, 140, 30), (0, 0, w, h), 3)
            for i in range(0, w, TILE):
                pygame.draw.rect(self.image, (255, 210, 80), (i + 4, 4, TILE - 8, h - 8), border_radius=4)
        else:
            # ground tile
            self.image.fill(DIRT_COL)
            pygame.draw.rect(self.image, GRASS_TOP, (0, 0, w, 10))
            for i in range(0, w, 20):
                pygame.draw.line(self.image, GRASS_BOT, (i, 0), (i, 10), 1)
        self.rect = self.image.get_rect(topleft=(x, y))


class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(self.image, COIN_COL, (7, 7), 7)
        pygame.draw.circle(self.image, (255, 240, 120), (5, 5), 3)
        self.rect = self.image.get_rect(center=(x, y))


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_range=120):
        super().__init__()
        self.image = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(bottomleft=(x, y))
        self.speed = 1.5
        self._origin_x = x
        self._patrol = patrol_range
        self._dir = 1

    def _draw(self):
        s, t = self.image, TILE
        s.fill((0, 0, 0, 0))
        # body
        pygame.draw.ellipse(s, ENEMY_COL, (2, t // 3, t - 4, t * 2 // 3))
        # head / eyes
        pygame.draw.circle(s, ENEMY_COL, (t // 2, t // 4), t // 4)
        pygame.draw.circle(s, ENEMY_EYE, (t // 2 - 7, t // 4), 5)
        pygame.draw.circle(s, ENEMY_EYE, (t // 2 + 7, t // 4), 5)
        pygame.draw.circle(s, (20, 20, 20), (t // 2 - 6, t // 4), 2)
        pygame.draw.circle(s, (20, 20, 20), (t // 2 + 6, t // 4), 2)
        # angry brows
        pygame.draw.line(s, (20, 20, 20), (t // 2 - 11, t // 4 - 5), (t // 2 - 3, t // 4 - 2), 2)
        pygame.draw.line(s, (20, 20, 20), (t // 2 + 3, t // 4 - 2), (t // 2 + 11, t // 4 - 5), 2)

    def update(self):
        self.rect.x += self._dir * self.speed
        if abs(self.rect.x - self._origin_x) > self._patrol:
            self._dir *= -1


class Flag(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 80), pygame.SRCALPHA)
        pygame.draw.line(self.image, (180, 180, 180), (4, 0), (4, 79), 3)
        pygame.draw.polygon(self.image, FLAG_COL, [(4, 0), (20, 10), (4, 20)])
        self.rect = self.image.get_rect(bottomleft=(x, y))


# ═══════════════════════════════════════════════════════════════════════════════
#  Level builder
# ═══════════════════════════════════════════════════════════════════════════════

def build_level():
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    ground_y = SCREEN_H - TILE
    world_px = WORLD_W * TILE

    # ── continuous ground with a few gaps ─────────────────────────────────
    gap_positions = {18, 19, 35, 36, 55, 56}
    x = 0
    while x < world_px:
        tile_col = x // TILE
        if tile_col not in gap_positions:
            platforms.add(Platform(x, ground_y, TILE))
            # two rows deep
            platforms.add(Platform(x, ground_y + TILE, TILE))
        x += TILE

    # ── floating platforms ─────────────────────────────────────────────────
    floaters = [
        (6, ground_y - 3 * TILE, 3),
        (12, ground_y - 4 * TILE, 2),
        (17, ground_y - 2 * TILE, 4),
        (22, ground_y - 5 * TILE, 2),
        (28, ground_y - 3 * TILE, 3),
        (33, ground_y - 4 * TILE, 2),
        (38, ground_y - 3 * TILE, 4),
        (45, ground_y - 5 * TILE, 3),
        (50, ground_y - 2 * TILE, 2),
        (57, ground_y - 4 * TILE, 3),
        (63, ground_y - 3 * TILE, 2),
        (68, ground_y - 5 * TILE, 3),
        (73, ground_y - 3 * TILE, 3),
    ]
    for (tx, py, tw) in floaters:
        platforms.add(Platform(tx * TILE, py, tw * TILE, TILE // 2, floating=True))

        # coins above floaters
        for ci in range(tw):
            coins.add(Coin((tx + ci) * TILE + TILE // 2, py - 20))

    # ── coins on ground stretches ─────────────────────────────────────────
    coin_tiles = [3, 5, 8, 10, 25, 27, 30, 40, 43, 48, 60, 65, 70]
    for ct in coin_tiles:
        coins.add(Coin(ct * TILE + TILE // 2, ground_y - 30))

    # ── enemies ───────────────────────────────────────────────────────────
    enemy_positions = [8, 15, 24, 31, 42, 52, 62, 70]
    for ep in enemy_positions:
        enemies.add(Enemy(ep * TILE, ground_y, patrol_range=100))

    # ── flag at end ────────────────────────────────────────────────────────
    flag = Flag((WORLD_W - 3) * TILE, ground_y)

    return platforms, coins, enemies, flag


# ═══════════════════════════════════════════════════════════════════════════════
#  Background
# ═══════════════════════════════════════════════════════════════════════════════

class Background:
    def __init__(self, world_px):
        # pre-generate clouds and hills
        rng = random.Random(42)
        self.clouds = [
            (rng.randint(0, world_px), rng.randint(30, 140), rng.randint(60, 140))
            for _ in range(35)
        ]
        self.hills = [
            (rng.randint(0, world_px), SCREEN_H - TILE - rng.randint(40, 120), rng.randint(80, 200))
            for _ in range(20)
        ]

    def draw(self, surf, cam_x):
        surf.fill(SKY)

        # sun (fixed screen position)
        pygame.draw.circle(surf, SUN_COL, (SCREEN_W - 80, 60), 36)

        # parallax hills (50 % speed)
        for hx, hy, hr in self.hills:
            sx = hx - cam_x * 0.5
            if -hr < sx < SCREEN_W + hr:
                pygame.draw.ellipse(surf, (80, 170, 80), (sx - hr, hy, hr * 2, SCREEN_H - hy))

        # parallax clouds (30 % speed)
        for cx, cy, cw in self.clouds:
            sx = cx - cam_x * 0.3
            if -cw < sx < SCREEN_W + cw:
                ch = cw // 2
                pygame.draw.ellipse(surf, CLOUD_COL, (sx, cy, cw, ch))
                pygame.draw.ellipse(surf, CLOUD_COL, (sx + cw // 4, cy - ch // 2, cw // 2, ch))


# ═══════════════════════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════════════════════

class HUD:
    def __init__(self):
        self.font_big = pygame.font.SysFont("consolas", 26, bold=True)
        self.font_sml = pygame.font.SysFont("consolas", 17)

    def draw(self, surf, player, pose_active):
        # score
        txt = self.font_big.render(f"SCORE  {player.score:06d}", True, HUD_COL)
        surf.blit(txt, (20, 12))

        # pose status
        status = "🎮 POSE ON" if pose_active else "⌨  KEYBOARD MODE"
        col = (80, 255, 120) if pose_active else (255, 220, 60)
        stxt = self.font_sml.render(status, True, col)
        surf.blit(stxt, (SCREEN_W - stxt.get_width() - 20, 16))

        if not player.alive:
            self._center_msg(surf, "GAME OVER  —  press R to restart", (255, 80, 80))

    def _center_msg(self, surf, msg, color):
        f = pygame.font.SysFont("consolas", 36, bold=True)
        t = f.render(msg, True, color)
        surf.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2)))


# ═══════════════════════════════════════════════════════════════════════════════
#  Game
# ═══════════════════════════════════════════════════════════════════════════════

class Game:
    def __init__(self, pose_controller=None):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("PoseRunner 🎮")
        self.clock = pygame.time.Clock()
        self.pose = pose_controller
        self._setup()

    def _setup(self):
        self.platforms, self.coins, self.enemies, self.flag = build_level()
        self.player = Player(80, SCREEN_H - TILE * 3)
        self.all_sprites = pygame.sprite.Group(
            *self.platforms, *self.coins, *self.enemies, self.flag, self.player
        )
        self.bg = Background(WORLD_W * TILE)
        self.hud = HUD()
        self.cam_x = 0.0

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._quit()
                if event.key == pygame.K_r:
                    self._setup()

    def _quit(self):
        if self.pose:
            self.pose.stop()
        pygame.quit()
        sys.exit()

    def _update(self):
        pose_state = self.pose.get_state() if self.pose else None
        kb = None  # keyboard handled inside player

        self.player.update(self.platforms, self.enemies, self.coins, pose_state, kb)
        self.enemies.update()

        # smooth camera
        target_cam = self.player.rect.centerx - SCREEN_W // 3
        max_cam = WORLD_W * TILE - SCREEN_W
        target_cam = max(0, min(target_cam, max_cam))
        self.cam_x += (target_cam - self.cam_x) * 0.12

        # kill-floor
        if self.player.rect.top > SCREEN_H + 50:
            self.player.alive = False

    def _draw(self):
        cam = int(self.cam_x)
        self.bg.draw(self.screen, cam)

        # draw all sprites offset by camera
        for sprite in [*self.platforms, *self.coins, self.flag, *self.enemies, self.player]:
            r = sprite.rect.move(-cam, 0)
            if -TILE < r.right and r.left < SCREEN_W:
                self.screen.blit(sprite.image, r)

        pose_active = bool(self.pose and self.pose.get_state().get("active"))
        self.hud.draw(self.screen, self.player, pose_active)
        pygame.display.flip()


game = Game()
game.run()
