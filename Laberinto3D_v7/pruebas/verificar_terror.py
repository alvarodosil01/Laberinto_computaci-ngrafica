"""Pruebas del ambiente de terror (ambiente_terror.py). Necesitan contexto OpenGL:

    xvfb-run -a -s "-screen 0 1280x720x24" python pruebas/verificar_terror.py

Guarda capturas en pruebas/capturas/ (prefijo terror_) y sale con código 1 si algo falla.
"""
import math
import os
import pathlib
import random
import sys
import traceback

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'Python'))
sys.path.insert(0, AQUI)
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import numpy as np
import pygame
from OpenGL.GL import *

import ambiente_terror
import verificar_gl as g                      # Reutiliza las utilidades (capturar, colocar, foto...).
from buffers import LoteDinamico, MallaGL
from configuracion import (TERROR_APAGON_DURACION, TERROR_BALANCEO_AMPLITUD, TERROR_NIEBLA_ALCANCE,
                           TERROR_RESPIRACION_AMPLITUD)
from juego import Juego
from objetos import Puerta

resultados = []


def ejecutar(f):
    try:
        informe = f()
        resultados.append((f.__name__, True, informe or ''))
    except Exception:
        resultados.append((f.__name__, False, traceback.format_exc(limit=5)))
    n, ok, inf = resultados[-1]
    print(('OK    ' if ok else 'FALLO ') + n)
    if inf:
        print('       ' + inf.replace('\n', '\n       '))
    sys.stdout.flush()
    return f


def pasillo_largo(p):
    """Celda y orientación con mucho suelo recto delante y algo detrás."""
    def largo(f, c, dz, dc):
        k = 0
        while 0 <= f + dz * (k + 1) < len(p.mapa) and 0 <= c + dc * (k + 1) < len(p.mapa) \
                and not p.mapa[f + dz * (k + 1)][c + dc * (k + 1)]:
            k += 1
        return k
    _, celda, (dc, dz) = max((min(largo(f, c, dz, dc), 7) + 3 * min(largo(f, c, -dz, -dc), 3), (f, c), (dc, dz))
                             for f, c in g.celdas_libres(p) for dz, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)))
    return celda, math.degrees(math.atan2(dc, -dz)), (dz, dc)


