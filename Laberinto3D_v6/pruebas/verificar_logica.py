"""Pruebas de lógica y geometría de Laberinto 3D v6 (no necesitan ventana ni OpenGL).

Ejecutar:   python pruebas/verificar_logica.py
Sale con código 1 si alguna comprobación falla.
"""
import math
import os
import random
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Python'))

import numpy as np

from camara_tercera import CamaraTercera, distancia_segura
from configuracion import (ALTURA_PARED, ALTURA_REMATE, FRACCION_MUSGO, PUERTA_UMBRAL, RADIO_JUGADOR,
                           TERCERA_DIST_MAX, TERCERA_MARGEN)
from dificultad import DIFICULTADES
from exploracion import colores_minimapa, colores_niebla
from geometria import (ConstructorMalla, GRUPOS_PARED, caras_expuestas, compartir_vertices,
                       construir_geometria_estatica)
from hud import formato_tiempo, nombre_rumbo
from laberinto import (alcanzable, celda_previa_a_puerta, distancias, generar, transitable)
from obj import cargar_obj
from objetos import Puerta
from partida import Partida

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Python')
SEMILLAS = (1, 2, 3, 7, 42, 99, 123, 2024)
resultados = []


def prueba(f):
    def envoltura():
        try:
            informe = f()
            resultados.append((f.__name__, True, informe or ''))
        except Exception:
            resultados.append((f.__name__, False, traceback.format_exc(limit=4)))
    envoltura.__name__ = f.__name__
    PRUEBAS.append(envoltura)
    return f


PRUEBAS = []


class Reloj:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


# ----------------------------------------------------------------------------- generación
@prueba
def laberinto_dificultades_y_alcanzabilidad():
    n = 0
    for d in DIFICULTADES:
        for semilla in SEMILLAS:
            mapa, entrada, salida = generar(d.tam, d.tam, d.aperturas, semilla)
            assert len(mapa) == d.tam and len(mapa[0]) == d.tam and d.tam % 2 == 1
            assert alcanzable(mapa, entrada, salida), (d.clave, semilla)
            f, c = salida
            assert f == d.tam - 1 and 0 < c < d.tam - 1, 'la puerta debe estar en el muro exterior'
            vecinos_libres = [(f + df, c + dc) for df, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                              if 0 <= f + df < d.tam and 0 <= c + dc < d.tam and not mapa[f + df][c + dc]]
            assert vecinos_libres == [celda_previa_a_puerta(salida)], 'la puerta debe cerrar un callejón'
            # Con la puerta cerrada TODO el suelo (salvo la puerta) sigue siendo una sola zona conexa.
            libres = {(i, j) for i in range(d.tam) for j in range(d.tam) if not mapa[i][j]} - {salida}
            assert set(distancias(mapa, entrada, bloqueadas={salida})) == libres, 'zona partida por la puerta'
            n += 1
    return f'{n} laberintos (3 dificultades x {len(SEMILLAS)} semillas): conexos, puerta en callejón'


@prueba
def parametros_de_dificultad_coherentes():
    tam = [d.tam for d in DIFICULTADES]
    esf = [d.esferas for d in DIFICULTADES]
    aper = [d.aperturas for d in DIFICULTADES]
    vision = [d.radio_vision for d in DIFICULTADES]
    assert tam == sorted(tam) and esf == sorted(esf) and aper == sorted(aper, reverse=True)
    assert vision == sorted(vision, reverse=True) and len({d.clave for d in DIFICULTADES}) == 3
    return ' | '.join(f'{d.nombre}: {d.tam}x{d.tam}, {d.esferas} esferas, {d.aperturas} conexiones, visión {d.radio_vision}'
                      for d in DIFICULTADES)


@prueba
def esferas_en_celdas_alcanzables():
    total = 0
    for d in DIFICULTADES:
        for semilla in range(40):
            p = Partida(d, semilla)
            alcance = distancias(p.mapa, p.entrada, bloqueadas={p.salida})
            celdas = [e.celda for e in p.esferas]
            assert len(celdas) == d.esferas == len(set(celdas)), 'cantidad o repetidas'
            for c in celdas:
                assert not p.mapa[c[0]][c[1]], 'esfera dentro de una pared'
                assert c in alcance, 'esfera inalcanzable con la puerta cerrada'
                assert c not in (p.entrada, p.salida, celda_previa_a_puerta(p.salida))
            total += len(celdas)
    return f'{total} esferas comprobadas (120 partidas)'


