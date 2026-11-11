"""Generación y colisiones del laberinto."""
import random
from collections import deque


def generar(ancho=21, alto=21, aperturas=12, semilla=None):
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
    return mapa, (1, 1), (alto - 2, ancho - 2)


def transitable(mapa, x, z, radio=0.18):
    for px in (x - radio, x + radio):
        for pz in (z - radio, z + radio):
            f, c = int(pz + 0.5), int(px + 0.5)
            if not (0 <= f < len(mapa) and 0 <= c < len(mapa[0])) or mapa[f][c]:
                return False
    return True


def alcanzable(mapa, inicio, fin):
    cola, visto = deque([inicio]), {inicio}
    while cola:
        f, c = cola.popleft()
        if (f, c) == fin:
            return True
        for df, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p = (f + df, c + dc)
            if 0 <= p[0] < len(mapa) and 0 <= p[1] < len(mapa[0]) and not mapa[p[0]][p[1]] and p not in visto:
                visto.add(p)
                cola.append(p)
    return False
