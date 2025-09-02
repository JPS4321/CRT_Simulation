import pygame
import math
import sys
import threading
import tkinter as tk

# -----------------------------
# CONFIGURACIÓN PYGAME
# -----------------------------
WIDTH, HEIGHT = 800, 600
FPS = 60
BLACK = (0, 0, 0)

pygame.init()
pantalla = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulación de CRT con Figuras de Lissajous")
clock = pygame.time.Clock()

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
running = True

# -----------------------------
# CORRECCIONES OFFSETS + FLIPS
# -----------------------------
PRESET_OFFSETS = {
    "1:1": (0,   0),
    "1:2": (0,  90),   # Y adelantado 90° → "U"
    "1:3": (180, 0),   # X invertido → corrige espejo
    "2:3": (90,  0),   # X adelantado 90°
}

FLIPS = {
    "1:1": (1,  1),
    "1:2": (1, -1),   # invertir Y
    "1:3": (1,  1),
    "2:3": (-1, 1),   # invertir X
}

# -----------------------------
# FUNCIONES DE SIMULACIÓN
# -----------------------------
def obtener_posicion(tiempo):
    """ Calcula la posición del haz en el CRT """
    global modo_sinusoidal
    if modo_sinusoidal:
        x = math.sin(2 * math.pi * freq_x * tiempo + fase_x)
        y = math.sin(2 * math.pi * freq_y * tiempo + fase_y)

        # aplicar flip según relación actual
        key = f"{int(freq_x)}:{int(freq_y)}"
        if key in FLIPS:
            fx, fy = FLIPS[key]
            x *= fx
            y *= fy
    else:
        x = voltaje_horizontal / 100.0
        y = voltaje_vertical / 100.0
    return x, y

def transformar_a_pantalla(x, y):
    """ Escala coordenadas normalizadas (-1..1) a la pantalla """
    px = int(WIDTH / 2 + x * (WIDTH / 2 - 50))
    py = int(HEIGHT / 2 - y * (HEIGHT / 2 - 50))
    return px, py

# -----------------------------
# BUCLE PRINCIPAL PYGAME
# -----------------------------
def ejecutar_pygame():
    global t, trayectoria, running
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    toggle_modo()

        # Calcular posición
        x, y = obtener_posicion(t)
        px, py = transformar_a_pantalla(x, y)

        trayectoria.append((px, py))
        if len(trayectoria) > persistencia:
            trayectoria.pop(0)

        pantalla.fill(BLACK)

        # Brillo depende del voltaje de aceleración
        for i, (tx, ty) in enumerate(trayectoria):
            intensidad = int((voltaje_aceleracion / 1000) * 255 * (i + 1) / len(trayectoria))
            intensidad = max(0, min(255, intensidad))  # limitar entre 0-255
            pygame.draw.circle(pantalla, (0, intensidad, 0), (tx, ty), 2)

        pygame.display.flip()
        t += dt
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

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
    """ Actualiza variables según sliders """
    global voltaje_aceleracion, voltaje_horizontal, voltaje_vertical
    global freq_x, fase_x, freq_y, fase_y, persistencia

    voltaje_aceleracion = aceleracion_slider.get()
    voltaje_horizontal = horizontal_slider.get()
    voltaje_vertical = vertical_slider.get()

    freq_x = freqx_slider.get()
    fase_x = math.radians(fasex_slider.get())
    freq_y = freqy_slider.get()
    fase_y = math.radians(fasey_slider.get())

    persistencia = persistencia_slider.get()
    root.after(50, actualizar_vars)

def salir():
    """Termina la simulación y cierra todo"""
    global running
    running = False
    root.destroy()


# -----------------------------
# CREAR INTERFAZ TKINTER
# -----------------------------
root = tk.Tk()
root.title("Controles CRT")

modo_label = tk.Label(root, text="Modo: Manual", font=("Arial", 12))
modo_label.pack()

