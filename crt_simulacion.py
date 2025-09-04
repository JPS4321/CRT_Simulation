import pygame
import math
import sys
from typing import Callable, Tuple, List

# =========================
# Configuración general
# =========================
WIDTH, HEIGHT = 1180, 700
FPS = 60

# Paleta tipo CRT
BLACK   = (5, 8, 7)
PHOS_BG = (8, 40, 18)
PHOS_GRID = (20, 80, 40)
PHOS_TRACE = (10, 255, 90)
METAL  = (185, 190, 195)
METAL_DARK = (120, 125, 130)
METAL_PANEL = (160, 165, 170)
WHITE  = (235, 235, 235)
TEXT   = (220, 230, 230)
GREY   = (60, 65, 70)
HILITE = (250, 255, 255)

pygame.init()
pygame.display.set_caption("Osciloscopio Retro - Simulación CRT (Vista lateral + Pantalla)")
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Tipografías
FONT_XXS = pygame.font.SysFont("consolas", 11)
FONT_XS  = pygame.font.SysFont("consolas", 12)
FONT_S   = pygame.font.SysFont("consolas", 14)
FONT_M   = pygame.font.SysFont("consolas", 18, bold=True)

# =========================
# Layout de la “carcasa”
# =========================
OUTER = pygame.Rect(10, 10, WIDTH-20, HEIGHT-20)

# Pantalla verde más baja para dar aire al panel inferior
CRT_RECT  = pygame.Rect(420, 40, 700, 410)

