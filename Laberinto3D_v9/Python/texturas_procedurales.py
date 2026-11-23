"""Texturas generadas con Pygame/NumPy (no necesitan archivos externos).

* pared / musgo: mismo muro de ladrillo; `musgo` añade una capa de musgo que crece desde la base.
  Ambas miden 256 x 486 px = 1.0 x 1.9 unidades de mundo (ALTURA_PARED), es decir, 256 px por unidad
  en horizontal y en vertical: el ladrillo no se deforma. Son periódicas en horizontal, de modo que
  los muros largos no muestran costuras cada celda.
* puerta cerrada / abierta: 240 x 475 px (1.0 x ALTURA_PARED+ALTURA_REMATE).
* esfera: damero dorado para que se aprecie la rotación.
"""
import math
import random

import numpy as np
import pygame

from configuracion import ALTURA_PARED, ALTURA_REMATE
from texturas import bytes_superficie, textura_desde_superficie

ANCHO_PARED = 256
ALTO_PARED = round(ANCHO_PARED * ALTURA_PARED)          # 486
FILAS = 8
ANCHO_LADRILLO = 128
MORTERO = (55, 59, 62)


def _bytes_a_array(superficie):
    datos = bytes_superficie(superficie, 'RGB', False)
    return np.frombuffer(datos, dtype=np.uint8).reshape(superficie.get_height(), superficie.get_width(), 3)


def _array_a_superficie(arr):
    arr = np.ascontiguousarray(arr, dtype=np.uint8)
    h, w = arr.shape[:2]
    return pygame.image.frombuffer(arr.tobytes(), (w, h), 'RGB')


