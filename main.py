import pygame
import sys
import math
import mysql.connector

# ---------- Indstillinger ----------
MAP_FILENAME = "map.png"
SCREEN_W, SCREEN_H = 900, 600
PLAYER_SIZE = 28
PLAYER_SPEED = 250
FPS = 60
# ------------------------------------
# ---------- MySQL forbindelses-info ----------
DB_HOST = "localhost"
DB_USER = "bammanx"
DB_PASS = "1"
DB_NAME = "store"
# ---------------------------------------------

# ------------------ TEGNING ------------------
def draw_arrow(surface, x, y, angle):
    length = 30
    width = 12

    points = [
        (0, -length),
        (width, length),
        (-width, length)
    ]

    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    rotated = []

    for px, py in points:
        rx = px * cos_a - py * sin_a
        ry = px * sin_a + py * cos_a
        rotated.append((x + rx, y + ry))

    pygame.draw.polygon(surface, (255, 0, 0), rotated)
# --------------------------------------------------


def db_init():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS
        )
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.commit()
        cur.close()
        conn.close()

        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                navn VARCHAR(255) NOT NULL,
                x INT NOT NULL,
                y INT NOT NULL
            )
        """)

        cur.execute("SELECT COUNT(*) FROM items")
        count = cur.fetchone()[0]

        if count == 0:
            cur.executemany(
                "INSERT INTO items (navn, x, y) VALUES (%s, %s, %s)",
                [
                    ("frugt", 740, 900),
                    ("chips", 1340, 1050),
                    ("sodavand", 900, 290),
                    ("gedeost", 1980, 260),
                    ("sandwich", 840, 1000),
                    ("blandselv slik", 840, 1010),
                    ("kage", 850, 460)
                ]
            )

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("DB init fejl:", e)


def db_search_item(navn):
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cursor = conn.cursor()
        cursor.execute("SELECT x, y FROM items WHERE navn = %s LIMIT 1", (navn,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        print("MySQL fejl:", e)
        return None


def db_insert_item(name, x, y):
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO items (navn, x, y) VALUES (%s, %s, %s)",
            (name, x, y)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Fejl ved indsættelse:", e)


def build_obstacle_mask(surface):
    w, h = surface.get_size()
    mask = pygame.Mask((w, h))
    px = pygame.PixelArray(surface)
    black = surface.map_rgb((0, 0, 0))
    for y in range(h):
        row = px[:, y]
        for x in range(w):
            if row[x] == black:
                mask.set_at((x, y), 1)
    del px
    return mask


def create_player_surface(size):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255, 200, 0), (size//2, size//2), size//2)
    return surf


def main():
    db_init()

    pygame.init()
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Kort + MySQL søgning + pil mod item")

    map_surf = pygame.image.load(MAP_FILENAME).convert()
    MAP_W, MAP_H = map_surf.get_size()

    obstacle_mask = build_obstacle_mask(map_surf)

    player_surf = create_player_surface(PLAYER_SIZE)
    player_mask = pygame.mask.from_surface(player_surf)

    player_x = MAP_W // 2
    player_y = MAP_H // 2

    zoom = 0.5

    scaled_map_w = int(MAP_W * zoom)
    scaled_map_h = int(MAP_H * zoom)

    scaled_map_surf = pygame.transform.smoothscale(
        map_surf, (scaled_map_w, scaled_map_h)
    )
    scaled_player_size = int(PLAYER_SIZE * zoom)
    scaled_player_surf = create_player_surface(scaled_player_size)
    scaled_player_mask = pygame.mask.from_surface(scaled_player_surf)

    # ----------- Søgefelt -----------
    font = pygame.font.SysFont(None, 28)
    search_text = ""
    search_active = False
    show_red_dot = False
    dot_x = 0
    dot_y = 0
    search_rect = pygame.Rect(SCREEN_W - 220, 10, 200, 32)

    # --- BLINKENDE MARKØR ---
    caret_visible = True
    caret_timer = 0.0
    CARET_BLINK_TIME = 0.5
    # ------------------------

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # ----- caret blink logik -----
        if search_active:
            caret_timer += dt
            if caret_timer >= CARET_BLINK_TIME:
                caret_visible = not caret_visible
                caret_timer = 0.0
        else:
            caret_visible = False
            caret_timer = 0.0
        # ----------------------------

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                search_active = search_rect.collidepoint(event.pos)

            if event.type == pygame.KEYDOWN and search_active:
                if event.key == pygame.K_BACKSPACE:
                    search_text = search_text[:-1]
                elif event.key == pygame.K_RETURN:
                    result = db_search_item(search_text.lower())
                    if result:
                        dot_x, dot_y = result
                        show_red_dot = True
                    else:
                        show_red_dot = False
                else:
                    if len(search_text) < 20:
                        search_text += event.unicode

            if event.type == pygame.KEYDOWN and not search_active:
                if event.key == pygame.K_e:
                    db_insert_item("nyt_item", int(player_x), int(player_y))

        if not search_active:
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_w]: dy -= 1
            if keys[pygame.K_s]: dy += 1
            if keys[pygame.K_a]: dx -= 1
            if keys[pygame.K_d]: dx += 1

            if dx != 0 or dy != 0:
                inv = 1 / (abs(dx) + abs(dy))
                dx *= inv
                dy *= inv

            new_x = player_x + dx * PLAYER_SPEED * dt
            new_y = player_y + dy * PLAYER_SPEED * dt

            if obstacle_mask.overlap(player_mask, (int(new_x), int(player_y))) is None:
                player_x = new_x
            if obstacle_mask.overlap(player_mask, (int(player_x), int(new_y))) is None:
                player_y = new_y

        cam_x = int((player_x + PLAYER_SIZE//2) * zoom - SCREEN_W / 2)
        cam_y = int((player_y + PLAYER_SIZE//2) * zoom - SCREEN_H / 2)
        cam_x = max(0, min(cam_x, scaled_map_w - SCREEN_W))
        cam_y = max(0, min(cam_y, scaled_map_h - SCREEN_H))

        screen.blit(
            scaled_map_surf,
            (0, 0),
            pygame.Rect(cam_x, cam_y, SCREEN_W, SCREEN_H)
        )

        player_screen_x = int(player_x * zoom) - cam_x
        player_screen_y = int(player_y * zoom) - cam_y
        screen.blit(scaled_player_surf, (player_screen_x, player_screen_y))

        if show_red_dot:
            rx = int(dot_x * zoom) - cam_x
            ry = int(dot_y * zoom) - cam_y
            if 0 <= rx <= SCREEN_W and 0 <= ry <= SCREEN_H:
                pygame.draw.circle(screen, (255, 0, 0), (rx, ry), int(8 * zoom))
            else:
                dxp = dot_x - player_x
                dyp = dot_y - player_y
                angle = math.atan2(dyp, dxp)
                draw_arrow(
                    screen,
                    player_screen_x + scaled_player_size // 2,
                    player_screen_y + scaled_player_size // 2,
                    angle + math.pi / 2
                )

        coords = font.render(
            f"X: {int(player_x)}, Y: {int(player_y)}", True, (0, 0, 0)
        )
        screen.blit(coords, (10, 10))

        # -------- SØGEFELT + CARET --------
        color = (70, 70, 70) if search_active else (40, 40, 40)
        pygame.draw.rect(screen, color, search_rect)

        text_surf = font.render(search_text, True, (255, 255, 255))
        screen.blit(text_surf, (search_rect.x + 5, search_rect.y + 5))

        if search_active and caret_visible:
            cx = search_rect.x + 5 + text_surf.get_width() + 2
            cy = search_rect.y + 6
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (cx, cy),
                (cx, cy + text_surf.get_height()),
                2
            )
        # ---------------------------------

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
