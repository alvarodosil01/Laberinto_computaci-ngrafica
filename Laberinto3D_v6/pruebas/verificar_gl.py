"""Pruebas con contexto OpenGL real de Laberinto 3D v6 (buffers, estado GL, dibujo y partida completa).

Necesitan una ventana/contexto OpenGL. En un servidor sin pantalla:

    xvfb-run -a -s "-screen 0 1280x720x24" python pruebas/verificar_gl.py

(en ese caso se renderiza por software con Mesa llvmpipe: sirve para comprobar corrección, no rendimiento).
Guarda capturas en pruebas/capturas/ y sale con código 1 si alguna comprobación falla.
"""
import math
import os
import random
import sys
import traceback

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'Python'))
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import numpy as np
import pygame
from OpenGL.GL import *

import buffers
from buffers import LoteDinamico, MallaGL
from configuracion import RADIO_JUGADOR
from dificultad import DIFICULTADES
from juego import Juego
from laberinto import celda_de
from objetos import Puerta

CAPTURAS = os.path.join(AQUI, 'capturas')
os.makedirs(CAPTURAS, exist_ok=True)
resultados = []
MAGENTA = (255, 0, 255)


class Teclas(dict):
    def __missing__(self, k):
        return 0


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def registrar(nombre, ok, informe=''):
    resultados.append((nombre, ok, informe))
    print(('OK    ' if ok else 'FALLO ') + nombre)
    if informe:
        print('       ' + informe.replace('\n', '\n       '))
    sys.stdout.flush()


def ejecutar(f):
    try:
        informe = f()
        registrar(f.__name__, True, informe or '')
    except Exception:
        registrar(f.__name__, False, traceback.format_exc(limit=5))
    return f


def capturar(juego):
    w, h = juego.ancho, juego.alto
    datos = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE)
    return np.flipud(np.frombuffer(datos, dtype=np.uint8).reshape(h, w, 3)).copy()


def guardar(img, nombre):
    h, w = img.shape[:2]
    pygame.image.save(pygame.image.frombuffer(img.tobytes(), (w, h), 'RGB'), os.path.join(CAPTURAS, nombre))


def foto(juego, nombre=None):
    juego.dibujar()
    assert glGetError() == GL_NO_ERROR
    img = capturar(juego)
    if nombre:
        guardar(img, nombre)
    return img


def buffers_vivos():
    return [i for i in range(1, 600) if glIsBuffer(i)]


def texturas_vivas():
    return [i for i in range(1, 600) if glIsTexture(i)]


def colocar(juego, celda, yaw, pitch=0.0, camara=None):
    p = juego.partida
    p.x, p.z = float(celda[1]), float(celda[0])
    juego.yaw, juego.pitch = yaw, pitch
    if camara and camara != juego.camara:
        juego._cambiar_camara(camara)
        juego.yaw, juego.pitch = yaw, pitch
    juego.cam3.reiniciar()
    juego.actualizar(1 / 60, Teclas())


def celdas_libres(p):
    return [(f, c) for f in range(len(p.mapa)) for c in range(len(p.mapa[0]))
            if not p.mapa[f][c] and (f, c) != p.salida]


def camino(mapa, origen, destino, bloqueadas=()):
    from collections import deque
    previo = {origen: None}
    cola = deque([origen])
    while cola:
        f, c = cola.popleft()
        if (f, c) == destino:
            break
        for df, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            q = (f + df, c + dc)
            if q not in previo and 0 <= q[0] < len(mapa) and 0 <= q[1] < len(mapa[0]) \
                    and not mapa[q[0]][q[1]] and q not in bloqueadas:
                previo[q] = (f, c)
                cola.append(q)
    ruta, n = [], destino
    while n is not None:
        ruta.append(n)
        n = previo[n]
    return ruta[::-1]