def _superficie_ladrillos():
    """Muro de ladrillo de 8 filas, periódico en horizontal, con las variaciones de color de la v5."""
    ancho, alto = ANCHO_PARED, ALTO_PARED
    s = pygame.Surface((ancho, alto))
    s.fill(MORTERO)
    azar = random.Random(31415)
    junta = 4
    for fila in range(FILAS):
        y0, y1 = round(fila * alto / FILAS), round((fila + 1) * alto / FILAS)
        desplazamiento = ANCHO_LADRILLO // 2 if fila % 2 else 0
        for i in range(ancho // ANCHO_LADRILLO):
            variacion = azar.randrange(-13, 14)
            base = (145 + variacion, 139 + variacion, 125 + variacion)
            for x in (i * ANCHO_LADRILLO + desplazamiento, i * ANCHO_LADRILLO + desplazamiento - ancho):
                pygame.draw.rect(s, base, (x + junta, y0 + junta, ANCHO_LADRILLO - junta, y1 - y0 - junta))
                pygame.draw.line(s, (179, 171, 151), (x + junta, y0 + junta),
                                 (x + ANCHO_LADRILLO - 1, y0 + junta), 2)          # Luz superior.
                pygame.draw.line(s, (99, 99, 93), (x + junta, y1 - 2),
                                 (x + ANCHO_LADRILLO - 1, y1 - 2), 2)              # Sombra inferior.
    for _ in range(12000):                    # Grano discreto sobre los ladrillos (no sobre el mortero).
        px, py = azar.randrange(ancho), azar.randrange(alto)
        color = s.get_at((px, py))
        if sum(color[:3]) > 250:
            d = azar.randrange(-13, 14)
            s.set_at((px, py), tuple(max(0, min(255, color[k] + d)) for k in range(3)))
    return s


def _ruido_periodico(rng, alto, ancho, celdas_y, celdas_x):
    """Ruido de valores suavizado, periódico en ambos ejes. Devuelve (alto, ancho) en [0, 1]."""
    rejilla = rng.random((celdas_y, celdas_x))
    ys = np.linspace(0, celdas_y, alto, endpoint=False)
    xs = np.linspace(0, celdas_x, ancho, endpoint=False)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    fy, fx = ys - y0, xs - x0
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    y1, x1 = (y0 + 1) % celdas_y, (x0 + 1) % celdas_x
    a = rejilla[np.ix_(y0, x0)]
    b = rejilla[np.ix_(y0, x1)]
    c = rejilla[np.ix_(y1, x0)]
    d = rejilla[np.ix_(y1, x1)]
    fx_, fy_ = fx[None, :], fy[:, None]
    return (a * (1 - fx_) + b * fx_) * (1 - fy_) + (c * (1 - fx_) + d * fx_) * fy_


def crear_superficie_pared():
    return _superficie_ladrillos()


def crear_superficie_musgo():
    """Mismos ladrillos que la pared + musgo desde la base, con manchas más altas en las juntas."""
    base = _bytes_a_array(_superficie_ladrillos()).astype(np.float64)
    alto, ancho = base.shape[:2]
    rng = np.random.default_rng(2718)
    ruido = (0.50 * _ruido_periodico(rng, alto, ancho, 6, 4) +
             0.30 * _ruido_periodico(rng, alto, ancho, 14, 8) +
             0.20 * _ruido_periodico(rng, alto, ancho, 30, 16))
    altura = 1.0 - np.arange(alto)[:, None] / (alto - 1)          # 0 abajo (suelo), 1 arriba (remate).
    sesgo = np.clip(1.0 - altura / 0.62, 0.0, 1.0) ** 0.9           # Musgo fuerte en la base.
    cobertura = ruido * 0.70 + sesgo * 0.85 - 0.30
    alfa = np.clip((cobertura - 0.20) / 0.20, 0.0, 1.0)[..., None]  # Borde suave.
    tono = _ruido_periodico(rng, alto, ancho, 20, 10)[..., None]
    musgo = np.array([52.0, 84.0, 34.0]) + tono * np.array([40.0, 52.0, 22.0])
    # El musgo oscurece un poco lo que cubre y deja asomar el relieve de los ladrillos.
    relieve = (base.mean(axis=2, keepdims=True) - 120.0) * 0.35
    resultado = base * (1 - alfa) + (musgo + relieve) * alfa
    return _array_a_superficie(np.clip(resultado, 0, 255))


def crear_textura_pared():
    return textura_desde_superficie(crear_superficie_pared(), mipmaps=True)


def crear_textura_musgo():
    return textura_desde_superficie(crear_superficie_musgo(), mipmaps=True)


# --------------------------------------------------------------------------------------
# Puerta
# --------------------------------------------------------------------------------------
ANCHO_PUERTA = 240
ALTO_PUERTA = round(ANCHO_PUERTA * (ALTURA_PARED + ALTURA_REMATE))     # 475


def _texto_centrado(s, texto, tam, color, y):
    fuente = pygame.font.Font(None, tam)
    img = fuente.render(texto, True, color)
    s.blit(img, ((s.get_width() - img.get_width()) // 2, y))


def crear_superficie_puerta(abierta):
    """Puerta reconocible: chapa con travesaños, remaches, candado + «CERRADA» (rojo) o flechas + «ABIERTA» (verde)."""
    w, h = ANCHO_PUERTA, ALTO_PUERTA
    s = pygame.Surface((w, h))
    chapa = (28, 110, 62) if abierta else (58, 64, 74)
    luz = (60, 190, 100) if abierta else (96, 104, 118)
    sombra = (14, 60, 34) if abierta else (30, 33, 40)
    s.fill(chapa)
    for x in range(0, w, 30):                                   # Tablones verticales.
        pygame.draw.line(s, sombra, (x, 0), (x, h), 2)
        pygame.draw.line(s, luz, (x + 2, 0), (x + 2, h), 1)
    # Travesaños con franjas diagonales amarillo/negro (aviso).
    for y0 in (int(h * 0.18), int(h * 0.80)):
        banda = pygame.Rect(0, y0, w, 34)
        pygame.draw.rect(s, (18, 18, 20), banda)
        for x in range(-40, w + 40, 28):
            pygame.draw.polygon(s, (245, 200, 30), [(x, y0 + 34), (x + 14, y0 + 34), (x + 34, y0), (x + 20, y0)])
        pygame.draw.rect(s, (18, 18, 20), banda, 3)
    rojo, blanco = (230, 60, 50), (240, 240, 235)
    _texto_centrado(s, 'SALIDA', 52, blanco, int(h * 0.075))
    cx, cy = w // 2, int(h * 0.50)
    if abierta:
        for k in range(3):                                      # Flechas hacia arriba (puerta que se abre).
            y = cy - 30 + k * 34
            pygame.draw.polygon(s, (190, 255, 205), [(cx - 38, y + 22), (cx, y - 10), (cx + 38, y + 22),
                                                     (cx + 38, y + 38), (cx, y + 8), (cx - 38, y + 38)])
        _texto_centrado(s, 'ABIERTA', 44, (200, 255, 215), int(h * 0.893))
    else:
        pygame.draw.arc(s, (210, 214, 222), (cx - 34, cy - 74, 68, 88), 0, math.pi, 10)   # Arco del candado.
        pygame.draw.line(s, (210, 214, 222), (cx - 34, cy - 30), (cx - 34, cy - 8), 10)
        pygame.draw.line(s, (210, 214, 222), (cx + 34, cy - 30), (cx + 34, cy - 8), 10)
        pygame.draw.rect(s, (236, 186, 40), (cx - 52, cy - 12, 104, 84), border_radius=10)
        pygame.draw.rect(s, (120, 84, 10), (cx - 52, cy - 12, 104, 84), 4, border_radius=10)
        pygame.draw.circle(s, (40, 28, 6), (cx, cy + 24), 11)
        pygame.draw.polygon(s, (40, 28, 6), [(cx - 6, cy + 28), (cx + 6, cy + 28), (cx + 10, cy + 56), (cx - 10, cy + 56)])
        _texto_centrado(s, 'CERRADA', 44, rojo, int(h * 0.893))
    for x in (12, w - 12):                                      # Remaches.
        for y in range(40, h, 56):
            pygame.draw.circle(s, sombra, (x + 1, y + 1), 5)
            pygame.draw.circle(s, luz, (x, y), 5)
    pygame.draw.rect(s, sombra, (0, 0, w, h), 6)                # Marco.
    pygame.draw.rect(s, luz, (3, 3, w - 6, h - 6), 2)
    return s


def crear_textura_puerta(abierta):
    return textura_desde_superficie(crear_superficie_puerta(abierta), mipmaps=True, repetir=False)


# --------------------------------------------------------------------------------------
# Esfera coleccionable
# --------------------------------------------------------------------------------------
def crear_superficie_esfera():
    w, h = 128, 64
    s = pygame.Surface((w, h))
    oro, ambar = (255, 214, 64), (222, 132, 14)
    for fila in range(4):
        for col in range(8):
            pygame.draw.rect(s, oro if (fila + col) % 2 == 0 else ambar,
                             (col * 16, fila * 16, 16, 16))
    for x in range(0, w, 16):
        pygame.draw.line(s, (150, 80, 0), (x, 0), (x, h), 1)
    for y in range(0, h, 16):
        pygame.draw.line(s, (150, 80, 0), (0, y), (w, y), 1)
    return s


def crear_textura_esfera():
    return textura_desde_superficie(crear_superficie_esfera(), mipmaps=True)
