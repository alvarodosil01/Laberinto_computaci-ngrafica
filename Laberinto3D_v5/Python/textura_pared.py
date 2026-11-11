"""Textura de bloques creada con Pygame; no requiere modelos externos."""
import random

import pygame
from OpenGL.GL import (GL_LINEAR, GL_REPEAT, GL_RGB, GL_TEXTURE_2D,
                       GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER,
                       GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_UNPACK_ALIGNMENT,
                       GL_UNSIGNED_BYTE, glBindTexture, glGenTextures,
                       glPixelStorei, glTexImage2D, glTexParameteri)


def crear_textura_pared():
    lado = 256
    superficie = pygame.Surface((lado, lado))
    superficie.fill((55, 59, 62))  # Mortero oscuro.
    azar = random.Random(31415)
    alto_bloque = 64
    ancho_bloque = 128
    junta = 5
    for fila in range(4):
        desplazamiento = -64 if fila % 2 else 0
        for columna in range(-1, 3):
            x = columna * ancho_bloque + desplazamiento
            y = fila * alto_bloque
            variacion = azar.randrange(-13, 14)
            base = (145 + variacion, 139 + variacion, 125 + variacion)
            pygame.draw.rect(superficie, base,
                             (x + junta, y + junta, ancho_bloque - junta, alto_bloque - junta))
            pygame.draw.line(superficie, (179, 171, 151),
                             (x + junta, y + junta),
                             (x + ancho_bloque - 1, y + junta), 2)
            pygame.draw.line(superficie, (99, 99, 93),
                             (x + junta, y + alto_bloque - 2),
                             (x + ancho_bloque - 1, y + alto_bloque - 2), 2)
    # Grano discreto para que el patrón no resulte plano.
    for _ in range(6000):
        px, py = azar.randrange(lado), azar.randrange(lado)
        color = superficie.get_at((px, py))
        if sum(color[:3]) > 250:
            delta = azar.randrange(-13, 14)
            superficie.set_at((px, py), tuple(max(0, min(255, color[i] + delta))
                                                 for i in range(3)))
    datos = pygame.image.tostring(superficie, 'RGB', 1)
    textura = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, textura)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, lado, lado, 0,
                 GL_RGB, GL_UNSIGNED_BYTE, datos)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return textura