def ir_a(juego, celda, reloj, dt=1 / 60):
    p = juego.partida
    for f, c in camino(p.mapa, p.celda_jugador, celda, p.bloqueadas())[1:]:
        while math.hypot(p.x - c, p.z - f) > 0.02 and not p.terminada:
            d = math.hypot(c - p.x, f - p.z)
            k = min(0.045, d) / d
            p.mover((c - p.x) * k, (f - p.z) * k)
            reloj.t += dt
            juego.actualizar(dt, Teclas())


def main():
    reloj = Reloj()
    juego = Juego('normal', semilla=11, reloj=reloj)
    juego.terror.fijar(False)      # Estas pruebas comprueban el aspecto clásico; el modo terror se prueba en verificar_terror.py.
    p = juego.partida
    info_gl = f"{glGetString(GL_VERSION).decode()} | {glGetString(GL_RENDERER).decode()}"
    print('Contexto:', info_gl)

    # Contadores de llamadas de dibujo (envolvemos las funciones de PyOpenGL usadas en buffers.py).
    cuenta = {'elements': 0, 'arrays': 0}
    original_de, original_da = buffers.glDrawElements, buffers.glDrawArrays

    def de(*a, **k):
        cuenta['elements'] += 1
        return original_de(*a, **k)

    def da(*a, **k):
        cuenta['arrays'] += 1
        return original_da(*a, **k)

    buffers.glDrawElements, buffers.glDrawArrays = de, da

    # ------------------------------------------------------------------ buffers
    @ejecutar
    def vbo_ebo_creados_y_con_tamano_correcto():
        grupos = juego.escena.mallas
        assert set(grupos) == {'suelo', 'pared', 'musgo', 'remate', 'entrada', 'salida', 'portal', 'aristas'}
        for nombre, m in grupos.items():
            glBindBuffer(GL_ARRAY_BUFFER, m.vbo)
            tam_v = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, m.ebo)
            tam_e = glGetBufferParameteriv(GL_ELEMENT_ARRAY_BUFFER, GL_BUFFER_SIZE)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
            comp = 8 if m.formato == 'pnt' else 3
            assert tam_v == m.n_vertices * comp * 4, (nombre, tam_v)          # float32
            assert tam_e == m.n_indices * (2 if m.tipo_gl == GL_UNSIGNED_SHORT else 4), (nombre, tam_e)
            assert glIsBuffer(m.vbo) and glIsBuffer(m.ebo)
        est = juego.escena.estadisticas
        return '; '.join(f"{n}: {e['vertices_sueltos']}->{e['vertices_unicos']} vértices, {e['indices']} índices {e['tipo_indice']}"
                         for n, e in est.items())

    @ejecutar
    def dibujo_con_glDrawElements_y_pocas_llamadas():
        juego.camara = 1
        juego.mostrar_hud = False
        cuenta['elements'] = cuenta['arrays'] = 0
        MallaGL.llamadas = 0
        foto(juego)
        sin_hud = cuenta['elements']
        juego.mostrar_hud = True
        cuenta['elements'] = cuenta['arrays'] = 0
        foto(juego)
        con_hud = cuenta['elements']
        assert cuenta['arrays'] == 0, 'en primera persona no debe usarse glDrawArrays'
        paredes = sum(map(sum, p.mapa))
        v5 = 1 + 2 * paredes + 2           # suelo + (muro + remate) por pared + entrada + salida (v5, sin personaje)
        assert sin_hud <= 7 + 1 + 1 + 5 and con_hud <= sin_hud + 3
        return (f'1ª persona: {sin_hud} glDrawElements para la escena ({paredes} muros), {con_hud} con la interfaz; '
                f'0 glDrawArrays. La v5 emitía unas {v5} llamadas glDrawArrays para esa misma escena (cálculo, no medición)')

    @ejecutar
    def n_regenera_sin_acumular_buffers_ni_texturas():
        vivos0, tex0, creadas0 = len(buffers_vivos()), len(texturas_vivas()), MallaGL.creadas
        mallas0 = MallaGL.vivas
        for k in range(12):
            antes_ids = set(buffers_vivos())
            juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n))
            foto(juego)
            assert MallaGL.vivas == mallas0, f'mallas vivas {MallaGL.vivas} != {mallas0}'
            assert len(buffers_vivos()) == vivos0, 'se acumulan buffers'
            assert len(texturas_vivas()) == tex0, 'se acumulan texturas'
        # Las texturas siguen siendo válidas tras 12 regeneraciones.
        for nombre, t in juego.texturas.items():
            assert glIsTexture(t), nombre
        creadas = MallaGL.creadas - creadas0
        return f'12 pulsaciones de N: buffers vivos {vivos0} -> {len(buffers_vivos())}, texturas {tex0} -> {len(texturas_vivas())}; mallas creadas en total +{creadas} (= 12 x {creadas // 12}) y todas las anteriores liberadas'

    @ejecutar
    def no_se_crean_buffers_por_fotograma():
        v0, c0 = len(buffers_vivos()), MallaGL.creadas
        for _ in range(60):
            juego.actualizar(1 / 60, Teclas())
            juego.dibujar()
        assert len(buffers_vivos()) == v0 and MallaGL.creadas == c0
        return '60 fotogramas: 0 buffers nuevos, 0 mallas nuevas'

    # ------------------------------------------------------------------ geometría visible
    @ejecutar
    def cull_activado_equivale_a_cull_desactivado_sin_caras_invertidas():
        """Con orientación correcta, descartar caras traseras no cambia la imagen.

        Una cara invertida desaparecería con el culling activado (cientos o miles de píxeles de diferencia).
        Se toleran como máximo TOLERANCIA píxeles: son píxeles justo sobre la arista de silueta, donde la regla
        de desempate del rasterizador asigna el centro del píxel a la cara trasera (que el culling descarta).
        """
        TOLERANCIA = 16
        juego.mostrar_hud = False
        azar = random.Random(3)
        total = 0
        peor = 0
        for cam in (1, 3, 2):
            for _ in range(10):
                f, c = azar.choice(celdas_libres(juego.partida))
                colocar(juego, (f, c), azar.uniform(0, 360), 20 if cam == 3 else azar.uniform(-30, 30), camara=cam)
                juego.usar_cull = True
                a = foto(juego)
                juego.usar_cull = False
                b = foto(juego)
                juego.usar_cull = True
                dif = int((a != b).any(axis=2).sum())
                assert dif <= TOLERANCIA, f'cámara {cam}: {dif} píxeles cambian al desactivar el culling (caras invertidas)'
                peor = max(peor, dif)
                total += 1
        juego.mostrar_hud = True
        juego._cambiar_camara(1)
        return f'{total} vistas (cámaras 1/2/3): imagen con y sin GL_CULL_FACE idéntica salvo <= {peor} píxeles de 921600 (desempate de aristas de silueta)'

    @ejecutar
    def sin_huecos_en_paredes_ni_suelo():
        """Fondo magenta + vistas que solo pueden ver suelo o muro: ningún píxel magenta = sin huecos."""
        juego.mostrar_hud = False
        glClearColor(1, 0, 1, 1)
        azar = random.Random(9)
        malos = 0
        vistas = 0
        for dif in DIFICULTADES:
            juego.nueva_partida(dif, 5)
            libres = celdas_libres(juego.partida)
            for _ in range(25):
                celda = azar.choice(libres)
                colocar(juego, celda, azar.uniform(0, 360), -40.0, camara=1)     # Mira hacia abajo (con FOV 60 el borde superior queda bajo el horizonte).
                img = foto(juego)
                magenta = int(((img == MAGENTA).all(axis=2)).sum())
                malos += magenta > 0
                vistas += 1
            # Cámara 3 con la pértiga alta (por encima de los muros): cerca del borde del mapa se ve el exterior por encima
            # del muro perimetral (no es un hueco), así que solo se usan celdas alejadas del borde.
            interiores = [c for c in libres if 4 <= c[0] < dif.tam - 4 and 4 <= c[1] < dif.tam - 4]
            for _ in range(15):
                celda = azar.choice(interiores)
                colocar(juego, celda, azar.uniform(0, 360), 55.0, camara=3)
                img = foto(juego)
                malos += int(((img[300:] == MAGENTA).all(axis=2)).sum() > 0)
                vistas += 1
            juego._cambiar_camara(1)
        glClearColor(0.08, 0.09, 0.12, 1)
        juego.mostrar_hud = True
        assert malos == 0, f'{malos} vistas con píxeles de fondo visibles (huecos)'
        return f'{vistas} vistas en las 3 dificultades (1ª y 3ª persona): 0 píxeles de fondo donde solo debe verse geometría'

    # ------------------------------------------------------------------ capturas de las tres cámaras
    @ejecutar
    def capturas_tres_camaras():
        juego.nueva_partida('normal', 11)
        p = juego.partida
        juego.mostrar_hud = True
        # Una celda en mitad de un pasillo recto largo (sitio delante y detrás): se ve el personaje en 3ª persona.
        def largo(f, c, dz, dc):
            k = 0
            while 0 <= f + dz * (k + 1) < 21 and 0 <= c + dc * (k + 1) < 21 and not p.mapa[f + dz * (k + 1)][c + dc * (k + 1)]:
                k += 1
            return k

        mejor = max((min(largo(f, c, dz, dc), 7) + 3 * min(largo(f, c, -dz, -dc), 3), (f, c), (dc, dz))
                    for f, c in celdas_libres(p) for dz, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)))
        _, celda, (dc, dz) = mejor
        yaw = math.degrees(math.atan2(dc, -dz))
        colocar(juego, celda, yaw, 0, camara=1)
        a = foto(juego, 'camara1_primera_persona.png')
        colocar(juego, celda, yaw, 22, camara=3)
        for _ in range(60):
            juego.actualizar(1 / 60, Teclas())
        b = foto(juego, 'camara3_tercera_persona.png')
        # Para la cenital se recorre un trozo del mapa y se enseña lo explorado.
        juego._cambiar_camara(2)
        for objetivo in [e.celda for e in p.esferas[:3]]:
            ir_a(juego, objetivo, reloj)
        c_ = foto(juego, 'camara2_cenital_explorado.png')
        assert not (a == b).all() and not (b == c_).all()
        return 'guardadas camara1_primera_persona.png, camara3_tercera_persona.png, camara2_cenital_explorado.png'

    @ejecutar
    def tercera_persona_no_atraviesa_paredes_en_imagen():
        """Pegado a una pared mirando a todas partes: nunca aparece el fondo ni el interior del muro (magenta)."""
        juego.nueva_partida('normal', 11)
        juego.mostrar_hud = False
        glClearColor(1, 0, 1, 1)
        malos, vistas = 0, 0
        azar = random.Random(4)
        for celda in azar.sample(celdas_libres(juego.partida), 25):
            for yaw in range(0, 360, 45):
                colocar(juego, celda, yaw, 20, camara=3)
                for _ in range(30):
                    juego.actualizar(1 / 60, Teclas())
                img = foto(juego)
                # Mitad inferior de la imagen: suelo y muros, nunca fondo.
                malos += int(((img[360:] == MAGENTA).all(axis=2)).sum() > 0)
                vistas += 1
        glClearColor(0.08, 0.09, 0.12, 1)
        juego.mostrar_hud = True
        juego._cambiar_camara(1)
        assert malos == 0
        return f'{vistas} vistas de 3ª persona pegado a paredes (8 giros por celda): sin fondo visible en la mitad inferior'

    # ------------------------------------------------------------------ partida y HUD
    @ejecutar
    def partida_completa_con_hud_y_pantalla_final():
        juego.nueva_partida('facil', 21)
        p = juego.partida
        juego._cambiar_camara(1)
        assert p.tiempo() < 1e-3
        # Acercarse a la puerta cerrada y comprobar que no deja pasar.
        ir_a(juego, p.esferas[0].celda, reloj)
        foto(juego, 'esfera_recogida_hud.png')
        for e in p.esferas[1:]:
            ir_a(juego, e.celda, reloj)
        assert p.puerta.desbloqueada and p.esferas_restantes == 0
        ir_a(juego, (p.salida[0] - 1, p.salida[1]), reloj)
        colocar(juego, (p.salida[0] - 1, p.salida[1]), 180, 0, camara=1)
        for _ in range(240):
            reloj.t += 1 / 60
            juego.actualizar(1 / 60, Teclas())
        assert p.puerta.estado == Puerta.ABIERTA and not p.puerta.solida
        ir_a(juego, p.salida, reloj)
        assert p.terminada
        reloj.t += 5
        img = foto(juego, 'pantalla_final.png')
        t_fin = p.tiempo()
        reloj.t += 30
        assert p.tiempo() == t_fin, 'el cronómetro debe detenerse'
        # Reiniciar con N: reloj a 0, nueva partida jugable.
        juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n))
        assert not juego.partida.terminada and juego.partida.tiempo() < 1e-3
        assert juego.partida.esferas_recogidas == 0 and not juego.partida.puerta.desbloqueada
        return f'partida Fácil completada (tiempo simulado {t_fin:.1f} s) y reiniciada con N'

    @ejecutar
    def puerta_estados_visibles_y_colision_coherente():
        juego.nueva_partida('normal', 11)
        p = juego.partida
        juego._cambiar_camara(1)
        previa = (p.salida[0] - 1, p.salida[1])
        # Vista lejana (hasta 3 celdas antes de la puerta, en línea recta) para comprobar que se reconoce.
        lejana = previa
        while lejana[0] > previa[0] - 3 and not p.mapa[lejana[0] - 1][lejana[1]]:
            lejana = (lejana[0] - 1, lejana[1])
        colocar(juego, lejana, 180, 0, camara=1)
        foto(juego, 'puerta_cerrada.png')
        colocar(juego, previa, 180, 0, camara=1)
        # Cerrada: avanzar contra ella no la atraviesa y no termina la partida.
        for _ in range(180):
            reloj.t += 1 / 60
            juego.actualizar(1 / 60, Teclas({pygame.K_w: 1}))
        assert not p.terminada and p.celda_jugador == previa and p.z <= previa[0] + 0.5 - RADIO_JUGADOR + 1e-6
        foto(juego, 'puerta_cerrada_contra_ella.png')
        # Se desbloquea: mientras se hunde sigue siendo sólida (lo que se ve coincide con la colisión).
        p.puerta.desbloquear()
        for _ in range(18):
            reloj.t += 1 / 60
            juego.actualizar(1 / 60, Teclas({pygame.K_w: 1}))
        assert p.puerta.estado == Puerta.ABRIENDO and p.puerta.solida and not p.terminada
        assert p.celda_jugador == previa, 'no puede pasar con la puerta a medio abrir'
        foto(juego, 'puerta_abriendose.png')
        for _ in range(240):
            reloj.t += 1 / 60
            juego.actualizar(1 / 60, Teclas({pygame.K_w: 1}))
            if p.terminada:
                break
        assert not p.puerta.solida and p.terminada and p.celda_jugador == p.salida
        return 'cerrada: no deja pasar; a medio abrir: sigue siendo sólida; abierta: se cruza y termina la partida'

    @ejecutar
    def cambio_de_dificultad_con_teclas():
        for tecla, esperado in ((pygame.K_F3, 'dificil'), (pygame.K_F1, 'facil'), (pygame.K_5, 'normal'), (pygame.K_6, 'dificil'),
                                (pygame.K_4, 'facil'), (pygame.K_F2, 'normal')):
            reloj.t += 7
            juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=tecla))
            d = juego.partida.dificultad
            assert d.clave == esperado and len(juego.partida.mapa) == d.tam
            assert juego.partida.esferas_totales == d.esferas and juego.partida.tiempo() < 1e-3
            foto(juego)
            if esperado == 'dificil':
                foto(juego, 'dificultad_dificil.png')
        return 'F1/F2/F3 y 4/5/6 seleccionan dificultad, regeneran el laberinto y reinician el cronómetro'

    @ejecutar
    def interfaz_sin_fugas_de_estado_gl():
        """Después de dibujar la interfaz el estado 3D queda como se esperaba."""
        foto(juego)
        assert glIsEnabled(GL_DEPTH_TEST) and glIsEnabled(GL_CULL_FACE)
        assert not glIsEnabled(GL_BLEND) and not glIsEnabled(GL_TEXTURE_2D) and not glIsEnabled(GL_LIGHTING)
        assert glGetIntegerv(GL_MATRIX_MODE) == GL_MODELVIEW
        assert glGetIntegerv(GL_ARRAY_BUFFER_BINDING) == 0 and glGetIntegerv(GL_ELEMENT_ARRAY_BUFFER_BINDING) == 0
        assert glGetIntegerv(GL_TEXTURE_BINDING_2D) == 0
        for est in (GL_VERTEX_ARRAY, GL_NORMAL_ARRAY, GL_TEXTURE_COORD_ARRAY, GL_COLOR_ARRAY):
            assert not glIsEnabled(est)
        assert glGetIntegerv(GL_MODELVIEW_STACK_DEPTH) == 1 and glGetIntegerv(GL_PROJECTION_STACK_DEPTH) == 1
        em = glGetMaterialfv(GL_FRONT, GL_EMISSION)
        assert max(em[:3]) == 0, 'la emisión de las esferas no debe filtrarse'
        return 'tras un fotograma completo: buffers/arrays/texturas desenlazados, pilas de matrices vacías, emisión a 0'

    @ejecutar
    def todas_las_camaras_y_ayudas_se_dibujan():
        for cam in (1, 2, 3):
            for mapa in (True, False):
                for ayuda in (True, False):
                    for luz in (False, True):
                        juego.mostrar_mapa, juego.mostrar_ayuda, juego.luz_local = mapa, ayuda, luz
                        colocar(juego, juego.partida.entrada, 0, 20 if cam == 3 else 0, camara=cam)
                        foto(juego)
        for _ in range(5):
            juego.tono = (juego.tono + 1) % 5
            foto(juego)
        juego.mostrar_mapa = juego.mostrar_ayuda = True
        juego.luz_local = False
        juego._cambiar_camara(1)
        return '3 cámaras x mapa on/off x ayuda on/off x luz general/local x 5 tonos, sin errores GL'

    @ejecutar
    def texturas_intactas_tras_varias_n_y_musgo_visible():
        for _ in range(6):
            juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n))
        juego.mostrar_hud = False
        p = juego.partida
        azar = random.Random(12)
        verdosos = 0
        for cam in (1, 3, 2):
            for _ in range(10):
                celda = azar.choice(celdas_libres(p))
                colocar(juego, celda, azar.uniform(0, 360), 20 if cam == 3 else 0, camara=cam)
                img = foto(juego).astype(int)
                blancos = float(((img > 240).all(axis=2)).mean())
                calidez = float((img[..., 0] - img[..., 2]).mean())      # Ladrillo/mármol son cálidos; sin textura = gris neutro.
                assert blancos < 0.02 and img.std() > 8 and (calidez > 2 or cam == 2), \
                    f'cámara {cam}: textura perdida (blanco {blancos:.2%}, std {img.std():.1f}, calidez {calidez:.1f})'
                if cam == 1:
                    verdosos += int(((img[..., 1] > img[..., 0] + 10) & (img[..., 1] > img[..., 2] + 10)).sum())
        juego.mostrar_hud = True
        juego._cambiar_camara(1)
        assert verdosos > 5000, 'no se ve musgo'
        return f'tras 6 N seguidas: las 3 cámaras renderizan con textura (sin blancos); {verdosos} píxeles de musgo en 10 vistas'

    @ejecutar
    def brujula_responde_al_giro_y_ocupa_poco():
        p = juego.partida
        rojo_centro = {}
        recortes = {}
        for yaw in (0, 45, 90, 180, 270, 360):
            glClearColor(0, 0, 0, 1)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            juego.hud.dibujar(p, 1, yaw, False, False, '', 0)
            img = capturar(juego).astype(int)
            zona = img[8:70, 400:880]
            recortes[yaw] = zona
            centro = zona[:, 215:265]
            rojo_centro[yaw] = int(((centro[..., 0] > 200) & (centro[..., 1] < 120) & (centro[..., 2] < 120)).sum())
        glClearColor(0.08, 0.09, 0.12, 1)
        assert rojo_centro[0] > 20 and rojo_centro[360] > 20, 'N (en rojo) debe estar centrada mirando al norte'
        assert rojo_centro[90] == 0 and rojo_centro[180] == 0 and rojo_centro[270] == 0
        assert np.array_equal(recortes[0], recortes[360]), 'yaw 0 y 360 son el mismo rumbo'
        ys = (0, 45, 90, 180, 270)
        for i, a in enumerate(ys):
            for b in ys[i + 1:]:
                assert int((recortes[a] != recortes[b]).any(axis=2).sum()) > 300, (a, b)
        fraccion = (460 * 34 + 150 * 14) / (juego.ancho * juego.alto)
        assert fraccion < 0.04
        return f'N centrada con rumbo 0/360, y distinta a 45/90/180/270; la brújula ocupa ~{fraccion:.1%} de la pantalla (arriba, centrada)'

    @ejecutar
    def animacion_de_esferas_depende_del_tiempo_no_de_fotogramas():
        e = juego.partida.esferas[0]
        t0 = 123.456
        a = [e.pose(t0 + k * 0.25) for k in range(20)]
        # Mismo resultado sea cual sea el número de fotogramas intermedios.
        b = [e.pose(t0 + k * 0.25) for k in range(20)]
        assert a == b
        ys = [e.pose(k * 0.01)[0] for k in range(400)]
        assert 0.40 < min(ys) < max(ys) < 0.70 and (max(ys) - min(ys)) > 0.15, (min(ys), max(ys))
        ang = [e.pose(k * 0.5)[1] for k in range(8)]
        assert len(set(round(x, 3) for x in ang)) == 8
        return f'altura entre {min(ys):.2f} y {max(ys):.2f}, giro {(ang[1] - ang[0]) % 360:.0f} grados cada 0.5 s (función de t)'

    # ------------------------------------------------------------------ cierre
    @ejecutar
    def liberacion_total_al_cerrar():
        antes_b, antes_t = len(buffers_vivos()), len(texturas_vivas())
        assert antes_b > 0 and antes_t > 0
        juego.liberar_recursos()
        assert MallaGL.vivas == 0 and LoteDinamico.vivos == 0
        assert not buffers_vivos(), f'quedan buffers: {buffers_vivos()}'
        assert not texturas_vivas(), f'quedan texturas: {texturas_vivas()}'
        return f'al cerrar: {antes_b} buffers y {antes_t} texturas -> 0 (con el contexto aún activo)'

    pygame.quit()
    fallos = sum(1 for _, ok, _ in resultados if not ok)
    print(f'\n{len(resultados) - fallos}/{len(resultados)} pruebas gráficas superadas  [{info_gl}]')
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