# Diagrama a la izquierda, alineado verticalmente con la pantalla
DIAG_W, DIAG_H = 360, 250
DIAG_RECT = pygame.Rect(30, CRT_RECT.centery - DIAG_H//2, DIAG_W, DIAG_H)

# Panel inferior y sus tres zonas
PANEL = pygame.Rect(20, CRT_RECT.bottom + 15, WIDTH-40, HEIGHT - CRT_RECT.bottom - 30)
PAD = 14
LEFT_ZONE   = pygame.Rect(PANEL.x+PAD, PANEL.y+PAD, 380, PANEL.height-2*PAD)          # manecillas
CENTER_ZONE = pygame.Rect(LEFT_ZONE.right+PAD, PANEL.y+PAD, 180, PANEL.height-2*PAD)  # modo/apagar
RIGHT_ZONE  = pygame.Rect(CENTER_ZONE.right+PAD, PANEL.y+PAD,
                          PANEL.right-(CENTER_ZONE.right+2*PAD), PANEL.height-2*PAD)  # presets

# =========================
# Estado de la simulación
# =========================
voltaje_aceleracion = 500
voltaje_vertical = 0
voltaje_horizontal = 0

modo_sinusoidal = False
freq_x = 1.0
freq_y = 1.0
fase_x = 0.0
fase_y = 0.0

persistencia = 150
trayectoria: List[Tuple[int,int]] = []

t = 0.0
dt = 1.0 / FPS

# Ajustes de fase por relación y flips para que se vean “como en laboratorio”
PRESET_OFFSETS = {
    "1:1": (0,   0),
    "1:2": (0,  90),
    "1:3": (180, 0),
    "2:3": (90,  0),
}
FLIPS = {
    "1:1": (1,  1),
    "1:2": (1, -1),
    "1:3": (1,  1),
    "2:3": (-1, 1),
}

def obtener_posicion(tiempo: float) -> Tuple[float, float]:
    """Devuelve la posición normalizada del haz (x, y) en [-1, 1]."""
    if modo_sinusoidal:
        x = math.sin(2*math.pi*freq_x*tiempo + fase_x)
        y = math.sin(2*math.pi*freq_y*tiempo + fase_y)
        key = f"{int(freq_x)}:{int(freq_y)}"
        if key in FLIPS:
            fx, fy = FLIPS[key]; x *= fx; y *= fy
    else:
        x = max(-1, min(1, voltaje_horizontal / 100.0))
        y = max(-1, min(1, voltaje_vertical   / 100.0))
    return x, y

def to_rect(x: float, y: float, rect: pygame.Rect) -> Tuple[int,int]:
    """Escala coordenadas [-1,1] al rectángulo dado, con un pequeño margen."""
    margin = 28
    hw = (rect.width  - 2*margin) / 2
    hh = (rect.height - 2*margin) / 2
    px = int(rect.centerx + x * hw)
    py = int(rect.centery - y * hh)
    return px, py

# =========================
# Controles UI
# =========================
def clamp(v, a, b): 
    return max(a, min(b, v))

# Perillas: parámetros de sensibilidad (más tranquilas de manejar)
ANGLE_MIN = -140
ANGLE_MAX =  140
DEAD_ZONE = 6
SENS_DRAG = 0.08
SENS_WHEEL = 0.5
SENS_WHEEL_FINE = 0.1

class Knob:
    """Perilla tipo osciloscopio: giro normal, ajuste fino (SHIFT) y rueda."""
    def __init__(self, x, y, r, min_val, max_val, value, label, step=1, default=None):
        self.x, self.y, self.r = x, y, r
        self.min_val, self.max_val = min_val, max_val
        self.value = clamp(value, min_val, max_val)
        self.default = value if default is None else default
        self.label = label
        self.step = step
        self.drag_angle = False
        self.drag_linear = False
        self._last_my = 0

    @property
    def rect(self): 
        return pygame.Rect(self.x-self.r, self.y-self.r, 2*self.r, 2*self.r)

    def _val_to_angle(self, v):
        frac = (v - self.min_val) / (self.max_val - self.min_val or 1)
        return math.radians(ANGLE_MIN + frac * (ANGLE_MAX - ANGLE_MIN))

    def _angle_to_val(self, ang):
        deg = math.degrees(ang)
        while deg <= -180: deg += 360
        while deg >   180: deg -= 360
        deg = clamp(deg, ANGLE_MIN, ANGLE_MAX)
        frac = (deg - ANGLE_MIN) / (ANGLE_MAX - ANGLE_MIN)
        v = self.min_val + frac * (self.max_val - self.min_val)
        v = round(v / self.step) * self.step
        return clamp(v, self.min_val, self.max_val)

    def set_value(self, v):
        self.value = clamp(v, self.min_val, self.max_val)
        self.drag_angle = False
        self.drag_linear = False

    def handle_event(self, e):
        # Click izquierdo: giro o modo fino (si mantienes SHIFT)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                self.drag_linear = True
                self._last_my = e.pos[1]
            else:
                self.drag_angle = True

        # Click derecho: vuelve al valor por defecto
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.rect.collidepoint(e.pos):
            self.set_value(self.default)

        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.drag_angle = False
            self.drag_linear = False

        elif e.type == pygame.MOUSEMOTION:
            if self.drag_angle:
                mx, my = e.pos
                # Si el puntero pasa por el centro, ignoramos para evitar saltos raros
                if (mx - self.x) ** 2 + (my - self.y) ** 2 < DEAD_ZONE ** 2:
                    return
                ang = math.atan2(my - self.y, mx - self.x) - math.pi / 2
                self.value = self._angle_to_val(ang)
            elif self.drag_linear:
                dy = e.pos[1] - self._last_my
                if dy:
                    self.value = clamp(
                        self.value - dy * self.step * SENS_DRAG,
                        self.min_val, self.max_val
                    )
                    self._last_my = e.pos[1]

        # Rueda del mouse: suave y con SHIFT aún más fino
        elif e.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            inc = self.step * (SENS_WHEEL_FINE if (pygame.key.get_mods() & pygame.KMOD_SHIFT) else SENS_WHEEL)
            self.value = clamp(self.value + e.y * inc, self.min_val, self.max_val)

    def draw(self, surf):
        mouse_over = self.rect.collidepoint(pygame.mouse.get_pos())

        pygame.draw.circle(surf, METAL, (self.x, self.y), self.r)
        pygame.draw.circle(surf, METAL_DARK, (self.x, self.y), self.r, 2)
        if mouse_over:
            pygame.draw.circle(surf, HILITE, (self.x, self.y), self.r, 1)

        # marcas del dial
        for i in range(ANGLE_MIN, ANGLE_MAX+1, 20):
            ang = math.radians(i)
            r1 = self.r-2; r2 = self.r-7
            x1 = int(self.x + r1*math.sin(ang)); y1 = int(self.y - r1*math.cos(ang))
            x2 = int(self.x + r2*math.sin(ang)); y2 = int(self.y - r2*math.cos(ang))
            pygame.draw.line(surf, GREY, (x1,y1), (x2,y2), 2)

        # aguja
        ang = self._val_to_angle(self.value)
        lx = int(self.x + (self.r-9) * math.sin(ang))
        ly = int(self.y - (self.r-9) * math.cos(ang))
        pygame.draw.line(surf, BLACK, (self.x, self.y), (lx, ly), 4)
        pygame.draw.circle(surf, WHITE, (self.x, self.y), 3)

        # texto
        lab = FONT_XS.render(self.label, True, TEXT)
        surf.blit(lab, (self.x - lab.get_width()//2, self.y + self.r + 4))
        valtxt = FONT_XXS.render(self._value_label(), True, TEXT)
        surf.blit(valtxt, (self.x - valtxt.get_width()//2, self.y + self.r + 18))

    def _value_label(self):
        rng = self.max_val - self.min_val
        if rng <= 10: return f"{self.value:.2f}"
        if rng <= 100: return f"{self.value:.1f}"
        return f"{int(round(self.value))}"

class Button:
    """Botón sencillo estilo panel metálico."""
    def __init__(self, rect: pygame.Rect, text: str, action: Callable, small=False):
        self.rect = rect
        self.text = text
        self.action = action
        self.small = small
        self._down = False

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self._down = True
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self._down and self.rect.collidepoint(e.pos):
                self.action()
            self._down = False

    def draw(self, surf):
        mouse_over = self.rect.collidepoint(pygame.mouse.get_pos())
        col = (200,205,210) if mouse_over else METAL
        if self._down: col = METAL_DARK
        pygame.draw.rect(surf, col, self.rect, border_radius=6)
        pygame.draw.rect(surf, GREY, self.rect, 2, border_radius=6)
        font = FONT_XXS if self.small else FONT_S
        txt = font.render(self.text, True, BLACK)
        surf.blit(txt, (self.rect.centerx - txt.get_width()//2,
                        self.rect.centery - txt.get_height()//2))

# =========================
# Dibujo de elementos
# =========================
def draw_beam_on_crt(px, py):
    """Punto brillante del haz con un pequeño halo."""
    for r, a in [(8, 40), (5, 90), (3, 160)]:
        s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*PHOS_TRACE, a), (r+1, r+1), r)
        screen.blit(s, (px-r-1, py-r-1))
    pygame.draw.circle(screen, PHOS_TRACE, (px, py), 1)

def draw_tube_outline(surface, rect, y_norm: float):
    """Mini diagrama lateral del CRT con el rayo moviéndose en Y."""
    pygame.draw.rect(surface, (20,20,25), rect.inflate(-10,-10), 0, border_radius=8)
    pygame.draw.rect(surface, GREY, rect.inflate(-10,-10), 2, border_radius=8)

    x0, y0, w, h = rect.inflate(-30, -30)
    midy = y0 + h//2
    left = x0 + 30
    right = x0 + w - 30

    pygame.draw.rect(surface, WHITE, (left-15, midy-12, 70, 24), 2)  # cañón

    for i in range(3):  # ánodos
        pygame.draw.rect(surface, WHITE, (left + i*18, midy-6, 10, 12), 2)

    plates_x = left + 70 + 18  # placas verticales
    pygame.draw.rect(surface, WHITE, (plates_x, midy-28, 30, 10), 2)
    pygame.draw.rect(surface, WHITE, (plates_x, midy+18, 30, 10), 2)
    surface.blit(FONT_XS.render("Vert. defl. plates", True, TEXT), (plates_x-6, midy-46))

    neck_x = plates_x + 48  # cono y pantalla
    pygame.draw.polygon(surface, WHITE, [(neck_x, midy-20), (neck_x, midy+20), (right-25, midy)], 2)

    face_radius = max(18, min(32, (h // 5)))
    screen_center = (right, midy)
    pygame.draw.circle(surface, WHITE, screen_center, face_radius, 2)
    pygame.draw.rect(surface, GREY,
                     pygame.Rect(screen_center[0]-face_radius-5, screen_center[1]-face_radius,
                                 5, 2*face_radius), 1)

    # rayo hasta el borde de la pantalla
    target = (screen_center[0] - face_radius, int(screen_center[1] - y_norm * face_radius))
    pygame.draw.line(surface, WHITE, (left-15, midy), (neck_x, midy), 2)
    pygame.draw.line(surface, WHITE, (neck_x, midy), target, 2)

def draw_panel_chasis():
    """Bordes y cajas del panel inferior."""
    pygame.draw.rect(screen, METAL_PANEL, PANEL, border_radius=8)
    pygame.draw.rect(screen, GREY, PANEL, 2, border_radius=8)
    pygame.draw.rect(screen, (150,150,155), LEFT_ZONE, 1, border_radius=6)
    pygame.draw.rect(screen, (150,150,155), CENTER_ZONE, 1, border_radius=6)
    pygame.draw.rect(screen, (150,150,155), RIGHT_ZONE, 1, border_radius=6)

# =========================
# Presets
# =========================
PRESET_SPECS = [
    ("1:1", 0), ("1:1", 45), ("1:1", 90), ("1:1", 135), ("1:1", 180),
    ("1:2", 0), ("1:2", 45), ("1:2", 90), ("1:2", 135), ("1:2", 180),
    ("1:3", 0), ("1:3", 45), ("1:3", 90), ("1:3", 135), ("1:3", 180),
    ("2:3", 0), ("2:3", 45), ("2:3", 90), ("2:3", 135), ("2:3", 180),
]

def aplicar_preset_en_perillas(ratio: str, delta_deg: int):
    """Cuando pulsas un preset, actualiza perillas y listo."""
    fx, fy = map(int, ratio.split(":"))
    base_x, base_y = PRESET_OFFSETS[ratio]
    phix = base_x % 360
    phiy = (base_y + delta_deg) % 360
    knob_fx.set_value(fx)
    knob_fy.set_value(fy)
    knob_phix.set_value(phix)
    knob_phiy.set_value(phiy)

# =========================
# Construcción de controles
# =========================
knobs: List[Knob] = []

# Manecillas (izquierda)
RADIUS = 18
gapy   = 50
gapx   = 86
ky0 = LEFT_ZONE.y + 40
kx0 = LEFT_ZONE.x + 70

knob_acc = Knob(kx0,           ky0,           RADIUS, 100, 1000, 500, "Aceleración", step=5)
knob_pers= Knob(kx0+gapx,      ky0,           RADIUS, 10,  300,  150, "Persistencia", step=1)
knob_vx  = Knob(kx0,           ky0+gapy,      RADIUS, -100, 100, 0, "Volt X", step=1, default=0)
knob_vy  = Knob(kx0+gapx,      ky0+gapy,      RADIUS, -100, 100, 0, "Volt Y", step=1, default=0)
kxs = LEFT_ZONE.x + 50
kys = ky0 + 2*gapy + 4
knob_fx  = Knob(kxs,           kys,           RADIUS, 1, 5, 1, "fX Hz", step=1)
knob_phix= Knob(kxs+gapx,      kys,           RADIUS, 0, 360, 0, "faseX °", step=5)
knob_fy  = Knob(kxs+2*gapx,    kys,           RADIUS, 1, 5, 1, "fY Hz", step=1)
knob_phiy= Knob(kxs+3*gapx,    kys,           RADIUS, 0, 360, 0, "faseY °", step=5)

knobs.extend([knob_acc, knob_pers, knob_vx, knob_vy, knob_fx, knob_phix, knob_fy, knob_phiy])

# Botones del centro
buttons: List[Button] = []

def toggle_modo():
    global modo_sinusoidal
    modo_sinusoidal = not modo_sinusoidal

btn_modo = Button(pygame.Rect(CENTER_ZONE.centerx-45, CENTER_ZONE.y+28, 90, 34), "Modo", toggle_modo)
btn_apagar = Button(pygame.Rect(CENTER_ZONE.centerx-54, CENTER_ZONE.y+86, 108, 38),
                    "Apagar", lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)))
buttons.extend([btn_modo, btn_apagar])

# Presets (derecha) en grilla 5x4 ajustada al espacio
preset_buttons: List[Button] = []
cols, rows = 5, 4
gap_x, gap_y = 6, 6
cell_w = (RIGHT_ZONE.width - (cols-1)*gap_x - 20) // cols
cell_h = 26
grid_left  = RIGHT_ZONE.x + 10
grid_top   = RIGHT_ZONE.y + 34

for i, (rat, delt) in enumerate(PRESET_SPECS):
    cx = i % cols
    cy = i // cols
    r = pygame.Rect(grid_left + cx*(cell_w+gap_x),
                    grid_top  + cy*(cell_h+gap_y),
                    cell_w, cell_h)
    def make_action(rat=rat, delt=delt):
        return lambda: aplicar_preset_en_perillas(rat, delt)
    label = f"{rat} δ={delt}°"
    preset_buttons.append(Button(r, label, make_action(), small=True))

# =========================
# Bucle principal
# =========================
running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        if hasattr(pygame, "WINDOWEVENT") and e.type == pygame.WINDOWEVENT:
            if getattr(e, "event", None) == getattr(pygame, "WINDOWEVENT_CLOSE", None):
                running = False

        for k in knobs:           k.handle_event(e)
        for b in buttons:         b.handle_event(e)
        for pb in preset_buttons: pb.handle_event(e)

    # Lee las perillas
    voltaje_aceleracion = knob_acc.value
    persistencia        = int(knob_pers.value)
    voltaje_horizontal  = knob_vx.value
    voltaje_vertical    = knob_vy.value
    freq_x              = int(knob_fx.value)
    fase_x              = math.radians(knob_phix.value)
    freq_y              = int(knob_fy.value)
    fase_y              = math.radians(knob_phiy.value)

    # Actualiza la trayectoria (persistencia tipo fósforo)
    x, y = obtener_posicion(t)
    px_scr, py_scr = to_rect(x, y, CRT_RECT)
    trayectoria.append((px_scr, py_scr))
    if len(trayectoria) > persistencia:
        trayectoria.pop(0)

    # --- Dibujo ---
    screen.fill((30, 30, 34))

    # Marco exterior
    pygame.draw.rect(screen, METAL, OUTER, border_radius=12)
    pygame.draw.rect(screen, GREY, OUTER, 4, border_radius=12)

    # Pantalla con rejilla
    pygame.draw.rect(screen, BLACK, CRT_RECT, border_radius=8)
    inner = CRT_RECT.inflate(-14, -14)
    pygame.draw.rect(screen, PHOS_BG, inner, border_radius=8)
    grid = inner.inflate(-20, -20)
    for xg in range(grid.left, grid.right, 24):
        pygame.draw.line(screen, PHOS_GRID, (xg, grid.top), (xg, grid.bottom), 1)
    for yg in range(grid.top, grid.bottom, 24):
        pygame.draw.line(screen, PHOS_GRID, (grid.left, yg), (grid.right, yg), 1)

    # Info rápida del modo y parámetros
    mode_text = "MODE: SINUSOIDAL" if modo_sinusoidal else "MODE: MANUAL"
    screen.blit(FONT_M.render(mode_text, True, HILITE), (inner.x + 16, inner.y + 12))
    params = FONT_S.render(
        f"fx={freq_x}Hz  fy={freq_y}Hz  phix={int(math.degrees(fase_x))}°  phiy={int(math.degrees(fase_y))}°",
        True, HILITE)
    screen.blit(params, (inner.x + 16, inner.y + 36))

    # Trazo verde con brillo
    def c(v): return max(0, min(255, v))
    for i, (tx, ty) in enumerate(trayectoria):
        base = max(60, min(255, int((voltaje_aceleracion/1000) * 255)))
        frac = (i+1)/max(1,len(trayectoria))
        col = (int(PHOS_TRACE[0]*frac), c(int(base*frac)), int(90*frac))
        s = pygame.Surface((3,3), pygame.SRCALPHA)
        s.fill((*col, int(200*frac)))
        screen.blit(s, (tx-1, ty-1))
        if i == len(trayectoria)-1:
            draw_beam_on_crt(tx, ty)

    # Diagrama lateral
    draw_tube_outline(screen, DIAG_RECT, y)

    # Panel y rótulos
    draw_panel_chasis()
    screen.blit(FONT_S.render("MANECILLAS", True, TEXT), (LEFT_ZONE.x+10, LEFT_ZONE.y+8))
    screen.blit(FONT_S.render("CONTROLES",  True, TEXT), (CENTER_ZONE.x+10, CENTER_ZONE.y+8))
    screen.blit(FONT_S.render("PRESETS",    True, TEXT), (RIGHT_ZONE.x+10, RIGHT_ZONE.y+8))

    # Subtítulos dentro de manecillas
    screen.blit(FONT_XS.render("GENERAL", True, TEXT), (LEFT_ZONE.x+10, ky0-22))
    screen.blit(FONT_XS.render("MANUAL (X/Y)", True, TEXT), (LEFT_ZONE.x+10, ky0+gapy-22))
    screen.blit(FONT_XS.render("SINUSOIDAL", True, TEXT), (LEFT_ZONE.x+10, kys-22))

    # Controles en pantalla
    for k in knobs:   k.draw(screen)
    for b in buttons: b.draw(screen)
    for pb in preset_buttons: pb.draw(screen)

    pygame.display.flip()
    t += dt
    clock.tick(FPS)

pygame.quit()
sys.exit(0)
