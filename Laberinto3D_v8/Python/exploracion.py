"""Mapa explorado: regla de revelado y texturas por celda (minimapa y niebla de la cámara cenital).

Regla (simple y consistente): al entrar el jugador en una celda se revelan
  1. todas las celdas de suelo a las que se llega en como máximo `radio` pasos de pasillo (4 direcciones,
     sin atravesar paredes), y
  2. las paredes que rodean (8 vecinas) a cualquiera de esas celdas de suelo.
Así no se «ve» a través de las paredes: solo se descubre lo que se ha recorrido o está al alcance.
Una `Exploracion` nueva (nueva partida) empieza vacía.
"""
from collections import deque

import numpy as np

from laberinto import VECINOS_4, celda_de

COLOR_DESCONOCIDO = (14, 15, 22, 255)
COLOR_PARED = (176, 160, 124, 255)
COLOR_SUELO = (54, 96, 150, 255)
COLOR_ENTRADA = (60, 220, 90, 255)
COLOR_SALIDA_CERRADA = (235, 60, 60, 255)
COLOR_SALIDA_ABIERTA = (80, 255, 140, 255)
COLOR_ESFERA = (255, 214, 40, 255)


class Exploracion:
    def __init__(self, mapa, radio):
        self.mapa = mapa
        self.radio = radio
        self.alto, self.ancho = len(mapa), len(mapa[0])
        self.descubierto = np.zeros((self.alto, self.ancho), dtype=bool)
        self.version = 0                  # Se incrementa cuando cambia lo descubierto.
        self._ultima = None

    def revelar_desde(self, celda):
        """Revela alrededor de `celda`. Devuelve True si se descubrió algo nuevo."""
        if celda == self._ultima:
            return False
        self._ultima = celda
        antes = int(self.descubierto.sum())
        dist = {celda: 0}
        cola = deque([celda])
        suelo = [celda]
        while cola:
            f, c = cola.popleft()
            if dist[(f, c)] == self.radio:
                continue
            for df, dc in VECINOS_4:
                p = (f + df, c + dc)
                if (0 <= p[0] < self.alto and 0 <= p[1] < self.ancho and not self.mapa[p[0]][p[1]]
                        and p not in dist):
                    dist[p] = dist[(f, c)] + 1
                    cola.append(p)
                    suelo.append(p)
        for f, c in suelo:
            self.descubierto[f, c] = True
            for df in (-1, 0, 1):                      # Solo PAREDES vecinas: el suelo se revela únicamente por pasillo.
                for dc in (-1, 0, 1):
                    vf, vc = f + df, c + dc
                    if 0 <= vf < self.alto and 0 <= vc < self.ancho and self.mapa[vf][vc]:
                        self.descubierto[vf, vc] = True
        nuevo = int(self.descubierto.sum()) > antes
        if nuevo:
            self.version += 1
        return nuevo

    def revelar_celda(self, celda):
        """Revela una sola celda (y sus vecinas de pared): p. ej. la puerta al desbloquearse."""
        f, c = celda
        antes = int(self.descubierto.sum())
        self.descubierto[f, c] = True
        for df in (-1, 0, 1):
            for dc in (-1, 0, 1):
                vf, vc = f + df, c + dc
                if 0 <= vf < self.alto and 0 <= vc < self.ancho and self.mapa[vf][vc]:
                    self.descubierto[vf, vc] = True
        if int(self.descubierto.sum()) > antes:
            self.version += 1

    def esta_descubierta(self, celda):
        return bool(self.descubierto[celda[0], celda[1]])


def colores_minimapa(partida):
    """Array (alto, ancho, 4) uint8 con el color de cada celda del minimapa."""
    ex = partida.exploracion
    mapa = np.array(partida.mapa, dtype=bool)
    img = np.empty((ex.alto, ex.ancho, 4), dtype=np.uint8)
    img[:] = COLOR_DESCONOCIDO
    d = ex.descubierto
    img[d & mapa] = COLOR_PARED
    img[d & ~mapa] = COLOR_SUELO
    f, c = partida.entrada
    img[f, c] = COLOR_ENTRADA
    f, c = partida.salida
    if d[f, c] or partida.puerta.desbloqueada:            # La salida se muestra si se ha descubierto o ya se abrió.
        img[f, c] = COLOR_SALIDA_ABIERTA if partida.puerta.desbloqueada else COLOR_SALIDA_CERRADA
    for e in partida.esferas:
        if not e.recogida and d[e.celda[0], e.celda[1]]:
            img[e.celda[0], e.celda[1]] = COLOR_ESFERA
    return img


def colores_niebla(exploracion):
    """Array (alto, ancho, 4): opaco donde no se ha explorado, transparente donde sí."""
    img = np.zeros((exploracion.alto, exploracion.ancho, 4), dtype=np.uint8)
    img[~exploracion.descubierto] = (6, 7, 11, 255)
    return img