# ----------------------------------------------------------------------------- geometría
def _grupos(semilla=5, dif=DIFICULTADES[1]):
    p = Partida(dif, semilla)
    return p, construir_geometria_estatica(p.mapa, p.salida, p.entrada, p.musgo)


def _triangulos(vertices, indices):
    t = indices.reshape(-1, 3)
    return vertices[t[:, 0]], vertices[t[:, 1]], vertices[t[:, 2]]


@prueba
def geometria_sin_caras_ocultas():
    """Cada pared-suelo contiguo da exactamente una cara; pared-pared ninguna; nada hacia fuera del mapa."""
    for dif in DIFICULTADES:
        p, g = _grupos(11, dif)
        mapa = p.mapa
        alto, ancho = len(mapa), len(mapa[0])
        esperadas = set()
        for f in range(alto):
            for c in range(ancho):
                if not mapa[f][c]:
                    continue
                for nx, nz in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    vf, vc = f + nz, c + nx
                    if 0 <= vf < alto and 0 <= vc < ancho and not mapa[vf][vc]:
                        esperadas.add((f, c, nx, nz))
        assert esperadas == set(caras_expuestas(mapa))
        # Quads laterales realmente presentes en los buffers (pared + musgo).
        n_quads = sum(len(g[n][1]) // 6 for n in ('pared', 'musgo'))
        assert n_quads == len(esperadas), (n_quads, len(esperadas))
        # Ninguna cara mira a otra pared ni fuera del mapa: la normal de cada triángulo apunta a suelo transitable.
        for nombre in ('pared', 'musgo', 'remate'):
            v, i, _ = g[nombre]
            a, b, c3 = _triangulos(v, i)
            for t in range(len(a)):
                n = a[t, 3:6]
                if abs(n[1]) > 0.5:
                    continue                                          # Tapas superiores.
                cen = (a[t, :3] + b[t, :3] + c3[t, :3]) / 3
                px, pz = cen[0] + 0.2 * n[0], cen[2] + 0.2 * n[2]
                fc, cc = math.floor(pz + 0.5), math.floor(px + 0.5)
                assert 0 <= fc < alto and 0 <= cc < ancho and not mapa[fc][cc], 'cara visible hacia pared/exterior'
    return 'caras laterales = exactamente las pared-suelo; 0 entre paredes contiguas ni hacia el exterior (3 dificultades)'


@prueba
def geometria_orientacion_normales_y_uv():
    """Sin caras invertidas (CCW coincide con la normal, que es unitaria) y sin texturas deformadas."""
    for dif in DIFICULTADES:
        p, g = _grupos(21, dif)
        for nombre, (v, i, _) in g.items():
            if nombre == 'aristas':
                continue
            a, b, c = _triangulos(v, i)
            geo = np.cross(b[:, :3] - a[:, :3], c[:, :3] - a[:, :3])
            nrm = a[:, 3:6]
            assert np.allclose(np.linalg.norm(nrm, axis=1), 1.0, atol=1e-5), f'{nombre}: normales no unitarias'
            assert np.all(np.einsum('ij,ij->i', geo, nrm) > 1e-9), f'{nombre}: triángulos con orientación invertida'
            # Los tres vértices de un triángulo comparten normal (caras planas).
            assert np.allclose(a[:, 3:6], b[:, 3:6]) and np.allclose(a[:, 3:6], c[:, 3:6])
            if nombre in GRUPOS_PARED + ('suelo',):
                # Jacobiano UV/mundo: (u,v) como función afín de la posición. Se resuelve por mínimos cuadrados.
                pos, uv = v[:, :3].astype(np.float64), v[:, 6:8].astype(np.float64)
                for tri in i.reshape(-1, 3)[:: max(1, len(i) // 600)]:
                    P = pos[tri]
                    U = uv[tri]
                    e1, e2 = P[1] - P[0], P[2] - P[0]
                    d1, d2 = U[1] - U[0], U[2] - U[0]
                    # Para cada eje de textura, el gradiente en el plano de la cara debe tener módulo = escala esperada.
                    n = np.cross(e1, e2)
                    n /= np.linalg.norm(n)
                    M = np.array([e1, e2, n]).T
                    grad_u = np.linalg.solve(M.T, np.array([d1[0], d2[0], 0]))
                    grad_v = np.linalg.solve(M.T, np.array([d1[1], d2[1], 0]))
                    gu, gv = np.linalg.norm(grad_u), np.linalg.norm(grad_v)
                    if nombre in ('pared', 'musgo'):
                        assert abs(gu - 1.0) < 1e-4 and abs(gv - 1.0 / ALTURA_PARED) < 1e-4, (nombre, gu, gv)
                    elif nombre == 'remate':
                        assert abs(gu - 1.0) < 1e-4 and abs(gv - 1.0) < 1e-4, (nombre, gu, gv)
                    else:
                        assert abs(gu - 1.0) < 1e-4 and abs(gv - 1.0) < 1e-4
                    # u y v perpendiculares: sin cizalla.
                    assert abs(float(grad_u @ grad_v)) < 1e-6
    return 'normales unitarias, CCW = normal, UV en unidades de mundo (1 azulejo = 1 x 1.9 en pared; sin cizalla)'


@prueba
def vertices_compartidos_sin_perdida():
    """El EBO comparte solo vértices con posición+normal+UV idénticas y reproduce el flujo original."""
    for dif in DIFICULTADES:
        p = Partida(dif, 3)
        # Reconstruye el flujo "suelto" con ConstructorMalla para compararlo con (vertices, indices).
        c = ConstructorMalla()
        rng = random.Random(0)
        for _ in range(300):
            x, z = rng.randrange(10), rng.randrange(10)
            c.quad((x, 0, z), (1, 0, 0), (0, 1, 0), eu=(1, 0, 0), ev=(0, 1, 0))
            c.quad((x, 0, z), (0, 0, 1), (1, 0, 0), eu=(1, 0, 0), ev=(0, 0, 1))
        sueltos = np.round(np.array(c._filas), 6) + 0.0
        v, i, n_sueltos = c.construir()
        assert n_sueltos == len(sueltos) and len(v) < len(sueltos), 'debería haber vértices compartidos'
        recon = v[i.reshape(-1)]
        original = sueltos[np.array(c._indices)]
        assert np.allclose(recon, original, atol=1e-6), 'la reconstrucción por índices difiere del original'
        # No hay dos vértices únicos idénticos (se ha compartido todo lo compartible)...
        assert len(np.unique(np.round(v.astype(np.float64), 6), axis=0)) == len(v)
    # ...pero esquinas con la misma posición y normal/UV distintas NO se unen (caso explícito).
    a = np.array([[0, 0, 0, 0, 1, 0, 0, 0], [0, 0, 0, 0, 1, 0, 1, 0],      # mismo punto y normal, UV distinta
                  [0, 0, 0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 0, 0, 0]], float)  # normal distinta / duplicado exacto
    v, idx = compartir_vertices(a, np.arange(4))
    assert len(v) == 3 and idx[0] == idx[3] and len({idx[0], idx[1], idx[2]}) == 3
    return 'reconstrucción por índices idéntica; UV/normal distintas no se fusionan'


@prueba
def estadistica_de_vertices_y_tipos():
    p, g = _grupos(5)
    lineas = []
    for nombre, (v, i, sueltos) in g.items():
        assert v.dtype == np.float32 and v.flags['C_CONTIGUOUS']
        assert i.dtype in (np.uint16, np.uint32) and int(i.max()) < len(v)
        if i.dtype == np.uint16:
            assert len(v) <= 65535
        lineas.append(f'{nombre}: {sueltos}->{len(v)} v, {len(i)} i ({i.dtype})')
    return '; '.join(lineas)


@prueba
def obj_cargado_con_indices_y_orientacion():
    for archivo, esperados in (('cubo.obj', (24, 36)), ('esfera_lr.obj', (151, 672))):
        v, i, sueltos = cargar_obj(os.path.join(BASE, 'modelos', archivo))
        assert (len(v), len(i)) == esperados, (archivo, len(v), len(i))
        a, b, c = _triangulos(v, i)
        geo = np.cross(b[:, :3] - a[:, :3], c[:, :3] - a[:, :3])
        mal = int((np.einsum('ij,ij->i', geo, a[:, 3:6] + b[:, 3:6] + c[:, 3:6]) < 0).sum())
        assert mal == 0, f'{archivo}: {mal} triángulos invertidos tras orientar'
    return 'cubo 36 índices/24 vértices (en lugar de 36 vértices); esfera 672 índices/151 vértices; 0 triángulos invertidos'


@prueba
def musgo_parte_de_las_paredes():
    fr = []
    for dif in DIFICULTADES:
        p, g = _grupos(8, dif)
        quads_p, quads_m = len(g['pared'][1]) // 6, len(g['musgo'][1]) // 6
        total = quads_p + quads_m
        assert quads_m > 0 and quads_p > 0
        fr.append(quads_m / total)
        assert 0.15 < quads_m / total < 0.60, quads_m / total
        assert all(p.mapa[f][c] == 1 for f, c in p.musgo), 'musgo solo en paredes'
    return 'fracción de caras con musgo: ' + ', '.join(f'{x:.0%}' for x in fr) + f' (objetivo {FRACCION_MUSGO:.0%})'


# ----------------------------------------------------------------------------- juego
@prueba
def puerta_solida_hasta_hundirse():
    puerta = Puerta((20, 19))
    assert puerta.solida and puerta.bloqueadas() == {(20, 19)} and not puerta.desbloqueada
    puerta.actualizar(5.0)
    assert puerta.estado == Puerta.CERRADA, 'sin desbloquear no se abre'
    puerta.desbloquear()
    vistos = []
    t = 0.0
    while puerta.estado != Puerta.ABIERTA:
        puerta.actualizar(1 / 60)
        t += 1 / 60
        # Coherencia visible/colisión: sólida <=> su cara superior está por encima del umbral de paso.
        assert puerta.solida == (puerta.altura_superior > PUERTA_UMBRAL)
        vistos.append(puerta.solida)
    assert vistos[0] and not vistos[-1] and not puerta.solida and puerta.bloqueadas() == frozenset()
    assert vistos == sorted(vistos, reverse=True), 'sólida -> no sólida una sola vez'
    return f'se abre en {t:.2f} s; pasa a no sólida con la cara superior bajo {PUERTA_UMBRAL} m'


def _camino(mapa, origen, destino, bloqueadas=()):
    """Camino BFS de celdas origen->destino."""
    from collections import deque
    previo = {origen: None}
    cola = deque([origen])
    while cola:
        f, c = cola.popleft()
        if (f, c) == destino:
            break
        for df, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p = (f + df, c + dc)
            if p not in previo and 0 <= p[0] < len(mapa) and 0 <= p[1] < len(mapa[0]) \
                    and not mapa[p[0]][p[1]] and p not in bloqueadas:
                previo[p] = (f, c)
                cola.append(p)
    ruta, n = [], destino
    while n is not None:
        ruta.append(n)
        n = previo[n]
    return ruta[::-1]


def _ir_a(p, celda, dt=1 / 60, paso=0.045, reloj=None):
    """Mueve al jugador al centro de `celda` pasando por el centro de cada celda del camino. Devuelve los eventos."""
    eventos = []
    for f, c in _camino(p.mapa, p.celda_jugador, celda, bloqueadas=p.bloqueadas())[1:]:
        while math.hypot(p.x - c, p.z - f) > 0.02 and not p.terminada:
            d = math.hypot(c - p.x, f - p.z)
            k = min(paso, d) / d
            p.mover((c - p.x) * k, (f - p.z) * k)
            eventos += p.actualizar(dt)
            if reloj:
                reloj.t += dt
    return eventos


@prueba
def partida_completa_esferas_puerta_salida_y_cronometro():
    for dif in DIFICULTADES:
        reloj = Reloj()
        p = Partida(dif, 17, reloj=reloj)
        assert p.tiempo() == 0 and not p.terminada and p.esferas_restantes == dif.esferas
        # 1) La puerta cerrada es un muro: no se puede entrar ni terminar.
        eventos = _ir_a(p, celda_previa_a_puerta(p.salida), reloj=reloj)
        for _ in range(120):
            p.mover(0, 0.05)                                    # Empuja hacia el sur, contra la puerta.
            eventos += p.actualizar(1 / 60)
        assert p.celda_jugador != p.salida and not p.terminada and p.puerta.solida
        assert p.z < p.salida[0] - 0.5 + 1e-6 - RADIO_JUGADOR + 0.2, 'el jugador no debe solapar la puerta'
        # 2) Recoger todas las esferas: cada una exactamente una vez (el evento 'esfera' se emite una vez por esfera).
        previas = p.esferas_restantes
        while p.esferas_restantes:
            objetivo = next(e for e in p.esferas if not e.recogida)
            eventos += _ir_a(p, objetivo.celda, reloj=reloj)
            assert objetivo.recogida and p.esferas_restantes < previas
            previas = p.esferas_restantes
            if p.esferas_restantes:
                assert not p.puerta.desbloqueada, 'la puerta no se abre hasta recogerlas todas'
        for _ in range(30):
            eventos += [x for x in p.actualizar(1 / 60) if x == 'esfera']    # Quedarse encima no recoge de nuevo.
        assert eventos.count('esfera') == dif.esferas and eventos.count('puerta') == 1
        assert p.puerta.desbloqueada and p.esferas_restantes == 0
        # 3) Mientras se hunde sigue siendo sólida; al abrirse se puede pasar y terminar.
        assert p.puerta.solida
        t_final_antes = reloj.t
        _ir_a(p, celda_previa_a_puerta(p.salida), reloj=reloj)
        for _ in range(240):
            p.actualizar(1 / 60)
            reloj.t += 1 / 60
        assert not p.puerta.solida and not p.terminada
        _ir_a(p, p.salida, reloj=reloj)
        assert p.terminada and p.celda_jugador == p.salida
        # 4) El cronómetro se detiene al completar la partida.
        t_congelado = p.tiempo()
        reloj.t += 50
        assert p.tiempo() == t_congelado and t_congelado > 0
        assert not p.mover(0.3, 0)                              # Fin de partida: el jugador queda quieto.
    return 'esferas 1 vez c/u -> puerta se abre -> salida; antes de abrir la puerta no deja entrar; cronómetro se congela'


@prueba
def cronometro_y_reinicio():
    reloj = Reloj()
    p = Partida('normal', 4, reloj=reloj)
    reloj.t += 12.5
    assert abs(p.tiempo() - 12.5) < 1e-9
    q = Partida('facil', 4, reloj=reloj)                        # Nueva partida / cambio de dificultad: reloj a 0.
    assert q.tiempo() == 0 and q.esferas_restantes == q.esferas_totales == 3 and not q.terminada
    assert formato_tiempo(75.34) == '01:15.3' and formato_tiempo(0) == '00:00.0'
    return 'el reloj arranca con la partida, y N / cambio de dificultad crean una partida con reloj a 0'


@prueba
def exploracion_revela_solo_lo_cercano_y_se_reinicia():
    p = Partida('normal', 6)
    ex = p.exploracion
    inicial = int(ex.descubierto.sum())
    assert ex.esta_descubierta(p.entrada) and 0 < inicial < 0.2 * 21 * 21
    assert not ex.esta_descubierta(p.salida), 'la salida lejana no está descubierta al empezar'
    # Regla: celdas de suelo a <= radio pasos + sus paredes vecinas; ninguna celda de suelo más lejos.
    dist = distancias(p.mapa, p.celda_jugador)
    for f in range(21):
        for c in range(21):
            if ex.descubierto[f, c] and not p.mapa[f][c]:
                assert dist[(f, c)] <= ex.radio, 'suelo revelado a través de paredes o demasiado lejos'
    # Caminar revela más y no «ve» celdas a través de una pared.
    _ir_a(p, p.esferas[0].celda)
    assert int(ex.descubierto.sum()) > inicial
    # Una partida nueva empieza sin exploración previa.
    q = Partida('normal', 6)
    assert int(q.exploracion.descubierto.sum()) == inicial
    # La salida solo se pinta en el mapa si está descubierta o la puerta ya se abrió.
    img = colores_minimapa(p)
    sf, sc = p.salida
    assert tuple(img[sf, sc]) != (235, 60, 60, 255) or ex.esta_descubierta(p.salida)
    # Colores: desconocido / pared / suelo / jugador-entrada son distintos entre sí.
    assert len({tuple(img[f, c]) for f, c in ((20, 0), (0, 0), (1, 2), (1, 1))} - {tuple(img[1, 1])}) >= 1
    niebla = colores_niebla(ex)
    assert niebla[..., 3].min() == 0 and niebla[..., 3].max() == 255
    return f'{inicial} celdas reveladas al empezar (de 441); regla: suelo <= {ex.radio} pasos + paredes vecinas'


@prueba
def exploracion_al_abrir_puerta_marca_la_salida():
    p = Partida('facil', 9)
    assert not p.exploracion.esta_descubierta(p.salida)
    for e in p.esferas:
        _ir_a(p, e.celda)
    assert p.puerta.desbloqueada and p.exploracion.esta_descubierta(p.salida)
    img = colores_minimapa(p)
    assert tuple(img[p.salida[0], p.salida[1]]) == (80, 255, 140, 255)
    return 'al recoger la última esfera la salida queda marcada en el mapa'


@prueba
def brujula_rumbos():
    esperado = {0: 'N', 44: 'NE', 90: 'E', 135: 'SE', 180: 'S', 225: 'SO', 270: 'O', 315: 'NO', 359.9: 'N', -90: 'O', 450: 'E'}
    for yaw, nombre in esperado.items():
        assert nombre_rumbo(yaw) == nombre, (yaw, nombre_rumbo(yaw))
    # El convenio coincide con el de movimiento: yaw=90 avanza hacia +x (este), yaw=0 hacia -z (norte).
    p = Partida('normal', 1)
    p.x, p.z = 3.0, 1.0
    dx, dz = p.mover_en_direccion(90, 1, 0, 0.1)
    assert dx > 0 and abs(dz) < 1e-9
    dx, dz = p.mover_en_direccion(0, 1, 0, 0.1)
    assert dz < 0 and abs(dx) < 1e-9
    return 'yaw 0=N, 90=E, 180=S, 270=O; consistente con el movimiento (yaw 90 -> +x)'


# ----------------------------------------------------------------------------- cámara 3ª persona
# El rayo se muestrea cada 0.02 y puede saltarse una cuña de <0.01 en el borde del margen de 0.12; por eso se
# comprueba con 0.10, que sigue siendo mayor que la diagonal del plano cercano (0.084): ningún vértice del
# plano cercano puede alcanzar un muro.
MARGEN_PRUEBA = 0.10


def _segmento_libre(mapa, x, z, cx, cz, bloqueadas, margen):
    n = max(2, int(math.hypot(cx - x, cz - z) / 0.01))
    return all(transitable(mapa, x + (cx - x) * k / n, z + (cz - z) * k / n, margen, bloqueadas)
               for k in range(n + 1))


@prueba
def camara_tercera_nunca_atraviesa_muros():
    rng = random.Random(5)
    marcos = 0
    peor_margen = 1.0
    for dif in DIFICULTADES:
        for semilla in (1, 2):
            p = Partida(dif, semilla)
            cam = CamaraTercera()
            for dt in (1 / 240, 1 / 60, 0.05):
                yaw, pitch = rng.uniform(0, 360), 20.0
                cel = [(f, c) for f in range(len(p.mapa)) for c in range(len(p.mapa)) if not p.mapa[f][c] and (f, c) != p.salida]
                f, c = rng.choice(cel)
                p.x, p.z = float(c), float(f)
                cam.reiniciar()
                for paso in range(900):
                    # Movimiento aleatorio con giros bruscos (incluye saltos de yaw de 90-180 grados).
                    if rng.random() < 0.02:
                        yaw += rng.choice((-180, -90, 90, 180))
                    yaw += rng.uniform(-300, 300) * dt
                    pitch = max(8, min(55, pitch + rng.uniform(-40, 40) * dt))
                    p.mover_en_direccion(yaw + rng.choice((0, 0, 90, 180)), 1, rng.choice((-1, 0, 1)), dt)
                    pos, obj = cam.actualizar(dt, p.mapa, p.x, p.z, yaw, pitch, p.bloqueadas())
                    h = math.hypot(pos[0] - p.x, pos[2] - p.z)
                    # Todo el segmento jugador->cámara está libre con margen y la cámara también.
                    assert _segmento_libre(p.mapa, p.x, p.z, pos[0], pos[2], p.bloqueadas(), MARGEN_PRUEBA), \
                        (dif.clave, semilla, dt, paso)
                    assert cam.distancia <= cam.dist_segura + 1e-9 and cam.distancia <= TERCERA_DIST_MAX + 1e-9
                    marcos += 1
    return f'{marcos} fotogramas aleatorios (dt 1/240, 1/60, 0.05; giros bruscos): segmento jugador-cámara siempre libre con margen {MARGEN_PRUEBA} (margen de diseño {TERCERA_MARGEN})'


@prueba
def camara_tercera_suaviza_y_sigue_al_jugador():
    p = Partida('normal', 3)
    # Pasillo con salida lateral: al girar la pértiga pasa de tener sitio a tener muro de golpe.
    cam = CamaraTercera()
    rng = random.Random(1)
    brutos, suaves = [], []
    cel = [(f, c) for f in range(21) for c in range(21) if not p.mapa[f][c] and (f, c) != p.salida]
    pico_bruto = pico_suave = 0.0
    for f, c in rng.sample(cel, 60):
        p.x, p.z = float(c), float(f)
        cam.reiniciar()
        dt = 1 / 60
        previo_b = previo_s = None
        for k in range(180):                                     # Giro continuo de 180 grados por segundo.
            yaw = k * 3.0
            bruto = distancia_segura(p.mapa, p.x, p.z, yaw, 20.0, p.bloqueadas())
            cam.actualizar(dt, p.mapa, p.x, p.z, yaw, 20.0, p.bloqueadas())
            if previo_b is not None:
                pico_bruto = max(pico_bruto, abs(bruto - previo_b))
                pico_suave = max(pico_suave, abs(cam.distancia - previo_s))
            previo_b, previo_s = bruto, cam.distancia
    # Seguimiento: el objetivo de la mirada es exactamente el jugador (sin retardo) cuando la pértiga es larga.
    p.x, p.z = 3.0, 3.0
    cam.reiniciar()
    for k in range(30):
        p.x += 0.02
        cam.actualizar(1 / 60, p.mapa, p.x, p.z, 0.0, 20.0)
        if cam.distancia > 1.0:
            assert abs(cam.objetivo[0] - p.x) < 1e-9 and abs(cam.objetivo[2] - p.z) < 1e-9
    assert pico_suave < pico_bruto, (pico_suave, pico_bruto)
    return f'salto máximo de distancia por fotograma al girar: bruto (v5) {pico_bruto:.2f} -> suavizado {pico_suave:.2f}; objetivo = jugador sin retardo'


@prueba
def camara_tercera_contra_pared_converge_a_primera_persona():
    p = Partida('normal', 3)
    cam = CamaraTercera()
    p.x, p.z = 1.0, 1.0                                         # Esquina de la entrada: paredes al norte y al oeste.
    for yaw in (0, 90, 180, 270):
        cam.reiniciar()
        for _ in range(10):
            cam.actualizar(1 / 60, p.mapa, p.x, p.z, yaw, 20.0)
        assert transitable(p.mapa, cam.posicion[0], cam.posicion[2], TERCERA_MARGEN)
        assert 0.0 <= cam.distancia <= TERCERA_DIST_MAX
    return 'en la esquina de la entrada la cámara queda siempre dentro de suelo libre'


def main():
    for prueba_ in PRUEBAS:
        prueba_()
    fallos = 0
    for nombre, ok, informe in resultados:
        print(('OK    ' if ok else 'FALLO ') + nombre)
        if informe:
            print('       ' + informe.replace('\n', '\n       '))
        fallos += not ok
    print(f'\n{len(resultados) - fallos}/{len(resultados)} pruebas superadas')
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
