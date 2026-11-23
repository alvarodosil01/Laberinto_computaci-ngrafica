"""Interfaz 2D: texto, panel de datos, brújula, minimapa, ayuda y pantalla final.

Todo el texto y las formas se dibujan con UN lote dinámico (`LoteDinamico`): los glifos se
rasterizan una sola vez en un atlas de textura (pygame.font) y cada fotograma solo se rellenan
los vértices de los quads. No se crean texturas ni buffers por fotograma. El minimapa es una
textura de una celda = un texel que solo se vuelve a subir cuando cambia lo explorado.
"""
import math


import numpy as np
import pygame
from OpenGL.GL import *

from buffers import LoteDinamico
from exploracion import (COLOR_ENTRADA, COLOR_ESFERA, COLOR_SALIDA_CERRADA, colores_minimapa)
from texturas import actualizar_textura_array, bytes_superficie, liberar_texturas, textura_desde_array

CARACTERES = ''.join(chr(c) for c in range(32, 127)) + 'áéíóúüñÁÉÍÓÚÜÑ¡¿·°'
TAMANOS = {'peq': 16, 'med': 24, 'gran': 46}

BLANCO = (1.0, 1.0, 1.0, 1.0)
GRIS = (0.78, 0.80, 0.84, 1.0)
ROJO = (1.0, 0.32, 0.28, 1.0)
VERDE = (0.40, 1.0, 0.55, 1.0)
AMARILLO = (1.0, 0.85, 0.25, 1.0)
CIAN = (0.35, 0.85, 1.0, 1.0)
FONDO = (0.02, 0.03, 0.06, 0.62)

NOMBRES_RUMBO = ('N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO')