def main():
    reloj = g.Reloj()
    juego = Juego('normal', semilla=11, reloj=reloj)
    T = g.Teclas()
    p = juego.partida
    terror = juego.terror
    print('Contexto:', glGetString(GL_VERSION).decode(), '|', glGetString(GL_RENDERER).decode())
    celda, yaw, (dz, dc) = pasillo_largo(p)

    def vista(cam=1, y=None, pitch=0.0, c=None, hud=False):
        juego.mostrar_hud = hud
        g.colocar(juego, c or celda, yaw if y is None else y, pitch, camara=cam)
        juego.yaw_personaje = juego.yaw
        for _ in range(3):
            juego.actualizar(1 / 60, T)
        return g.foto(juego)

    @ejecutar
    def modo_terror_por_defecto_con_shader():
        assert terror.disponible and terror.activo, 'el modo terror debe estar activo por defecto'
        assert glIsProgram(terror.programa) and glGetProgramiv(terror.programa, GL_LINK_STATUS)
        for k in ('pared', 'musgo', 'suelo', 'remate'):
            assert juego.texturas[k] == terror.terror[k] != terror.clasicas[k]
        return f'shader enlazado; {len(terror.terror)} texturas sucias activas; sonido {"activo" if terror.sonido.activo else "inactivo"}'

    @ejecutar
    def oscuro_con_niebla_y_mucho_menos_luz_que_el_clasico():
        a = vista().astype(float).mean()
        terror.fijar(False)
        b = vista().astype(float).mean()
        terror.fijar(True)
        assert a < 0.45 * b, (a, b)
        return f'brillo medio en 1ª persona: terror {a:.1f} frente a clásico {b:.1f} (sobre 255)'

    @ejecutar
    def linterna_en_cono_con_borde_suave_y_apagable():
        terror.intensidad, terror.linterna = 1.0, True
        # Pegado a un muro lejano: se ve el cono sobre la pared del fondo.
        img = vista().astype(float).mean(axis=2)
        centro = img[260:460, 540:740].mean()
        esquinas = np.mean([img[60:160, 60:160].mean(), img[60:160, -160:-60].mean(),
                            img[-160:-60, 60:160].mean(), img[-160:-60, -160:-60].mean()])
        assert centro > 1.6 * esquinas, (centro, esquinas)
        g.guardar(g.foto(juego), 'terror_camara1_linterna.png')
        terror.linterna = False
        apagada = vista().astype(float).mean()
        g.guardar(g.foto(juego), 'terror_linterna_apagada.png')
        terror.linterna = True
        assert apagada < 0.5 * img.mean() and apagada < 14, apagada
        return f'centro {centro:.0f} / esquinas {esquinas:.0f} con linterna; media {apagada:.1f} con la linterna apagada (tecla I)'

    @ejecutar
    def tecla_i_y_t_alternan_linterna_y_modo():
        juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
        assert terror.linterna is False and juego.luz_local is False, 'en terror, I solo enciende/apaga la linterna'
        juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
        assert terror.linterna is True
        juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t))
        assert not terror.activo and juego.texturas['pared'] == terror.clasicas['pared']
        juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
        assert juego.luz_local is True, 'en clásico, I sigue siendo la luz local de siempre'
        juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
        juego.procesar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t))
        assert terror.activo
        return 'T alterna terror/clásico; I = linterna en terror y luz local en clásico'

    @ejecutar
    def modo_clasico_exacto_tras_alternar_t():
        azar = random.Random(5)
        n = 0
        for cam in (1, 3, 2):
            for _ in range(4):
                c = azar.choice(g.celdas_libres(p))
                y = azar.uniform(0, 360)
                terror.fijar(False)
                a = vista(cam, y, 20 if cam == 3 else 0, c, hud=True)
                terror.fijar(True)
                vista(cam, y, 20 if cam == 3 else 0, c, hud=True)          # Pasar por terror no debe dejar rastro.
                terror.fijar(False)
                b = vista(cam, y, 20 if cam == 3 else 0, c, hud=True)
                assert np.array_equal(a, b), f'cámara {cam}: el modo clásico cambia tras pasar por el terror'
                n += 1
        terror.fijar(True)
        assert terror.balanceo_y() == 0.0 or terror.activo
        return f'{n} vistas (cámaras 1/2/3, con HUD): el clásico es idéntico píxel a píxel antes y después de alternar T'

    @ejecutar
    def cenital_legible_en_terror():
        terror.fijar(False)
        a = vista(2).astype(float).mean()
        terror.fijar(True)
        b = vista(2).astype(float).mean()
        g.guardar(g.foto(juego), 'terror_camara2_cenital.png')
        assert b > 0.55 * a, (a, b)
        return f'brillo medio de la cenital: clásico {a:.1f}, terror {b:.1f} (sin niebla, con más ambiente)'

    @ejecutar
    def hud_no_se_ve_afectado():
        def amarillos():
            img = vista(1, hud=True).astype(int)
            zona = img[10:40, 135:210]                                    # «Normal» en amarillo.
            return int(((zona[..., 0] > 240) & (zona[..., 1] > 200) & (zona[..., 2] < 90)).sum())
        a = amarillos()
        terror.fijar(False)
        b = amarillos()
        terror.fijar(True)
        assert abs(a - b) <= 3 and a > 50, (a, b)      # Solo difieren píxeles de borde del suavizado del texto.
        img = vista(1, hud=True)
        g.guardar(img, 'terror_camara1_con_hud.png')
        return f'texto del HUD con el mismo color y píxeles en ambos modos ({a} píxeles amarillos); viñeta y grano se dibujan antes del HUD'

    @ejecutar
    def esferas_y_portal_emiten_luz_propia():
        terror.linterna = False
        e = p.esferas[0]
        a = math.radians(yaw)
        ox, oz = p.x + math.sin(a) * 2.0, p.z - math.cos(a) * 2.0
        g.colocar(juego, celda, yaw, 0, camara=1)
        e.x, e.z = ox, oz
        juego.mostrar_hud = False
        img = g.foto(juego).astype(int)
        zona = img[300:420, 560:720]
        doradas = int(((zona[..., 0] > 120) & (zona[..., 0] > zona[..., 2] + 40)).sum())
        g.guardar(g.foto(juego), 'terror_esfera_emisiva.png')
        e.x, e.z = float(e.celda[1]), float(e.celda[0])
        assert doradas > 400, f'la esfera no brilla sin linterna ({doradas})'
        # Portal: puerta abierta, vista desde la celda previa, linterna apagada.
        previa = (p.salida[0] - 1, p.salida[1])
        p.puerta.desbloquear()
        for _ in range(240):
            reloj.t += 1 / 60
            juego.actualizar(1 / 60, T)
        g.colocar(juego, previa, 180, 0, camara=1)
        img = g.foto(juego).astype(int)
        verdes = int(((img[..., 1] > 110) & (img[..., 1] > img[..., 0] + 25)).sum())
        g.guardar(g.foto(juego), 'terror_portal_abierto.png')
        terror.linterna = True
        assert verdes > 8000, f'el portal no brilla en verde ({verdes})'
        return f'sin linterna: {doradas} píxeles dorados de la esfera y {verdes} verdes del portal'

    @ejecutar
    def tercera_persona_con_linterna():
        juego.nueva_partida('normal', 11)
        c, y, _ = pasillo_largo(juego.partida)
        g.colocar(juego, c, y, 22, camara=3)
        juego.yaw_personaje = y
        juego.mostrar_hud = True
        for _ in range(60):
            juego.actualizar(1 / 60, T)
        img = g.foto(juego, 'terror_camara3.png').astype(float)
        assert 3 < img.mean() < 90
        juego._cambiar_camara(1)
        return f'3ª persona en terror: brillo medio {img.mean():.1f}'

    @ejecutar
    def parpadeo_apagones_y_rafagas():
        t = ambiente_terror.AmbienteTerror.__new__(ambiente_terror.AmbienteTerror)   # Solo la lógica, sin recursos GL.
        t.__dict__.update(terror.__dict__)
        t.sonido = type('Mudo', (), {'dar_paso': lambda s: None, 'latir': lambda s, *a: None})()
        t._azar = random.Random(1)
        t.t, t._fin_rafaga, t._fin_apagon, t._prox_rafaga = 0.0, -1.0, -1.0, 6.0
        serie = []
        for _ in range(60 * 900):                                           # 15 minutos simulados.
            t.actualizar(1 / 60, False, None)
            serie.append(t.intensidad)
        s = np.array(serie)
        apagado = s == 0.0
        duraciones, n = [], 0
        for v in apagado:
            if v:
                n += 1
            elif n:
                duraciones.append(n / 60)
                n = 0
        assert 3 <= len(duraciones) <= 40, len(duraciones)
        assert min(duraciones) >= TERROR_APAGON_DURACION[0] - 0.05 and max(duraciones) <= TERROR_APAGON_DURACION[1] + 0.05, duraciones
        normales = s[~apagado]
        assert normales.max() <= 1.07 and (normales < 0.6).sum() > 30, 'faltan ráfagas de parpadeo'
        assert np.std(normales[(normales > 0.9)]) > 0.01, 'sin fluctuación continua'
        return (f'15 min simulados: {len(duraciones)} apagones de {min(duraciones):.2f}-{max(duraciones):.2f} s, '
                f'{(normales < 0.6).sum() / 60:.1f} s de parpadeo fuerte, fluctuación continua ±6 %')

    @ejecutar
    def balanceo_de_camara_sutil_y_nulo_en_clasico():
        terror.fijar(True)
        maximo = 0.0
        for _ in range(300):
            terror.actualizar(1 / 60, True, juego)
            maximo = max(maximo, abs(terror.balanceo_y()))
        quieto = [terror.balanceo_y() for _ in range(5)]
        for _ in range(300):
            terror.actualizar(1 / 60, False, juego)
            quieto.append(abs(terror.balanceo_y()))
        assert 0.4 * TERROR_BALANCEO_AMPLITUD < maximo <= TERROR_BALANCEO_AMPLITUD + TERROR_RESPIRACION_AMPLITUD + 1e-9, maximo
        assert max(quieto[-60:]) <= TERROR_RESPIRACION_AMPLITUD + 1e-9
        terror.fijar(False)
        assert terror.balanceo_y() == 0.0
        terror.fijar(True)
        return f'balanceo máximo {maximo:.4f} (amplitud {TERROR_BALANCEO_AMPLITUD}); quieto ≤ {TERROR_RESPIRACION_AMPLITUD}; 0 en clásico'

    @ejecutar
    def texturas_sucias_mismo_tamano_y_teselables():
        import texturas_procedurales as tp
        from ambiente_terror import ensuciar_superficie
        resumen = []
        for clave, sup in (('pared', tp.crear_superficie_pared()), ('musgo', tp.crear_superficie_musgo()),
                           ('suelo', pygame.image.load(os.path.join(AQUI, '..', 'Python', 'texturas', 'granito.png'))),
                           ('remate', pygame.image.load(os.path.join(AQUI, '..', 'Python', 'texturas', 'marmol.png')))):
            sucia = ensuciar_superficie(sup, clave, 1)
            assert sucia.get_size() == sup.get_size()
            a = tp._bytes_a_array(sup).astype(float)
            b = tp._bytes_a_array(sucia).astype(float)
            assert b.mean() < 0.85 * a.mean(), (clave, a.mean(), b.mean())
            sat = lambda x: (x.max(axis=2) - x.min(axis=2)).mean()
            assert sat(b) < sat(a) * 1.05 + 1, (clave, sat(a), sat(b))
            costura = lambda x: np.abs(x[:, 0] - x[:, -1]).mean() / (np.abs(x[:, 20] - x[:, 21]).mean() + 1)
            assert costura(b) < 2.5 * max(costura(a), 1.0), (clave, costura(a), costura(b))
            resumen.append(f'{clave} {a.mean():.0f}->{b.mean():.0f}')
        return 'mismo tamaño, más oscuras, menos saturadas y sin costura al repetir: ' + ', '.join(resumen)

    @ejecutar
    def estado_gl_limpio_en_terror():
        vista(1, hud=True)
        assert glGetIntegerv(GL_CURRENT_PROGRAM) == 0, 'el shader debe quedar desactivado'
        assert glIsEnabled(GL_DEPTH_TEST) and glIsEnabled(GL_CULL_FACE) and glGetBooleanv(GL_DEPTH_WRITEMASK)
        assert not glIsEnabled(GL_BLEND) and not glIsEnabled(GL_TEXTURE_2D) and not glIsEnabled(GL_LIGHTING)
        assert glGetIntegerv(GL_ARRAY_BUFFER_BINDING) == 0 and glGetIntegerv(GL_ELEMENT_ARRAY_BUFFER_BINDING) == 0
        assert glGetIntegerv(GL_TEXTURE_BINDING_2D) == 0
        assert glGetIntegerv(GL_MODELVIEW_STACK_DEPTH) == 1 and glGetIntegerv(GL_PROJECTION_STACK_DEPTH) == 1
        assert max(glGetMaterialfv(GL_FRONT, GL_EMISSION)[:3]) == 0
        for cam in (2, 3, 1):
            vista(cam, pitch=20 if cam == 3 else 0, hud=True)
            assert glGetIntegerv(GL_CURRENT_PROGRAM) == 0 and glGetError() == GL_NO_ERROR
        return 'tras cada fotograma de terror: programa 0, mezcla/textura/iluminación como antes, pilas de matrices equilibradas, sin errores GL'

    @ejecutar
    def todas_las_combinaciones_sin_errores():
        for cam in (1, 2, 3):
            for linterna in (True, False):
                for tono in range(5):
                    terror.linterna, juego.tono = linterna, tono
                    vista(cam, pitch=20 if cam == 3 else 0, hud=True)
        terror.linterna, juego.tono = True, 0
        for dif in ('facil', 'dificil', 'normal'):
            juego.nueva_partida(dif, 3)
            vista(1, c=juego.partida.entrada, hud=True)
        return '3 cámaras x linterna on/off x 5 tonos x 3 dificultades, sin errores'

    @ejecutar
    def fallback_si_el_shader_no_compila():
        original = ambiente_terror.FRAGMENTO
        ambiente_terror.FRAGMENTO = original.replace('void main() {', 'void main() { esto_no_compila;')
        try:
            texturas = dict(juego.texturas)
            t = ambiente_terror.AmbienteTerror(texturas, pathlib.Path(AQUI, '..', 'Python', 'texturas').resolve())
        finally:
            ambiente_terror.FRAGMENTO = original
        assert not t.disponible and not t.activo, 'sin shader debe quedar en modo clásico'
        t.fijar(True)
        assert not t.activo and t.balanceo_y() == 0.0 and not t.luces_fijas(juego) and not t.activo_3d(1)
        t.liberar()
        assert glGetError() == GL_NO_ERROR
        return 'con un shader roto: aviso por consola, modo clásico y ningún error (el juego sigue funcionando)'

    @ejecutar
    def sonido_se_desactiva_solo_sin_audio():
        original_init, original_get = pygame.mixer.init, pygame.mixer.get_init
        pygame.mixer.get_init = lambda: None
        def sin_audio(*a, **k):
            raise pygame.error('sin dispositivo de audio')
        pygame.mixer.init = sin_audio
        try:
            s = ambiente_terror.SonidoTerror()
        finally:
            pygame.mixer.init, pygame.mixer.get_init = original_init, original_get
        assert not s.activo
        s.empezar(), s.dar_paso(), s.latir(1.0, 1.0), s.parar()
        # Con audio (controlador dummy): se pueden reproducir todos los sonidos sin error.
        if terror.sonido.activo:
            terror.sonido.dar_paso(), terror.sonido.latir(1.0, 0.0), terror.sonido.latir(1.0, 1.0)
        return f'sin dispositivo: desactivado sin excepción; con audio dummy: {"sonidos generados y reproducidos" if terror.sonido.activo else "inactivo"}'

    @ejecutar
    def coste_de_los_efectos():
        import time
        juego.mostrar_hud = True
        g.colocar(juego, celda, yaw, 0, camara=1)
        res = {}
        for modo in (False, True):
            terror.fijar(modo)
            for _ in range(5):
                juego.actualizar(1 / 60, T), juego.dibujar()
            glFinish()
            t0 = time.perf_counter()
            for _ in range(60):
                juego.actualizar(1 / 60, T), juego.dibujar()
            glFinish()
            res[modo] = (time.perf_counter() - t0) / 60 * 1000
        terror.fijar(True)
        return f'(Mesa llvmpipe, solo orientativo) clásico {res[False]:.1f} ms/fotograma, terror {res[True]:.1f} ms/fotograma'

    @ejecutar
    def liberacion_total_al_cerrar():
        programa = terror.programa
        juego.liberar_recursos()
        assert not glIsProgram(programa), 'el shader debe borrarse'
        assert MallaGL.vivas == 0 and LoteDinamico.vivos == 0
        assert not g.buffers_vivos() and not g.texturas_vivas(), (g.buffers_vivos(), g.texturas_vivas())
        return 'shader, buffers y texturas (incluidas las 4 sucias, la viñeta, el grano y el halo) liberados: 0 vivos'

    pygame.quit()
    fallos = sum(1 for _, ok, _ in resultados if not ok)
    print(f'\n{len(resultados) - fallos}/{len(resultados)} pruebas de terror superadas')
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
