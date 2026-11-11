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
from textura_pared import crear_textura_pared

BASE = Path(__file__).resolve().parent
TAM = 21
TONOS = (
    ('blanco', (1.0, 1.0, 1.0)),
    ('cálido', (1.0, 0.72, 0.43)),
    ('frío', (0.55, 0.77, 1.0)),
    ('verde', (0.55, 1.0, 0.65)),
    ('violeta', (0.85, 0.58, 1.0)),
)


def nuevo():
    mapa, entrada, salida = generar(TAM, TAM)
    return mapa, entrada, salida, 1.0, 1.0, [(1.0, 1.0)]


def dibujar(cubo, texturas, mapa, entrada, salida, x, z, ruta, camara, yaw):
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
                cubo.dibujar(texturas['remate'], t_x=c, t_y=1.93,
                             t_z=f, sx=1.04, sy=0.08, sz=1.04)
    # Bordes oscuros sobre cada prisma para distinguir paredes contiguas.
    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    glColor3f(0.16, 0.16, 0.16)
    glLineWidth(2)
    glBegin(GL_LINES)
    for f, fila in enumerate(mapa):
        for c, pared in enumerate(fila):
            if not pared:
                continue
            izq, der, frente, fondo = c-0.505, c+0.505, f-0.505, f+0.505
            for cx in (izq, der):
                for cz in (frente, fondo):
                    glVertex3f(cx, 0, cz)
                    glVertex3f(cx, 1.9, cz)
            for x1, z1, x2, z2 in ((izq, frente, der, frente),
                                    (der, frente, der, fondo),
                                    (der, fondo, izq, fondo),
                                    (izq, fondo, izq, frente)):
                glVertex3f(x1, 1.905, z1)
                glVertex3f(x2, 1.905, z2)
    glEnd()
    glColor3f(1, 1, 1)
    glEnable(GL_LIGHTING)
    for (f, c), nombre in ((entrada, 'entrada'), (salida, 'salida')):
        cubo.dibujar(texturas[nombre], t_x=c, t_y=0.005, t_z=f,
                     sx=0.72, sy=0.035, sz=0.72)
    if camara == 3:
        # Personaje compuesto únicamente de cubos elementales.
        cubo.dibujar(texturas['personaje'], t_x=x, t_y=0.48, t_z=z,
                     sx=0.35, sy=0.7, sz=0.25)
        cubo.dibujar(texturas['cabeza'], t_x=x, t_y=1.0, t_z=z,
                     sx=0.25, sy=0.25, sz=0.25)
        a = math.radians(yaw)
        cubo.dibujar(texturas['frente'], t_x=x+math.sin(a)*0.15,
                     t_y=0.73, t_z=z-math.cos(a)*0.15,
                     sx=0.10, sy=0.11, sz=0.10)
    if camara == 2:
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
    pygame.display.set_caption('Laberinto 3D | WASD mover, ratón mirar, 1/2/3 cámaras, L tono, I luz, N nuevo')
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)
    glClearColor(0.08, 0.09, 0.12, 1)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, (0.85, 0.85, 0.85, 1))
    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, (1, 1, 1, 1))
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.25, 0.25, 0.25, 1))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 18)
    cubo = Modelo(str(BASE / 'modelos' / 'cubo.obj'))
    texturas = {nombre: cargar_textura(str(BASE / 'texturas' / archivo))
                for nombre, archivo in {'remate': 'marmol.png', 'suelo': 'granito.png',
                                        'entrada': 'verde.png', 'salida': 'rojo.png',
                                        'personaje': 'azul.png', 'cabeza': 'amarillo.png',
                                        'frente': 'naranja.png'}.items()}
    texturas['pared'] = crear_textura_pared()
    mapa, entrada, salida, x, z, ruta = nuevo()
    yaw, pitch, yaw_personaje = 0.0, 0.0, 0.0
    camara, luz_local, tono, terminado = 1, False, 0, False
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    pygame.mouse.get_rel()
    reloj = pygame.time.Clock()
    activo = True
    while activo:
        dt = min(reloj.tick(FPS) / 1000, 0.05)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                activo = False
            elif evento.type == pygame.MOUSEMOTION and camara in (1, 3):
                yaw += evento.rel[0] * 0.16
                limite_inferior, limite_superior = (-70, 70) if camara == 1 else (8, 55)
                pitch = max(limite_inferior, min(limite_superior,
                                                pitch - evento.rel[1] * 0.12))
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    activo = False
                elif evento.key == pygame.K_1:
                    camara = 1
                    pitch = 0.0
                    pygame.event.set_grab(True)
                    pygame.mouse.set_visible(False)
                    pygame.mouse.get_rel()
                elif evento.key == pygame.K_2:
                    camara = 2
                    pygame.event.set_grab(False)
                    pygame.mouse.set_visible(True)
                elif evento.key == pygame.K_3:
                    camara = 3
                    pitch = 20.0
                    pygame.event.set_grab(True)
                    pygame.mouse.set_visible(False)
                    pygame.mouse.get_rel()
                elif evento.key == pygame.K_l:
                    tono = (tono + 1) % len(TONOS)
                elif evento.key == pygame.K_i:
                    luz_local = not luz_local
                elif evento.key == pygame.K_n:
                    mapa, entrada, salida, x, z, ruta = nuevo()
                    yaw, pitch, yaw_personaje, terminado = 0.0, 0.0, 0.0, False
                    pygame.display.set_caption('Laberinto 3D | WASD mover, ratón mirar, 1/2/3 cámaras, L tono, I luz, N nuevo')
        teclas = pygame.key.get_pressed()
        if not terminado:
            yaw += (int(teclas[pygame.K_RIGHT]) - int(teclas[pygame.K_LEFT])) * 110 * dt
            angulo = math.radians(yaw)
            avance = int(teclas[pygame.K_w]) - int(teclas[pygame.K_s])
            lateral = int(teclas[pygame.K_d]) - int(teclas[pygame.K_a])
            norma = math.hypot(avance, lateral)
            if norma:
                dx = (math.sin(angulo)*avance + math.cos(angulo)*lateral) * 2.8*dt/norma
                dz = (-math.cos(angulo)*avance + math.sin(angulo)*lateral) * 2.8*dt/norma
                if transitable(mapa, x+dx, z):
                    x += dx
                if transitable(mapa, x, z+dz):
                    z += dz
                if camara == 3 and (dx or dz):
                    yaw_personaje = math.degrees(math.atan2(dx, -dz))
                if math.hypot(x-ruta[-1][0], z-ruta[-1][1]) >= 0.15:
                    ruta.append((x, z))
            if (int(z+0.5), int(x+0.5)) == salida:
                terminado = True
                pygame.display.set_caption('¡Salida alcanzada! Pulsa N para crear otro laberinto')
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if camara == 2:
            aspecto = SCREEN_WIDTH / SCREEN_HEIGHT
            mitad_y = (TAM+2)/2
            mitad_x = mitad_y * aspecto
            glOrtho(-mitad_x, mitad_x, -mitad_y, mitad_y, 0.1, 100)
        else:
            gluPerspective(FOV, SCREEN_WIDTH/SCREEN_HEIGHT, 0.1, 100)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        if camara == 2:
            centro = (TAM-1)/2
            gluLookAt(centro, 35, centro, centro, 0, centro, 0, 0, -1)
        elif camara == 3:
            angulo = math.radians(yaw)
            distancia = 0.45
            for paso in range(5, 25):
                intento = paso * 0.1
                horizontal = math.cos(math.radians(pitch)) * intento
                cx = x - math.sin(angulo) * horizontal
                cz = z + math.cos(angulo) * horizontal
                if not transitable(mapa, cx, cz, radio=0.08):
                    break
                distancia = intento
            horizontal = math.cos(math.radians(pitch)) * distancia
            cx = x - math.sin(angulo) * horizontal
            cz = z + math.cos(angulo) * horizontal
            cy = 1.65 + math.sin(math.radians(pitch)) * distancia
            gluLookAt(cx, cy, cz, x, 0.75, z, 0, 1, 0)
        else:
            angulo = math.radians(yaw)
            inclinacion = math.radians(pitch)
            gluLookAt(x, 0.85, z,
                      x+math.sin(angulo)*math.cos(inclinacion),
                      0.85+math.sin(inclinacion),
                      z-math.cos(angulo)*math.cos(inclinacion), 0, 1, 0)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        color = TONOS[tono][1]
        ambiente = 0.22 if luz_local else 0.38
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (*(v * ambiente for v in color), 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0, 0, 0, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (*(v * 0.9 for v in color), 1))
        glLightfv(GL_LIGHT0, GL_POSITION, (x, 0.85, z, 1) if luz_local else (0.4, 1, 0.5, 0))
        glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.22 if luz_local else 0)
        glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0.045 if luz_local else 0)
        if luz_local:
            glDisable(GL_LIGHT1)
        else:
            glEnable(GL_LIGHT1)
            glLightfv(GL_LIGHT1, GL_AMBIENT, (0, 0, 0, 1))
            glLightfv(GL_LIGHT1, GL_DIFFUSE, (*(v * 0.45 for v in color), 1))
            glLightfv(GL_LIGHT1, GL_POSITION, (-0.6, 0.8, -0.4, 0))
        dibujar(cubo, texturas, mapa, entrada, salida, x, z, ruta, camara, yaw_personaje)
        pygame.display.flip()
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    pygame.quit()


if __name__ == '__main__':
    main()
