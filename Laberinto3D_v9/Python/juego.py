"""Aplicación Laberinto 3D v9: ventana, entrada de usuario, renderizado y bucle principal.

Separación de responsabilidades:
    partida.py / objetos.py / exploracion.py / laberinto.py   lógica de juego (sin OpenGL)
    geometria.py / obj.py                                     generación de geometría (sin OpenGL)
    buffers.py / escena.py / modelo.py                        VBO/EBO y ciclo de vida en GPU
    hud.py                                                    interfaz 2D
    camara_tercera.py                                         cámara en tercera persona (lógica)
    juego.py (este archivo)                                   pegamento: entrada + estado GL + orden de dibujo
"""
import math
import time
from pathlib import Path

import numpy as np
import pygame
from pygame.locals import DOUBLEBUF, OPENGL, RESIZABLE
from pygame._sdl2.video import Window
from OpenGL.GL import *

from ambiente_terror import AmbienteTerror
from buffers import MallaGL, RutaGL
from camara_tercera import CamaraTercera
from configuracion import (ANCHO_PASILLO, ESFERA_ESCALA, FAR_PLANE_JUEGO, FOV, FPS, NEAR_PLANE, SCREEN_HEIGHT,
                           SCREEN_WIDTH, DURACION_MENSAJE)
from dificultad import DIFICULTAD_INICIAL, DIFICULTADES, por_clave
from escena import EscenaEstatica
from exploracion import colores_niebla
from geometria import ConstructorMalla
from hud import Interfaz
from modelo import Modelo
from objetos import Puerta
from partida import Partida
from vistas import mirar_a, perspectiva
from texturas import (actualizar_textura_array, cargar_textura, liberar_texturas, textura_desde_array)
from texturas_procedurales import (crear_textura_esfera, crear_textura_musgo, crear_textura_pared,
                                   crear_textura_puerta)

BASE = Path(__file__).resolve().parent
TITULO = ('Laberinto 3D v9 | WASD mover, ratón mirar, 1/2/3 cámaras, F1/F2/F3 dificultad, '
          'L tono, I luz, E linterna, R modo terror, Tab mapa (mantener), H ayuda, F11 pantalla completa, N nuevo, Esc salir')
TONOS = (
    ('blanco', (1.0, 1.0, 1.0)),
    ('cálido', (1.0, 0.72, 0.43)),
    ('frío', (0.55, 0.77, 1.0)),
    ('verde', (0.55, 1.0, 0.65)),
    ('violeta', (0.85, 0.58, 1.0)),
)
ALTURA_NIEBLA = 2.2        # Plano de niebla de la cámara cenital, por encima de los muros (1.98).


