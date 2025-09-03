import pygame
import math
import sys
import threading
import tkinter as tk

# -----------------------------
# CONFIGURACIÓN PYGAME
# -----------------------------
WIDTH, HEIGHT = 1000, 620
FPS = 60
BLACK = (0, 0, 0)
GREY  = (50, 50, 50)
WHITE = (240, 240, 240)

pygame.init()
pantalla = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulación de CRT (Vista Lateral)")
clock = pygame.time.Clock()
font_small = pygame.font.SysFont("arial", 14)
font_title = pygame.font.SysFont("arial", 20, bold=True)

# Columna izquierda: centrado vertical
LEFT_COL_X = 20
LEFT_COL_W = 380
LATERAL_H = 220
LATERAL_RECT = pygame.Rect(LEFT_COL_X, (HEIGHT - LATERAL_H) // 2, LEFT_COL_W, LATERAL_H)

# Pantalla frontal a la derecha
SCREEN_RECT = pygame.Rect(430, 40, 540, 540)

# -----------------------------
# VARIABLES DE SIMULACIÓN
# -----------------------------
voltaje_aceleracion = 500
voltaje_vertical = 0
voltaje_horizontal = 0

modo_sinusoidal = False
freq_x = 1.0
freq_y = 1.0
fase_x = 0.0
fase_y = 0.0

persistencia = 150
trayectoria = []

t = 0
dt = 1 / FPS

# Evento de parada compartido entre hilos 
stop_evt = threading.Event()
after_id = None 

# -----------------------------
# CORRECCIONES OFFSETS + FLIPS
# -----------------------------
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

# -----------------------------
# FUNCIONES DE SIMULACIÓN
# -----------------------------
def obtener_posicion(tiempo):
    """Posición normalizada del haz (x,y) en [-1,1]."""
    if modo_sinusoidal:
        x = math.sin(2 * math.pi * freq_x * tiempo + fase_x)
        y = math.sin(2 * math.pi * freq_y * tiempo + fase_y)
        key = f"{int(freq_x)}:{int(freq_y)}"
        if key in FLIPS:
            fx, fy = FLIPS[key]
            x *= fx; y *= fy
    else:
        x = max(-1, min(1, voltaje_horizontal / 100.0))
        y = max(-1, min(1, voltaje_vertical   / 100.0))
    return x, y

def transformar_a_rect(x, y, rect):
    """Escala (-1..1) al rect destino (con margen)."""
    margin = 20
    hw = (rect.width  - 2*margin) / 2
    hh = (rect.height - 2*margin) / 2
    px = int(rect.centerx + x * hw)
    py = int(rect.centery - y * hh)
    return px, py

# -----------------------------
# DIBUJO DEL TUBO (vista lateral) + haz
# -----------------------------
def draw_tube_outline(surface, rect):
    pygame.draw.rect(surface, GREY, rect, 1)
    surface.blit(font_title.render("VISTA LATERAL", True, WHITE), (rect.centerx - 80, rect.y - 22))

    x0, y0, w, h = rect
    cx, cy = rect.center
    left  = x0 + 35
    right = x0 + w - 35
    midy  = cy

    # Cañón
    gun_len = 80
    pygame.draw.rect(surface, WHITE, (left-20, midy-15, gun_len, 30), 2)

    # Ánodos
    ax = left + 10
    for i in range(3):
        pygame.draw.rect(surface, WHITE, (ax + i*20, midy-8, 12, 16), 2)

    # Placas de deflexión vertical
    plates_x = left + gun_len + 20
    pygame.draw.rect(surface, WHITE, (plates_x, midy-35, 35, 12), 2)
    pygame.draw.rect(surface, WHITE, (plates_x, midy+23, 35, 12), 2)
    surface.blit(font_small.render("Vert. defl. plates", True, WHITE), (plates_x-5, midy-55))

    # Cono
    neck_x = plates_x + 55
    cone_top    = (neck_x, midy-25)
    cone_bottom = (neck_x, midy+25)
    cone_tip    = (right-25, midy)
    pygame.draw.polygon(surface, WHITE, [cone_top, cone_bottom, cone_tip], 2)

    # Pantalla circular
    face_radius = max(18, min(32, (h // 4)))
    screen_center = (right, midy)
    pygame.draw.circle(surface, WHITE, screen_center, face_radius, 2)
    surface.blit(font_small.render("Screen", True, WHITE), (right-15, midy-45))

    # ranura guía 
    slot_half = face_radius
    slot_w = 6
    slot_rect = pygame.Rect(screen_center[0] - face_radius - slot_w,
                            screen_center[1] - slot_half,
                            slot_w, 2*slot_half)
    pygame.draw.rect(surface, GREY, slot_rect, 1)

    return (left-20, midy), screen_center, (neck_x, midy), face_radius

def draw_beam_lateral(surface, rect, y_norm):
    """Haz moviéndose SOLO en Y en la vista lateral, acotado al círculo."""
    gun_base, screen_ctr, neck, R = draw_tube_outline(surface, rect)
    target = (screen_ctr[0] - R, int(screen_ctr[1] - y_norm * R))
    pygame.draw.line(surface, WHITE, gun_base, neck, 2)
    pygame.draw.line(surface, WHITE, neck, target, 2)

# -----------------------------
# BUCLE PRINCIPAL PYGAME
# -----------------------------
def ejecutar_pygame():
    global t, trayectoria

    # Aceptar eventos de cierre en Pygame 2
    WINDOWEVENT = getattr(pygame, "WINDOWEVENT", None)
    WINDOWEVENT_CLOSE = getattr(pygame, "WINDOWEVENT_CLOSE", None)

    while not stop_evt.is_set():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_evt.set()
            elif WINDOWEVENT and event.type == WINDOWEVENT and event.event == WINDOWEVENT_CLOSE:
                # Algunas plataformas emiten WINDOWEVENT_CLOSE en vez de QUIT
                stop_evt.set()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                toggle_modo()

        if stop_evt.is_set():
            break

        # Posición normalizada
        x, y = obtener_posicion(t)

        # Traza sobre la pantalla frontal
        px, py = transformar_a_rect(x, y, SCREEN_RECT)
        trayectoria.append((px, py))
        if len(trayectoria) > persistencia:
            trayectoria.pop(0)

        # ---- DIBUJO ----
        pantalla.fill(BLACK)
        draw_beam_lateral(pantalla, LATERAL_RECT, y)

        # Pantalla (vista frontal)
        pygame.draw.rect(pantalla, GREY, SCREEN_RECT, 2)
        label = font_title.render("PANTALLA (vista frontal)", True, WHITE)
        pantalla.blit(label, (SCREEN_RECT.x, SCREEN_RECT.y - 28))
        pygame.draw.rect(pantalla, WHITE, SCREEN_RECT.inflate(-40, -40), 2)

        # Persistencia
        for i, (tx, ty) in enumerate(trayectoria):
            intensidad = int((voltaje_aceleracion / 1000) * 255 * (i + 1) / max(1, len(trayectoria)))
            intensidad = max(0, min(255, intensidad))
            pygame.draw.circle(pantalla, (0, intensidad, 0), (tx, ty), 2)

        pygame.display.flip()
        t += dt
        clock.tick(FPS)

    # Señaló parar: cierro Pygame y pido a Tk que se mate
    try:
        pygame.display.quit()
        pygame.quit()
    except Exception:
        pass
    try:
        # Destruir Tk desde su propio hilo con after seguro
        if 'root' in globals() and root.winfo_exists():
            root.after(0, safe_destroy_root)
    except Exception:
        pass

# -----------------------------
# INTERFAZ CON TKINTER
# -----------------------------
def toggle_modo():
    """ Cambia entre Manual y Sinusoidal """
    global modo_sinusoidal
    modo_sinusoidal = not modo_sinusoidal
    modo_label.config(text="Modo: " + ("Sinusoidal (Lissajous)" if modo_sinusoidal else "Manual"))
    if modo_sinusoidal:
        horizontal_slider.pack_forget()
        vertical_slider.pack_forget()
    else:
        horizontal_slider.pack()
        vertical_slider.pack()

def actualizar_vars():
    """Actualiza sliders mientras no se haya pedido cerrar."""
    global after_id
    if stop_evt.is_set():
        return  # no reprogramar más
    try:
        # leer sliders
        global voltaje_aceleracion, voltaje_horizontal, voltaje_vertical
        global freq_x, fase_x, freq_y, fase_y, persistencia
        voltaje_aceleracion = aceleracion_slider.get()
        voltaje_horizontal  = horizontal_slider.get()
        voltaje_vertical    = vertical_slider.get()
        freq_x = freqx_slider.get()
        fase_x = math.radians(fasex_slider.get())
        freq_y = freqy_slider.get()
        fase_y = math.radians(fasey_slider.get())
        persistencia = persistencia_slider.get()
    finally:
        # reprogamar solo si seguimos activos
        if not stop_evt.is_set():
            after_id = root.after(50, actualizar_vars)

def safe_destroy_root():
    """Destruye Tk de forma segura (evita callbacks pendientes)."""
    global after_id
    try:
        if after_id is not None:
            root.after_cancel(after_id)
            after_id = None
    except Exception:
        pass
    try:
        if root.winfo_exists():
            root.destroy()
    except Exception:
        pass

def salir():
    """Cierre coordinado iniciado desde Tk (botón o 'X')."""
    if stop_evt.is_set():
        return
    stop_evt.set()
    # cancelar after y destruir Tk
    safe_destroy_root()
    # pedir a pygame que cierre su loop si está bloqueado en eventos
    try:
        pygame.event.post(pygame.event.Event(pygame.QUIT))
    except Exception:
        pass

# -----------------------------
# CREAR INTERFAZ TKINTER
# -----------------------------
root = tk.Tk()
root.title("Controles CRT")
root.protocol("WM_DELETE_WINDOW", salir)

modo_label = tk.Label(root, text="Modo: Manual", font=("Arial", 12))
modo_label.pack()

tk.Button(root, text="Cambiar modo (Manual/Sinusoidal)", command=toggle_modo).pack()
tk.Button(root, text="Salir", command=salir, bg="red", fg="white").pack(pady=10)

aceleracion_slider = tk.Scale(root, from_=100, to=1000, orient="horizontal", label="Voltaje Aceleración (Brillo)")
aceleracion_slider.set(500); aceleracion_slider.pack()

horizontal_slider = tk.Scale(root, from_=-100, to=100, orient="horizontal", label="Voltaje Horizontal")
horizontal_slider.pack()

vertical_slider = tk.Scale(root, from_=-100, to=100, orient="horizontal", label="Voltaje Vertical")
vertical_slider.pack()

freqx_slider = tk.Scale(root, from_=1, to=5, orient="horizontal", label="Frecuencia X (Hz)")
freqx_slider.set(1); freqx_slider.pack()

fasex_slider = tk.Scale(root, from_=0, to=360, orient="horizontal", label="Fase X (grados)")
fasex_slider.set(0); fasex_slider.pack()

freqy_slider = tk.Scale(root, from_=1, to=5, orient="horizontal", label="Frecuencia Y (Hz)")
freqy_slider.set(1); freqy_slider.pack()

fasey_slider = tk.Scale(root, from_=0, to=360, orient="horizontal", label="Fase Y (grados)")
fasey_slider.set(0); fasey_slider.pack()

persistencia_slider = tk.Scale(root, from_=10, to=200, orient="horizontal", label="Persistencia")
persistencia_slider.set(150); persistencia_slider.pack()

# -----------------------------
# PRESETS DE FIGURAS
# -----------------------------
presets = {
    "1:1 δ=0°": (1,1,0), "1:1 δ=45°": (1,1,45), "1:1 δ=90°": (1,1,90),
    "1:1 δ=135°": (1,1,135), "1:1 δ=180°": (1,1,180),
    "1:2 δ=0°": (1,2,0), "1:2 δ=45°": (1,2,45), "1:2 δ=90°": (1,2,90),
    "1:2 δ=135°": (1,2,135), "1:2 δ=180°": (1,2,180),
    "1:3 δ=0°": (1,3,0), "1:3 δ=45°": (1,3,45), "1:3 δ=90°": (1,3,90),
    "1:3 δ=135°": (1,3,135), "1:3 δ=180°": (1,3,180),
    "2:3 δ=0°": (2,3,0), "2:3 δ=45°": (2,3,45), "2:3 δ=90°": (2,3,90),
    "2:3 δ=135°": (2,3,135), "2:3 δ=180°": (2,3,180),
}
def aplicar_preset(selection):
    ratio, delta_tag = selection.split()[:2]
    fx, fy = map(int, ratio.split(":"))
    delta = int(delta_tag.split("=")[1].replace("°", ""))
    base_x, base_y = PRESET_OFFSETS[ratio]
    freqx_slider.set(fx); freqy_slider.set(fy)
    fasex_slider.set(base_x); fasey_slider.set(base_y + delta)

preset_var = tk.StringVar(root)
preset_var.set("Seleccionar preset")
preset_menu = tk.OptionMenu(root, preset_var, *presets.keys(), command=aplicar_preset)
preset_menu.pack()

# -----------------------------
# INICIO DE LA APP
# -----------------------------
# arrancar actualización periódica de sliders
after_id = root.after(100, actualizar_vars)

# Ejecutar pygame en un hilo aparte
thread = threading.Thread(target=ejecutar_pygame, daemon=True)
thread.start()

# Bucle principal de Tk
try:
    root.mainloop()
finally:
    # Nota: Si se cierra Tk por cualquier motivo matamos pygame
    stop_evt.set()
    try:
        pygame.event.post(pygame.event.Event(pygame.QUIT))
    except Exception:
        pass
    try:
        thread.join(timeout=1.5)
    except Exception:
        pass
    sys.exit(0)