tk.Button(root, text="Cambiar modo (Manual/Sinusoidal)", command=toggle_modo).pack()
tk.Button(root, text="Salir", command=salir, bg="red", fg="white").pack(pady=10)

# Siempre visible
aceleracion_slider = tk.Scale(root, from_=100, to=1000, orient="horizontal", label="Voltaje Aceleración (Brillo)")
aceleracion_slider.set(500)
aceleracion_slider.pack()

# Solo en modo Manual
horizontal_slider = tk.Scale(root, from_=-100, to=100, orient="horizontal", label="Voltaje Horizontal")
horizontal_slider.pack()

vertical_slider = tk.Scale(root, from_=-100, to=100, orient="horizontal", label="Voltaje Vertical")
vertical_slider.pack()

# Siempre visibles (modo sinusoidal)
freqx_slider = tk.Scale(root, from_=1, to=5, orient="horizontal", label="Frecuencia X (Hz)")
freqx_slider.set(1)
freqx_slider.pack()

fasex_slider = tk.Scale(root, from_=0, to=360, orient="horizontal", label="Fase X (grados)")
fasex_slider.set(0)
fasex_slider.pack()

freqy_slider = tk.Scale(root, from_=1, to=5, orient="horizontal", label="Frecuencia Y (Hz)")
freqy_slider.set(1)
freqy_slider.pack()

fasey_slider = tk.Scale(root, from_=0, to=360, orient="horizontal", label="Fase Y (grados)")
fasey_slider.set(0)
fasey_slider.pack()

persistencia_slider = tk.Scale(root, from_=10, to=120, orient="horizontal", label="Persistencia")
persistencia_slider.set(30)
persistencia_slider.pack()

# -----------------------------
# PRESETS DE FIGURAS
# -----------------------------
presets = {
    # Relación 1:1
    "1:1 δ=0°":   (1, 1, 0),
    "1:1 δ=45°":  (1, 1, 45),
    "1:1 δ=90°":  (1, 1, 90),
    "1:1 δ=135°": (1, 1, 135),
    "1:1 δ=180°": (1, 1, 180),

    # Relación 1:2
    "1:2 δ=0°":   (1, 2, 0),
    "1:2 δ=45°":  (1, 2, 45),
    "1:2 δ=90°":  (1, 2, 90),
    "1:2 δ=135°": (1, 2, 135),
    "1:2 δ=180°": (1, 2, 180),

    # Relación 1:3
    "1:3 δ=0°":   (1, 3, 0),
    "1:3 δ=45°":  (1, 3, 45),
    "1:3 δ=90°":  (1, 3, 90),
    "1:3 δ=135°": (1, 3, 135),
    "1:3 δ=180°": (1, 3, 180),

    # Relación 2:3
    "2:3 δ=0°":   (2, 3, 0),
    "2:3 δ=45°":  (2, 3, 45),
    "2:3 δ=90°":  (2, 3, 90),
    "2:3 δ=135°": (2, 3, 135),
    "2:3 δ=180°": (2, 3, 180),
}

def aplicar_preset(selection):
    """Mueve sliders según el preset elegido con offsets por fila."""
    ratio, delta_tag = selection.split()[:2]   # ej. "1:2", "δ=90°"
    fx, fy = map(int, ratio.split(":"))
    delta = int(delta_tag.split("=")[1].replace("°", ""))

    base_x, base_y = PRESET_OFFSETS[ratio]

    freqx_slider.set(fx)
    freqy_slider.set(fy)
    fasex_slider.set(base_x)
    fasey_slider.set(base_y + delta)

# Menú desplegable de presets
preset_var = tk.StringVar(root)
preset_var.set("Seleccionar preset")
preset_menu = tk.OptionMenu(root, preset_var, *presets.keys(), command=aplicar_preset)
preset_menu.pack()

# -----------------------------
# INICIO DE LA APP
# -----------------------------
root.after(100, actualizar_vars)

# Ejecutar pygame en un hilo aparte
thread = threading.Thread(target=ejecutar_pygame, daemon=True)
thread.start()

root.mainloop()
running = False
