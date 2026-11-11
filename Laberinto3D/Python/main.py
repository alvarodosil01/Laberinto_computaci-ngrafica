"""Laberinto 3D basado en el ejercicio del pórtico (Pygame y OpenGL)."""
import math
from pathlib import Path

import pygame
from pygame.locals import DOUBLEBUF, OPENGL
from OpenGL.GL import *
from OpenGL.GLU import *

from configuracion import SCREEN_WIDTH, SCREEN_HEIGHT, FOV, FPS
from laberinto import generar, transitable
from modelo import Modelo
from texturas import cargar_textura

BASE = Path(__file__).resolve().parent
TAM = 21


def nuevo():
    mapa, entrada, salida = generar(TAM, TAM)
    return mapa, entrada, salida, 1.0, 1.0, [(1.0, 1.0)]


def dibujar(cubo, texturas, mapa, entrada, salida, x, z, ruta, cenital):
    # Repite la textura del suelo por celda, en lugar de estirarla por todo el mapa.
    glMatrixMode(GL_TEXTURE)
    glPushMatrix()
    glLoadIdentity()
    glScalef(TAM, TAM, 1)
    glMatrixMode(GL_MODELVIEW)
    cubo.dibujar(texturas['suelo'], t_x=(TAM-1)/2, t_y=-0.12,
                 t_z=(TAM-1)/2, sx=TAM, sy=0.2, sz=TAM)
    glMatrixMode(GL_TEXTURE)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    for f, fila in enumerate(mapa):
        for c, pared in enumerate(fila):
            if pared:
                cubo.dibujar(texturas['pared'], t_x=c, t_y=0.95,
                             t_z=f, sx=1, sy=1.9, sz=1)
    for (f, c), nombre in ((entrada, 'entrada'), (salida, 'salida')):
        cubo.dibujar(texturas[nombre], t_x=c, t_y=0.005, t_z=f,
                     sx=0.72, sy=0.035, sz=0.72)
    if cenital:
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glColor3f(1, 0.8, 0.1)
        glLineWidth(3)
        glBegin(GL_LINE_STRIP)
        for px, pz in ruta:
            glVertex3f(px, 0.06, pz)
        glEnd()
        glColor3f(0.1, 0.8, 1)
        glPointSize(9)
        glBegin(GL_POINTS)
        glVertex3f(x, 0.07, z)
        glEnd()
        glColor3f(1, 1, 1)


def main():
    pygame.init()
    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption('Laberinto 3D | WASD mover, flechas girar, 1/2 cámaras, L luz, N nuevo')
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)
    glClearColor(0.08, 0.09, 0.12, 1)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.25, 0.25, 0.25, 1))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 18)
    cubo = Modelo(str(BASE / 'modelos' / 'cubo.obj'))
    texturas = {nombre: cargar_textura(str(BASE / 'texturas' / archivo))
                for nombre, archivo in {'pared': 'arenisca.png', 'suelo': 'granito.png',
                                        'entrada': 'verde.png', 'salida': 'rojo.png'}.items()}
    mapa, entrada, salida, x, z, ruta = nuevo()
    yaw, cenital, luz_local, terminado = 0.0, False, False, False
    reloj = pygame.time.Clock()
    activo = True
    while activo:
        dt = min(reloj.tick(FPS) / 1000, 0.05)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                activo = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    activo = False
                elif evento.key == pygame.K_1:
                    cenital = False
                elif evento.key == pygame.K_2:
                    cenital = True
                elif evento.key == pygame.K_l:
                    luz_local = not luz_local
                elif evento.key == pygame.K_n:
                    mapa, entrada, salida, x, z, ruta = nuevo()
                    yaw, terminado = 0.0, False
                    pygame.display.set_caption('Laberinto 3D | WASD mover, flechas girar, 1/2 cámaras, L luz, N nuevo')
        teclas = pygame.key.get_pressed()
        if not terminado:
            yaw += (int(teclas[pygame.K_RIGHT]) - int(teclas[pygame.K_LEFT])) * 110 * dt
            angulo = math.radians(yaw)
            avance = int(teclas[pygame.K_w] or teclas[pygame.K_UP]) - int(teclas[pygame.K_s])
            lateral = int(teclas[pygame.K_d]) - int(teclas[pygame.K_a])
            norma = math.hypot(avance, lateral)
            if norma:
                dx = (math.sin(angulo)*avance + math.cos(angulo)*lateral) * 2.8*dt/norma
                dz = (-math.cos(angulo)*avance + math.sin(angulo)*lateral) * 2.8*dt/norma
                if transitable(mapa, x+dx, z):
                    x += dx
                if transitable(mapa, x, z+dz):
                    z += dz
                if math.hypot(x-ruta[-1][0], z-ruta[-1][1]) >= 0.15:
                    ruta.append((x, z))
            if (int(z+0.5), int(x+0.5)) == salida:
                terminado = True
                pygame.display.set_caption('¡Salida alcanzada! Pulsa N para crear otro laberinto')
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if cenital:
            aspecto = SCREEN_WIDTH / SCREEN_HEIGHT
            mitad_y = (TAM+2)/2
            mitad_x = mitad_y * aspecto
            glOrtho(-mitad_x, mitad_x, -mitad_y, mitad_y, 0.1, 100)
        else:
            gluPerspective(FOV, SCREEN_WIDTH/SCREEN_HEIGHT, 0.1, 100)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        if cenital:
            centro = (TAM-1)/2
            gluLookAt(centro, 35, centro, centro, 0, centro, 0, 0, -1)
        else:
            angulo = math.radians(yaw)
            gluLookAt(x, 0.85, z, x+math.sin(angulo), 0.85,
                      z-math.cos(angulo), 0, 1, 0)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.07, 0.07, 0.07, 1) if luz_local else (0.28, 0.28, 0.28, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.85, 0.85, 0.82, 1))
        glLightfv(GL_LIGHT0, GL_POSITION, (x, 0.85, z, 1) if luz_local else (0.4, 1, 0.5, 0))
        glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.22 if luz_local else 0)
        glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0.045 if luz_local else 0)
        dibujar(cubo, texturas, mapa, entrada, salida, x, z, ruta, cenital)
        pygame.display.flip()
    pygame.quit()


if __name__ == '__main__':
    main()
