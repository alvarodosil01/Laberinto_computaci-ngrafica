"""Generación del laberinto, alcanzabilidad, colocación de esferas, musgo y colisiones.

Convenio del mapa (igual que en la v5): `mapa[f][c]` vale 1 para pared y 0 para suelo, con
`f` = fila (eje Z del mundo) y `c` = columna (eje X). El centro de la celda (f, c) está en el
punto de mundo x = c, z = f, y la celda ocupa [c-0.5, c+0.5] x [f-0.5, f+0.5].

Novedad v6: la salida es una puerta abierta en el muro exterior inferior, justo debajo de la
celda (alto-2, ancho-2), que era la salida de la v5. Así la puerta siempre cierra un callejón
sin salida y no puede partir el laberinto en dos zonas.
"""
import math
import random
from collections import deque

import numpy as np

from configuracion import ANCHO_PASILLO

VECINOS_4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def generar(ancho=21, alto=21, aperturas=12, semilla=None):
    """Devuelve (mapa, entrada, salida). `salida` es la celda de la puerta (en el muro exterior)."""
    if min(ancho, alto) < 7 or ancho % 2 == 0 or alto % 2 == 0:
        raise ValueError('Las dimensiones deben ser impares y >= 7')
    azar = random.Random(semilla)
    mapa = [[1] * ancho for _ in range(alto)]
    mapa[1][1] = 0
    pila = [(1, 1)]
    while pila:
        f, c = pila[-1]
        vecinos = [(f + df, c + dc, f + df // 2, c + dc // 2)
                   for df, dc in ((-2, 0), (2, 0), (0, -2), (0, 2))
                   if 1 <= f + df < alto - 1 and 1 <= c + dc < ancho - 1
                   and mapa[f + df][c + dc]]
        if vecinos:
            nf, nc, mf, mc = azar.choice(vecinos)
            mapa[mf][mc] = mapa[nf][nc] = 0
            pila.append((nf, nc))
        else:
            pila.pop()
    opciones = [(f, c) for f in range(1, alto - 1)
                for c in range(1, ancho - 1) if mapa[f][c] and
                ((not mapa[f][c - 1] and not mapa[f][c + 1]) or
                 (not mapa[f - 1][c] and not mapa[f + 1][c]))]
    azar.shuffle(opciones)
    for f, c in opciones[:aperturas]:
        mapa[f][c] = 0
    entrada = (1, 1)
    salida = (alto - 1, ancho - 2)          # Puerta en el muro exterior inferior.
    mapa[salida[0]][salida[1]] = 0
    # Duplicar solo las bandas de pasillo (índices impares), manteniendo
    # las bandas de muro con grosor 1 y la misma topología del DFS.
    columnas = [c for c in range(ancho) for _ in range(ANCHO_PASILLO if c % 2 else 1)]
    filas = [f for f in range(alto) for _ in range(ANCHO_PASILLO if f % 2 else 1)]
    mapa = [[mapa[f][c] for c in columnas] for f in filas]
    entrada = (filas.index(entrada[0]), columnas.index(entrada[1]))
    salida = (filas.index(salida[0]), columnas.index(salida[1]))
    return mapa, entrada, salida


def celda_de(x, z):
    """Celda (fila, columna) que contiene el punto de mundo (x, z)."""
    return math.floor(z + 0.5), math.floor(x + 0.5)


def transitable(mapa, x, z, radio=0.18, bloqueadas=()):
    """True si un cuadrado de semilado `radio` centrado en (x, z) no toca paredes ni celdas bloqueadas.

    `bloqueadas` es un conjunto de celdas (f, c) sólidas aunque el mapa diga suelo: la puerta cerrada.
    (v6: se usa floor en lugar de int, que redondeaba hacia cero los valores negativos.)
    """
    for px in (x - radio, x + radio):
        for pz in (z - radio, z + radio):
            f, c = math.floor(pz + 0.5), math.floor(px + 0.5)
            if not (0 <= f < len(mapa) and 0 <= c < len(mapa[0])) or mapa[f][c]:
                return False
            if bloqueadas and (f, c) in bloqueadas:
                return False
    return True


def distancias(mapa, origen, bloqueadas=()):
    """BFS en 4 direcciones. Devuelve un dict {celda: pasos} con las celdas alcanzables."""
    if origen in bloqueadas or mapa[origen[0]][origen[1]]:
        return {}
    dist = {origen: 0}
    cola = deque([origen])
    while cola:
        f, c = cola.popleft()
        for df, dc in VECINOS_4:
            p = (f + df, c + dc)
            if (0 <= p[0] < len(mapa) and 0 <= p[1] < len(mapa[0]) and not mapa[p[0]][p[1]]
                    and p not in dist and p not in bloqueadas):
                dist[p] = dist[(f, c)] + 1
                cola.append(p)
    return dist


def alcanzable(mapa, inicio, fin):
    return fin in distancias(mapa, inicio)


def celdas_puerta(salida):
    """La abertura inferior ocupa todo el ancho del pasillo."""
    f, c = salida
    return frozenset((f, c + i) for i in range(ANCHO_PASILLO))


def celda_previa_a_puerta(salida):
    """Celda de suelo interior que da acceso a la puerta (la puerta está en el muro inferior)."""
    return salida[0] - 1, salida[1]


def colocar_esferas(mapa, entrada, salida, cantidad, azar, separacion):
    """Elige `cantidad` celdas para las esferas.

    Solo se usan celdas transitables y alcanzables desde la entrada *sin atravesar la puerta*
    (que empieza cerrada). Se evitan la entrada y la celda previa a la puerta, y se intenta
    mantener una separación Manhattan mínima entre esferas, relajándola si no cabe.
    """
    alcance = distancias(mapa, entrada, bloqueadas=celdas_puerta(salida))
    prohibidas = {entrada} | set(celdas_puerta(salida)) | {celda_previa_a_puerta(c) for c in celdas_puerta(salida)}
    candidatas = [c for c, d in alcance.items() if c not in prohibidas and d >= 3]
    if len(candidatas) < cantidad:
        candidatas = [c for c in alcance if c not in prohibidas]
    if len(candidatas) < cantidad:
        raise ValueError('No hay celdas suficientes para colocar las esferas')
    for sep in range(separacion, -1, -1):
        azar.shuffle(candidatas)
        elegidas = []
        for celda in candidatas:
            if all(abs(celda[0] - o[0]) + abs(celda[1] - o[1]) >= sep for o in elegidas):
                elegidas.append(celda)
                if len(elegidas) == cantidad:
                    return elegidas
    raise ValueError('No se pudieron colocar las esferas')   # inalcanzable: sep=0 acepta todo


def mascara_musgo(mapa, azar, fraccion):
    """Conjunto de celdas de pared con musgo: ruido aleatorio suavizado -> manchas coherentes."""
    alto, ancho = len(mapa), len(mapa[0])
    paredes = np.array(mapa, dtype=bool)
    ruido = np.array([[azar.random() for _ in range(ancho)] for _ in range(alto)])
    for _ in range(2):                       # Dos pasadas de suavizado 3x3 (con bordes replicados).
        p = np.pad(ruido, 1, mode='edge')
        ruido = sum(p[1 + df:1 + df + alto, 1 + dc:1 + dc + ancho]
                    for df in (-1, 0, 1) for dc in (-1, 0, 1)) / 9.0
    if not paredes.any() or fraccion <= 0:
        return set()
    umbral = np.quantile(ruido[paredes], 1.0 - fraccion)
    return {(int(f), int(c)) for f, c in zip(*np.nonzero(paredes & (ruido >= umbral)))}
