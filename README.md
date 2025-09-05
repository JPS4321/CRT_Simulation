# Osciloscopio Retro — Simulación de CRT (Pygame)

Pequeña app que emula un **osciloscopio clásico**: una pantalla verde tipo CRT con rejilla y un **diagrama lateral** del tubo.
Incluye **manecillas (knobs)** para controlar parámetros, un **modo Manual** y un **modo Sinusoidal (Lissajous)**, y un set de **presets** listos para explorar figuras.

---

##  ¿Qué es?

- **Pantalla CRT** con persistencia tipo fósforo y rejilla.
- **Diagrama lateral** del tubo (el haz se mueve en **Y** como en la realidad).
- **Panel de control**:
  - Manecillas para brillo, persistencia, voltajes (manual) y parámetros sinusoidales (fx, fy, faseX, faseY).
  - Botón de **Modo** (Manual/Sinusoidal).
  - Botón **Apagar** (cierra la app).
  - **Presets** de figuras de Lissajous (relaciones 1:1, 1:2, 1:3, 2:3 con distintos desfases).

Todo está hecho con **Pygame** (sin dependencias raras).

---

##  Requisitos

- **Python 3.8+** (recomendado 3.10 o 3.11).
- **Pygame**:

```bash
pip install pygame
```

> En Linux puede que necesites SDL/ALSA/portaudio según tu distro (los paquetes de Pygame suelen traerlo resuelto).
> En macOS con brew: `brew install python` y luego `pip install pygame`.

---

##  Cómo ejecutar

Clona/descarga el proyecto y ejecuta:

```bash
python crt_simulacion.py
```

Si quieres aislar dependencias:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install pygame
python crt_simulacion.py
```

---

##  Controles

**Manecillas (knobs)**  
- **Click izquierdo + arrastrar en círculo:** giro normal (con topes; no “salta” de un extremo a otro).
- **SHIFT + click izquierdo + arrastrar vertical:** ajuste fino.
- **Rueda del mouse:** cambio suave (con **SHIFT** aún más fino).
- **Click derecho:** vuelve al valor por defecto de esa perilla.

**Botones**
- **Modo:** conmuta entre **Manual** y **Sinusoidal**.
- **Apagar:** cierra la aplicación.
- **Presets:** aplica una combinación `fx : fy` y desfase `δ` (actualiza también las manecillas).

**Pantalla**
- Arriba a la izquierda verás el **modo actual** y los **parámetros** activos.

---

##  Modos de operación

- **Manual:** controlas **Volt X** y **Volt Y** (rango -100..100).
- **Sinusoidal (Lissajous):** controlas **fx**, **fy**, **faseX**, **faseY**.
  Los **presets** son combinaciones típicas para explorar patrones rápidamente.

---

##  Presets incluidos

Relaciones: **1:1**, **1:2**, **1:3**, **2:3**  
Desfases: **0°**, **45°**, **90°**, **135°**, **180°**

> Al pulsar un preset se actualiza la simulación **y** se mueven las manecillas correspondientes.

---

##  Rendimiento y trucos

- Si notas la traza muy “pesada”, baja **Persistencia**.
- Para más brillo del haz, sube **Aceleración**.
- Si tu pantalla es pequeña, puedes reducir **`WIDTH`**/**`HEIGHT`**.
  También puedes ajustar **`CRT_RECT`** y las zonas del panel si quieres otra distribución.

---

##  Estructura simple

- `crt_simulacion.py` — todo el proyecto:
  - Layout (carcasa, CRT, diagrama, panel).
  - Simulación del haz: manual vs sinusoidal.
  - UI: clase `Knob` (perillas) y `Button` (botones).
  - Presets y lógica para aplicarlos.
  - Bucle principal de Pygame.

---

##  Personalización rápida

- Colores: ajusta la paleta al inicio (`PHOS_BG`, `PHOS_GRID`, `PHOS_TRACE`).
- Sensibilidad de perillas: mira `ANGLE_MIN`, `ANGLE_MAX`, `SENS_DRAG`, `SENS_WHEEL`, `SENS_WHEEL_FINE`.
- Límites/steps de cada perilla: en la construcción de `Knob(...)`.

---

## Problemas comunes

- **La ventana no cabe en mi pantalla:** baja `WIDTH`/`HEIGHT` y/o la altura de `CRT_RECT`.
- **No puedo instalar pygame:** actualiza `pip` (`python -m pip install -U pip`) y vuelve a intentar.
- **Cierre de ventana:** usa el botón **Apagar** o la **X**; ambos cierran bien.

---