def formato_tiempo(segundos):
    segundos = max(0.0, segundos)
    minutos = int(segundos // 60)
    return f'{minutos:02d}:{segundos - 60 * minutos:04.1f}'


def nombre_rumbo(yaw):
    return NOMBRES_RUMBO[int(((yaw % 360) + 22.5) // 45) % 8]


class AtlasTexto:
    """Atlas de glifos para tres tamaños + un texel blanco para dibujar rectángulos de color."""

    def __init__(self):
        ancho_atlas = 1024
        piezas = []                                   # (tamaño, carácter, array RGBA, avance)
        for nombre, px in TAMANOS.items():
            fuente = pygame.font.Font(None, px)
            for ch in CARACTERES:
                img = fuente.render(ch, True, (255, 255, 255))
                rgba = np.frombuffer(bytes_superficie(img, 'RGBA', False), dtype=np.uint8)
                rgba = rgba.reshape(img.get_height(), img.get_width(), 4)
                piezas.append((nombre, ch, rgba, fuente.size(ch)[0]))
        x, y, alto_fila = 8, 0, 0                     # Los 8 primeros px de la fila 0 los usa el texel blanco.
        colocadas = []
        for nombre, ch, rgba, avance in piezas:
            h, w = rgba.shape[:2]
            if x + w + 2 > ancho_atlas:
                x, y, alto_fila = 0, y + alto_fila + 2, 0
            colocadas.append((nombre, ch, rgba, avance, x, y))
            x += w + 2
            alto_fila = max(alto_fila, h)
        alto_atlas = y + alto_fila + 2
        alto_atlas += (-alto_atlas) % 4
        atlas = np.zeros((alto_atlas, ancho_atlas, 4), dtype=np.uint8)
        atlas[0:4, 0:4] = 255                         # Texel blanco (4x4).
        self.glifos = {n: {} for n in TAMANOS}
        for nombre, ch, rgba, avance, gx, gy in colocadas:
            h, w = rgba.shape[:2]
            atlas[gy:gy + h, gx:gx + w] = rgba
            self.glifos[nombre][ch] = ((gx / ancho_atlas, gy / alto_atlas,
                                        (gx + w) / ancho_atlas, (gy + h) / alto_atlas), w, h, avance)
        self.uv_blanco = (2 / ancho_atlas, 2 / alto_atlas, 2 / ancho_atlas, 2 / alto_atlas)
        self.textura = textura_desde_array(atlas, nearest=False, repetir=False)
        self.altura = {n: self.glifos[n]['M'][2] for n in TAMANOS}

    def ancho(self, texto, tam):
        g = self.glifos[tam]
        return sum(g.get(ch, g['?'])[3] for ch in texto)

    def liberar(self):
        liberar_texturas([self.textura])


class Interfaz:
    def __init__(self, ancho, alto):
        self.ancho, self.alto = ancho, alto
        self.atlas = AtlasTexto()
        self.fondo = LoteDinamico(1500)        # Paneles y recuadros (debajo del minimapa).
        self.frente = LoteDinamico(3000)       # Texto, marcas y marcador del jugador.
        self.lote_mapa = LoteDinamico(4)       # Minimapa: un quad texturizado.
        self.tex_mapa = None
        self._tam_mapa = None
        self._version_mapa = None

    # ------------------------------------------------------------------ primitivas
    def _rect(self, lote, x, y, w, h, color):
        lote.quad(x, y, x + w, y + h, self.atlas.uv_blanco, color)

    def _texto(self, lote, texto, x, y, tam='med', color=BLANCO, ancla='izq', sombra=True):
        g = self.atlas.glifos[tam]
        ancho = self.atlas.ancho(texto, tam)
        if ancla == 'centro':
            x -= ancho / 2
        elif ancla == 'der':
            x -= ancho
        x, y = round(x), round(y)
        for pasada in ((1, 0.0, 0.0, 0.0, 0.75), (0, *color)) if sombra else ((0, *color),):
            d, r, gg, b, a = pasada
            cx = x
            for ch in texto:
                uv, w, h, avance = g.get(ch, g['?'])
                if ch != ' ':
                    lote.quad(cx + d, y + d, cx + d + w, y + d + h, uv, (r, gg, b, a))
                cx += avance
        return ancho

    # ------------------------------------------------------------------ minimapa
    def _preparar_mapa(self, partida):
        tam = len(partida.mapa)
        if self._tam_mapa != tam or self.tex_mapa is None:
            if self.tex_mapa:
                liberar_texturas([self.tex_mapa])
            self.tex_mapa = textura_desde_array(colores_minimapa(partida), nearest=True)
            self._tam_mapa = tam
            self._version_mapa = (partida.exploracion.version, partida.puerta.estado)
            return
        version = (partida.exploracion.version, partida.puerta.estado)
        if version != self._version_mapa:
            actualizar_textura_array(self.tex_mapa, colores_minimapa(partida))
            self._version_mapa = version

    def reiniciar_mapa(self):
        """Fuerza reconstruir la textura del minimapa (partida nueva: la exploración vuelve a cero)."""
        self._version_mapa = None
        if self.tex_mapa:
            liberar_texturas([self.tex_mapa])
            self.tex_mapa = None

    # ------------------------------------------------------------------ composición
    def dibujar(self, partida, camara, yaw, mostrar_mapa, mostrar_ayuda, mensaje, ahora):
        A, B, M = self.fondo, self.frente, self.lote_mapa
        A.limpiar(), B.limpiar(), M.limpiar()
        W, H = self.ancho, self.alto
        mini = None
        if camara != 2 and mostrar_mapa and not partida.terminada:
            self._preparar_mapa(partida)
            mini = self._componer_minimapa(A, B, M, partida, yaw)
        elif camara == 2 or partida.terminada:
            self._preparar_mapa(partida)             # Mantiene actualizada la textura aunque no se vea.
        self._panel_datos(A, B, partida)
        if camara == 2:
            self._indicador_norte(A, B)
        else:
            self._brujula(A, B, yaw)
        if mensaje:
            self._texto(B, mensaje, W / 2, 66, 'med', AMARILLO, 'centro')
        if mostrar_ayuda:
            self._ayuda(A, B)
        else:
            self._texto(B, 'H: ayuda', 14, H - 24, 'peq', GRIS)
        if partida.terminada:
            self._pantalla_final(A, B, partida)

        # ---- estado GL de la interfaz 2D ----
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, W, H, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        cull = glIsEnabled(GL_CULL_FACE)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.atlas.textura)
        A.dibujar()
        if mini is not None and M.n_quads:
            glBindTexture(GL_TEXTURE_2D, self.tex_mapa)
            M.dibujar()
            glBindTexture(GL_TEXTURE_2D, self.atlas.textura)
        B.dibujar()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        if cull:
            glEnable(GL_CULL_FACE)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    # ------------------------------------------------------------------ elementos
    def _panel_datos(self, A, B, partida):
        x, y, w, h = 12, 12, 318, 126
        self._rect(A, x, y, w, h, FONDO)
        d = partida.dificultad
        self._texto(B, 'DIFICULTAD', x + 12, y + 8, 'peq', GRIS)
        self._texto(B, d.nombre, x + 12 + 118, y + 5, 'med', AMARILLO)
        self._texto(B, 'TIEMPO', x + 12, y + 34, 'peq', GRIS)
        self._texto(B, formato_tiempo(partida.tiempo()), x + 12 + 118, y + 31, 'med',
                    VERDE if partida.terminada else BLANCO)
        self._texto(B, 'ESFERAS', x + 12, y + 60, 'peq', GRIS)
        self._texto(B, f'{partida.esferas_recogidas}/{partida.esferas_totales}', x + 12 + 118, y + 57, 'med',
                    BLANCO)
        restantes = partida.esferas_restantes
        self._texto(B, f'quedan {restantes}' if restantes else '¡todas!', x + 12 + 176, y + 61, 'peq',
                    AMARILLO if restantes else VERDE)
        self._texto(B, 'PUERTA', x + 12, y + 86, 'peq', GRIS)
        if partida.puerta.desbloqueada:
            self._texto(B, 'ABIERTA', x + 12 + 118, y + 83, 'med', VERDE)
        else:
            self._texto(B, 'CERRADA', x + 12 + 118, y + 83, 'med', ROJO)
        self._texto(B, 'F1 Fácil · F2 Normal · F3 Difícil', x + 12, y + 108, 'peq', CIAN)

    def _brujula(self, A, B, yaw):
        W = self.ancho
        ancho_b, alto_b, y0 = 460, 34, 10
        cx = W / 2
        x0 = cx - ancho_b / 2
        px_grado = 3.0
        self._rect(A, x0, y0, ancho_b, alto_b, FONDO)
        mitad = ancho_b / 2 - 6
        for angulo in range(0, 360, 15):
            d = ((angulo - yaw + 180) % 360) - 180
            dx = d * px_grado
            if abs(dx) > mitad:
                continue
            alfa = min(1.0, (mitad - abs(dx)) / 40.0)
            if angulo % 90 == 0:
                etiqueta = NOMBRES_RUMBO[angulo // 45]
                self._texto(B, etiqueta, cx + dx, y0 + 5, 'med', (ROJO if angulo == 0 else BLANCO)[:3] + (alfa,),
                            'centro', sombra=False)
            elif angulo % 45 == 0:
                self._texto(B, NOMBRES_RUMBO[angulo // 45], cx + dx, y0 + 9, 'peq', GRIS[:3] + (alfa,),
                            'centro', sombra=False)
            else:
                self._rect(B, cx + dx - 1, y0 + alto_b - 11, 2, 7, (0.8, 0.85, 0.9, 0.7 * alfa))
        # Marcador central (triángulo) y rumbo numérico.
        B.quad_libre([(cx - 7, y0 + alto_b + 9), (cx + 7, y0 + alto_b + 9), (cx, y0 + alto_b + 1), (cx, y0 + alto_b + 1)],
                     [self.atlas.uv_blanco[:2]] * 4, AMARILLO)
        self._texto(B, f'{nombre_rumbo(yaw)} {int(yaw % 360):03d}°', cx, y0 + alto_b + 8, 'peq', AMARILLO, 'centro')

    def _indicador_norte(self, A, B):
        cx = self.ancho / 2
        self._rect(A, cx - 120, 10, 240, 30, FONDO)
        self._texto(B, 'Vista cenital: el NORTE está arriba', cx, 17, 'peq', GRIS, 'centro')

    def _ayuda(self, A, B):
        lineas = ('W A S D  mover (según la cámara)', 'Ratón o flechas izq/der  orientar la vista',
                  '1 / 2 / 3  cámara: primera persona / cenital / tercera',
                  'F1 F2 F3 (o 4 5 6)  dificultad', 'N  nuevo laberinto     L  tono     I  luz clásica',
                  'R  modo terror/clásico     E  linterna (modo terror)',
                  'Tab (mantener)  mapa    H  ayuda    Esc  salir',
                  'F11  pantalla completa / ventana')
        h = 16 * len(lineas) + 14
        y = self.alto - h - 12
        self._rect(A, 12, y, 400, h, FONDO)
        for i, t in enumerate(lineas):
            self._texto(B, t, 22, y + 8 + 16 * i, 'peq', BLANCO if i == 0 else GRIS)

    def _componer_minimapa(self, A, B, M, partida, yaw):
        tam = len(partida.mapa)
        celda = min(12, 220 // tam)
        lado = tam * celda
        pad = 8
        ancho_panel = max(lado + 2 * pad, 188)
        alto_panel = lado + 2 * pad + 22 + 38
        x_panel = self.ancho - ancho_panel - 12
        y_panel = self.alto - alto_panel - 12
        self._rect(A, x_panel, y_panel, ancho_panel, alto_panel, FONDO)
        self._texto(B, 'MAPA EXPLORADO', x_panel + ancho_panel / 2, y_panel + 5, 'peq', GRIS, 'centro')
        mx = x_panel + (ancho_panel - lado) / 2
        my = y_panel + 22 + pad / 2
        self._rect(A, mx - 2, my - 2, lado + 4, lado + 4, (0.9, 0.9, 0.95, 0.9))     # Marco.
        M.quad(mx, my, mx + lado, my + lado, (0, 0, 1, 1), (1, 1, 1, 1))
        # Marcador del jugador: triángulo orientado según la mirada (norte = arriba).
        px = mx + (partida.x + 0.5) * celda
        py = my + (partida.z + 0.5) * celda
        a = math.radians(yaw)
        d = (math.sin(a), -math.cos(a))
        n = (-d[1], d[0])
        r = max(4.0, celda * 0.6)
        puntos = [(px + d[0] * r * 1.3, py + d[1] * r * 1.3),
                  (px - d[0] * r * 0.8 + n[0] * r * 0.8, py - d[1] * r * 0.8 + n[1] * r * 0.8),
                  (px - d[0] * r * 0.3, py - d[1] * r * 0.3),
                  (px - d[0] * r * 0.8 - n[0] * r * 0.8, py - d[1] * r * 0.8 - n[1] * r * 0.8)]
        uvb = [self.atlas.uv_blanco[:2]] * 4
        sombra = [(x + 1, y + 1) for x, y in puntos]
        B.quad_libre(sombra, uvb, (0, 0, 0, 0.9))
        B.quad_libre(puntos, uvb, CIAN)
        # Leyenda.
        ly = my + lado + pad + 2
        lx = x_panel + 10
        for color, texto in ((COLOR_ENTRADA, 'Entrada'), (COLOR_SALIDA_CERRADA, 'Salida'), (COLOR_ESFERA, 'Esfera')):
            self._rect(B, lx, ly + 3, 9, 9, tuple(c / 255 for c in color))
            lx += 14 + self._texto(B, texto, lx + 14, ly, 'peq', GRIS) + 6
        self._texto(B, 'Oscuro = sin explorar', x_panel + 10, ly + 16, 'peq', GRIS)
        return (mx, my, lado)

    def _pantalla_final(self, A, B, partida):
        W, H = self.ancho, self.alto
        self._rect(A, 0, 0, W, H, (0.0, 0.0, 0.03, 0.55))
        pw, ph = 620, 330
        x, y = (W - pw) / 2, (H - ph) / 2
        self._rect(A, x - 3, y - 3, pw + 6, ph + 6, (0.4, 1.0, 0.55, 0.9))
        self._rect(A, x, y, pw, ph, (0.03, 0.05, 0.09, 0.96))
        cx = W / 2
        self._texto(B, '¡LABERINTO COMPLETADO!', cx, y + 24, 'gran', VERDE, 'centro')
        filas = (('Dificultad', partida.dificultad.nombre),
                 ('Tiempo', formato_tiempo(partida.tiempo())),
                 ('Esferas recogidas', f'{partida.esferas_recogidas} / {partida.esferas_totales}'))
        for i, (etiqueta, valor) in enumerate(filas):
            yy = y + 98 + 40 * i
            self._texto(B, etiqueta, cx - 40, yy, 'med', GRIS, 'der')
            self._texto(B, valor, cx - 20, yy, 'med', BLANCO)
        self._texto(B, 'Pulsa N para empezar otra partida', cx, y + 234, 'med', AMARILLO, 'centro')
        self._texto(B, 'F1 / F2 / F3: elegir dificultad   ·   Esc: salir', cx, y + 270, 'peq', GRIS, 'centro')

    def liberar(self):
        self.fondo.liberar()
        self.frente.liberar()
        self.lote_mapa.liberar()
        self.atlas.liberar()
        if self.tex_mapa:
            liberar_texturas([self.tex_mapa])
            self.tex_mapa = None