class Juego:
    def __init__(self, dificultad=DIFICULTAD_INICIAL, semilla=None, tam_ventana=(SCREEN_WIDTH, SCREEN_HEIGHT),
                 reloj=time.perf_counter):
        self.reloj = reloj
        self.ancho, self.alto = tam_ventana
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.set_mode(tam_ventana, DOUBLEBUF | OPENGL | RESIZABLE)
        self._ventana = Window.from_display_module()
        self.pantalla_completa = False
        self._tam_ventana = tuple(tam_ventana)
        self._pos_ventana = self._ventana.position
        pygame.display.set_caption(TITULO)
        self._configurar_opengl()

        # --- recursos de GPU que viven durante toda la aplicación ---
        carpeta = BASE / 'texturas'
        cargar = lambda nombre, mip=False: cargar_textura(str(carpeta / nombre), mipmaps=mip)
        self.texturas = {
            'remate': cargar('marmol.png', True), 'suelo': cargar('granito.png', True),
            'entrada': cargar('verde.png'), 'salida': cargar('rojo.png'),
            'personaje': cargar('azul.png'), 'cabeza': cargar('amarillo.png'), 'frente': cargar('naranja.png'),
            'pared': crear_textura_pared(), 'musgo': crear_textura_musgo(),
            'puerta_cerrada': crear_textura_puerta(False), 'puerta_abierta': crear_textura_puerta(True),
            'esfera': crear_textura_esfera(), 'portal': self._textura_portal(),
        }
        self.terror = AmbienteTerror(self.texturas, carpeta)      # Modo terror (tecla R); ver ambiente_terror.py.
        self.cubo = Modelo(str(BASE / 'modelos' / 'cubo.obj'))
        self.esfera = Modelo(str(BASE / 'modelos' / 'esfera_lr.obj'))
        self.escena = EscenaEstatica(self.texturas)
        self.hud = Interfaz(self.ancho, self.alto)
        self.ruta_gl = RutaGL()
        self.cam3 = CamaraTercera()
        self.malla_niebla = None
        self.tex_niebla = None
        self._version_niebla = None

        # --- estado de la vista ---
        self.dificultad = por_clave(dificultad) if isinstance(dificultad, str) else dificultad
        self.camara, self.luz_local, self.tono = 1, False, 0
        self.yaw, self.pitch, self.yaw_personaje = 0.0, 0.0, 0.0
        self.mostrar_mapa, self.mostrar_ayuda = False, True
        self.mostrar_hud = True          # Se desactiva en las pruebas gráficas para analizar solo la escena 3D.
        self.usar_cull = True            # Idem: permite comparar con y sin descarte de caras traseras.
        self._mensaje, self._mensaje_hasta = '', 0.0
        self.t_anim = self.reloj()
        self.activo = True
        self.partida = None
        self.nueva_partida(self.dificultad, semilla)
        self._ajustar_tamano()
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        pygame.mouse.get_rel()

    def _ajustar_tamano(self):
        """Actualiza el viewport y la interfaz usando el tamaño actual de la ventana."""
        self.ancho, self.alto = (max(1, int(v)) for v in self._ventana.size)
        glViewport(0, 0, self.ancho, self.alto)
        self.hud.ancho, self.hud.alto = self.ancho, self.alto

    def _alternar_pantalla_completa(self):
        """F11: cambia el modo de la misma ventana, conservando el contexto OpenGL."""
        if self.pantalla_completa:
            self._ventana.set_windowed()
            self._ventana.size = self._tam_ventana
            self._ventana.position = self._pos_ventana
            self.pantalla_completa = False
        else:
            self._tam_ventana = self._ventana.size
            self._pos_ventana = self._ventana.position
            self._ventana.set_fullscreen(desktop=True)
            self.pantalla_completa = True
        self._ajustar_tamano()
        self.mostrar_mapa = False
        agarrar = self.camara in (1, 3)
        pygame.event.set_grab(agarrar)
        pygame.mouse.set_visible(not agarrar)
        pygame.mouse.get_rel()

    # ------------------------------------------------------------------ OpenGL
    def _configurar_opengl(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)
        glEnable(GL_CULL_FACE)               # Toda la geometría está orientada: se descartan las caras traseras.
        glCullFace(GL_BACK)
        glFrontFace(GL_CCW)
        glClearColor(0.08, 0.09, 0.12, 1)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, (0.85, 0.85, 0.85, 1))
        glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, (1, 1, 1, 1))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.25, 0.25, 0.25, 1))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 18)

    @staticmethod
    def _textura_portal():
        """Degradado vertical verde claro para el fondo luminoso de la puerta."""
        t = np.linspace(0, 1, 32)[:, None]
        base = np.array([70, 225, 130]) * (1 - t) + np.array([215, 255, 225]) * t
        img = np.repeat(base[:, None, :], 4, axis=1)
        img = np.concatenate([img, np.full(img.shape[:2] + (1,), 255)], axis=2)
        return textura_desde_array(img.astype(np.uint8), nearest=False)

    # ------------------------------------------------------------------ partidas
    def nueva_partida(self, dificultad=None, semilla=None):
        """Crea una partida nueva y reconstruye todo lo que depende del mapa (cierra la anterior)."""
        if dificultad is not None:
            self.dificultad = por_clave(dificultad) if isinstance(dificultad, str) else dificultad
        self.partida = Partida(self.dificultad, semilla, reloj=self.reloj)
        self.escena.construir(self.partida)                 # Libera los VBO/EBO anteriores y crea los nuevos.
        self.hud.reiniciar_mapa()
        self._reconstruir_niebla()
        self.ruta_gl.reiniciar()
        self.yaw = self.yaw_personaje = self.partida.yaw_inicial      # Empieza mirando por el pasillo.
        self.pitch = 10.0 if self.camara == 3 else 0.0
        self.cam3.reiniciar()
        self._sincronizar_ruta()
        self._mensaje = ''
        pygame.display.set_caption(TITULO)

    def _reconstruir_niebla(self):
        """Plano de niebla de la cámara cenital: una malla de 1 quad y una textura de 1 texel por celda."""
        if self.malla_niebla:
            self.malla_niebla.liberar()
        if self.tex_niebla:
            liberar_texturas([self.tex_niebla])
        tam = len(self.partida.mapa)
        c = ConstructorMalla()
        c.quad((-0.5, ALTURA_NIEBLA, -0.5), (0, 0, tam), (tam, 0, 0), eu=(1, 0, 0), ev=(0, 0, 1),
               su=1 / tam, sv=1 / tam, ou=0.5 / tam, ov=0.5 / tam)
        vertices, indices, _ = c.construir()
        self.malla_niebla = MallaGL(vertices, indices)
        self.tex_niebla = textura_desde_array(colores_niebla(self.partida.exploracion), nearest=True)
        self._version_niebla = self.partida.exploracion.version

    def _sincronizar_ruta(self):
        while self.ruta_gl.n < len(self.partida.ruta):
            x, z = self.partida.ruta[self.ruta_gl.n]
            self.ruta_gl.añadir(x, 0.06, z)

    def _avisar(self, texto):
        self._mensaje = texto
        self._mensaje_hasta = self.reloj() + DURACION_MENSAJE

    # ------------------------------------------------------------------ entrada
    def procesar_evento(self, evento):
        """Devuelve False si hay que salir."""
        if evento.type == pygame.QUIT:
            return False
        if evento.type in (pygame.WINDOWRESIZED, pygame.WINDOWSIZECHANGED):
            self._ajustar_tamano()
            return True
        if evento.type == pygame.MOUSEMOTION and self.camara in (1, 3):
            self.yaw += evento.rel[0] * 0.16
            inferior, superior = (-70, 70) if self.camara == 1 else (-8, 30)
            self.pitch = max(inferior, min(superior, self.pitch - evento.rel[1] * 0.12))
        elif evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_TAB:
                self.mostrar_mapa = True
            self._tecla(evento.key)
            if evento.key == pygame.K_ESCAPE:
                return False
        elif evento.type == pygame.KEYUP and evento.key == pygame.K_TAB:
            self.mostrar_mapa = False
        elif evento.type == getattr(pygame, 'WINDOWFOCUSLOST', -1):
            self.mostrar_mapa = False
        return True

    def _tecla(self, tecla):
        if self.terror.tecla(tecla, self):                        # R (modo terror) y E (linterna, en modo terror).
            return
        if tecla == pygame.K_F11:
            self._alternar_pantalla_completa()
        elif tecla == pygame.K_1:
            self._cambiar_camara(1)
        elif tecla == pygame.K_2:
            self._cambiar_camara(2)
        elif tecla == pygame.K_3:
            self._cambiar_camara(3)
        elif tecla == pygame.K_l:
            self.tono = (self.tono + 1) % len(TONOS)
        elif tecla == pygame.K_i:
            self.luz_local = not self.luz_local
        elif tecla == pygame.K_h:
            self.mostrar_ayuda = not self.mostrar_ayuda
        elif tecla == pygame.K_n:
            self.nueva_partida()                                  # Misma dificultad.
        else:
            nombre = pygame.key.name(tecla).upper()
            for d in DIFICULTADES:
                if nombre in d.teclas:
                    self.nueva_partida(d)                         # Cambiar de dificultad reinicia la partida.
                    self._avisar(f'Dificultad {d.nombre}')
                    break

    def _cambiar_camara(self, camara):
        self.camara = camara
        if camara == 1:
            self.pitch = 0.0
        elif camara == 3:
            self.pitch = 10.0
            self.cam3.reiniciar()
        agarrar = camara in (1, 3)
        pygame.event.set_grab(agarrar)
        pygame.mouse.set_visible(not agarrar)
        if agarrar:
            pygame.mouse.get_rel()

    # ------------------------------------------------------------------ simulación
    def actualizar(self, dt, teclas=None):
        """Avanza la simulación `dt` segundos (ya limitado por el llamador) con el estado de `teclas`."""
        teclas = pygame.key.get_pressed() if teclas is None else teclas
        p = self.partida
        self.t_anim = self.reloj()
        caminando = False
        if not p.terminada:
            self.yaw += (int(teclas[pygame.K_RIGHT]) - int(teclas[pygame.K_LEFT])) * 110 * dt
            avance = int(teclas[pygame.K_w]) - int(teclas[pygame.K_s])
            lateral = int(teclas[pygame.K_d]) - int(teclas[pygame.K_a])
            dx, dz = p.mover_en_direccion(self.yaw, avance, lateral, dt)
            caminando = bool(dx or dz)
            if self.camara == 3 and (dx or dz):
                self.yaw_personaje = math.degrees(math.atan2(dx, -dz))
        for evento in p.actualizar(dt):
            if evento == 'esfera':
                restantes = p.esferas_restantes
                if restantes:
                    self._avisar(f'¡Esfera recogida! Quedan {restantes}')
            elif evento == 'puerta':
                self._avisar('¡Puerta de salida abierta! Búscala (marcada en el mapa)')
            elif evento == 'salida':
                pygame.display.set_caption('¡Salida alcanzada! Pulsa N para crear otro laberinto')
        self._sincronizar_ruta()
        self.terror.actualizar(dt, caminando, self)
        if self.camara == 3:
            self.cam3.actualizar(dt, p.mapa, p.x, p.z, self.yaw, self.pitch, p.bloqueadas())

    # ------------------------------------------------------------------ dibujo
    def dibujar(self):
        p = self.partida
        self.terror.antes_de_limpiar(self.camara)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        (glEnable if self.usar_cull else glDisable)(GL_CULL_FACE)
        self._aplicar_camara()
        self._aplicar_luces()
        glEnable(GL_LIGHTING)
        self.terror.empezar_escena(self)                        # Shader de linterna + niebla (solo modo terror, cámaras 1/3).
        self.escena.dibujar_solidos(p.puerta.desbloqueada)
        self._dibujar_dinamicos()
        self.terror.terminar_escena(self)                       # Apaga el shader y dibuja los halos.
        if not self.terror.activo_3d(self.camara):
            self.escena.dibujar_aristas()
        if self.camara == 2:
            self._dibujar_cenital()
        glDisable(GL_LIGHTING)
        self.terror.dibujar_efectos(self)                       # Viñeta y grano, antes del HUD.
        if self.mostrar_hud:
            mensaje = self._mensaje if self.reloj() < self._mensaje_hasta else ''
            self.hud.dibujar(p, self.camara, self.yaw, self.mostrar_mapa, self.mostrar_ayuda, mensaje, self.t_anim)

    def _aplicar_camara(self):
        p = self.partida
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        tam = len(p.mapa)
        if self.camara == 2:
            mitad_y = (tam + 2) / 2
            mitad_x = mitad_y * self.ancho / self.alto
            glOrtho(-mitad_x, mitad_x, -mitad_y, mitad_y, 0.1, FAR_PLANE_JUEGO)
        else:
            perspectiva(FOV, self.ancho / self.alto, NEAR_PLANE, FAR_PLANE_JUEGO)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        if self.camara == 2:
            centro = (tam - 1) / 2
            mirar_a((centro, 35, centro), (centro, 0, centro), (0, 0, -1))
        elif self.camara == 3:
            mirar_a(self.cam3.posicion, self.cam3.objetivo, (0, 1, 0))
        else:
            a, inc = math.radians(self.yaw), math.radians(self.pitch)
            oy = self.terror.balanceo_y()                       # 0 en modo clásico.
            mirar_a((p.x, 0.85 + oy, p.z),
                    (p.x + math.sin(a) * math.cos(inc), 0.85 + oy + math.sin(inc), p.z - math.cos(a) * math.cos(inc)),
                    (0, 1, 0))

    def _aplicar_luces(self):
        if self.terror.luces_fijas(self):                       # Modo terror: iluminación propia (shader / cenital).
            return
        p = self.partida
        glEnable(GL_LIGHT0)
        color = TONOS[self.tono][1]
        ambiente = 0.22 if self.luz_local else 0.38
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (*(v * ambiente for v in color), 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0, 0, 0, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (*(v * 0.9 for v in color), 1))
        glLightfv(GL_LIGHT0, GL_POSITION, (p.x, 0.85, p.z, 1) if self.luz_local else (0.4, 1, 0.5, 0))
        glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.22 if self.luz_local else 0)
        glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0.045 if self.luz_local else 0)
        if self.luz_local:
            glDisable(GL_LIGHT1)
        else:
            glEnable(GL_LIGHT1)
            glLightfv(GL_LIGHT1, GL_AMBIENT, (0, 0, 0, 1))
            glLightfv(GL_LIGHT1, GL_DIFFUSE, (*(v * 0.45 for v in color), 1))
            glLightfv(GL_LIGHT1, GL_POSITION, (-0.6, 0.8, -0.4, 0))

    def _dibujar_dinamicos(self):
        """Objetos que cambian cada fotograma: se dibujan con transformaciones sobre mallas compartidas."""
        p = self.partida
        if p.puerta.visible:
            f, c = p.salida
            textura = self.texturas['puerta_abierta' if p.puerta.desbloqueada else 'puerta_cerrada']
            # Giro de 180º para que el texto de la cara norte (hacia el pasillo) no salga en espejo.
            self.cubo.dibujar(textura, t_x=c + (ANCHO_PASILLO - 1) / 2, t_y=Puerta.ALTURA / 2 - p.puerta.hundimiento, t_z=f,
                              angulo=180, eje_y=1, sx=ANCHO_PASILLO, sy=Puerta.ALTURA, sz=1)
        pendientes = [e for e in p.esferas if not e.recogida]
        if pendientes:
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.30, 0.22, 0.05, 1))      # Brillo propio.
            for e in pendientes:
                y, angulo = e.pose(self.t_anim)
                self.esfera.dibujar(self.texturas['esfera'], t_x=e.x, t_y=y, t_z=e.z, angulo=angulo, eje_y=1,
                                    sx=ESFERA_ESCALA, sy=ESFERA_ESCALA, sz=ESFERA_ESCALA)
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0, 0, 0, 1))
        if self.camara == 3 and self.cam3.dibujar_personaje:
            a = math.radians(self.yaw_personaje)
            t = self.texturas
            # Un personaje redondeado reutiliza la esfera OBJ y sus VBO/EBO.
            def parte(textura, lateral, altura, frente, sx, sy, sz):
                self.esfera.dibujar(textura,
                    t_x=p.x + math.cos(a)*lateral + math.sin(a)*frente,
                    t_y=altura,
                    t_z=p.z + math.sin(a)*lateral - math.cos(a)*frente,
                    angulo=self.yaw_personaje, eje_y=1, sx=sx, sy=sy, sz=sz)

            parte(t['personaje'], 0, 0.57, 0, 0.34, 0.52, 0.26)
            parte(t['cabeza'], 0, 0.98, 0, 0.29, 0.29, 0.29)
            for lado in (-1, 1):
                parte(t['personaje'], lado * 0.21, 0.58, 0, 0.13, 0.36, 0.13)
                parte(t['personaje'], lado * 0.095, 0.20, 0, 0.14, 0.38, 0.15)
            parte(t['frente'], 0, 0.97, 0.14, 0.11, 0.08, 0.06)

    def _dibujar_cenital(self):
        """Rastro, marcador del jugador y niebla de lo no explorado (solo en la cámara cenital)."""
        p = self.partida
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glColor3f(1, 0.8, 0.1)
        glLineWidth(3)
        self.ruta_gl.dibujar()
        glLineWidth(1)
        glColor3f(0.1, 0.8, 1)
        glPointSize(9)
        glBegin(GL_POINTS)
        glVertex3f(p.x, 0.07, p.z)
        glEnd()
        glPointSize(1)
        glColor3f(1, 1, 1)
        if self.partida.exploracion.version != self._version_niebla:
            actualizar_textura_array(self.tex_niebla, colores_niebla(p.exploracion))
            self._version_niebla = p.exploracion.version
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBindTexture(GL_TEXTURE_2D, self.tex_niebla)
        self.malla_niebla.dibujar()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)

    # ------------------------------------------------------------------ ciclo de vida
    def ejecutar(self):
        reloj = pygame.time.Clock()
        while self.activo:
            dt = min(reloj.tick(FPS) / 1000, 0.05)
            for evento in pygame.event.get():
                if not self.procesar_evento(evento):
                    self.activo = False
            self.actualizar(dt)
            self.dibujar()
            pygame.display.flip()
        self.cerrar()

    def cerrar(self):
        """Libera todos los recursos de GPU mientras el contexto OpenGL sigue activo y cierra pygame."""
        self.liberar_recursos()
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        pygame.quit()

    def liberar_recursos(self):
        """Borra VBO, EBO y texturas (el contexto debe seguir activo). Se puede llamar una sola vez."""
        self.escena.liberar()
        for modelo in (self.cubo, self.esfera):
            modelo.liberar()
        self.hud.liberar()
        self.terror.liberar()
        self.ruta_gl.liberar()
        if self.malla_niebla:
            self.malla_niebla.liberar()
            self.malla_niebla = None
        liberar_texturas(list(self.texturas.values()) + [self.tex_niebla])
        self.tex_niebla = None
