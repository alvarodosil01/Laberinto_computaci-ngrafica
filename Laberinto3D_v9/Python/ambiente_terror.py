"""Ambiente de terror (survival horror): oscuridad, niebla, linterna, texturas sucias, viñeta, grano y sonido.

Es un retoque de atmósfera: no toca la lógica de juego, los buffers ni la geometría. `Juego` solo llama a
unos pocos ganchos (ver los métodos públicos de `AmbienteTerror`). La tecla R alterna entre modo terror y
modo clásico; en modo clásico no se ejecuta nada de este módulo y el aspecto es el de siempre.

Cómo funciona (todo con OpenGL 2.1 en modo compatibilidad):
  * Un único par de shaders GLSL 1.20 sustituye a la iluminación fija al dibujar sólidos y objetos dinámicos
    en 1ª y 3ª persona: luz ambiente mínima + linterna en cono por píxel + niebla exponencial. Usa los atributos
    fijos (gl_Vertex, gl_Normal, gl_MultiTexCoord0, gl_*Matrix), así que los VBO/EBO no cambian.
  * La cámara cenital (2) sigue con la iluminación fija y un ambiente mayor, sin niebla, para leer el mapa.
  * Si el shader no compila o no hay GLSL, se vuelve al modo clásico con un aviso por consola.
"""
import math
import random

import numpy as np
import pygame
from OpenGL.GL import *

from configuracion import (
    TERROR_ACTIVO_AL_INICIO, TERROR_AMBIENTE, TERROR_AMBIENTE_CENITAL, TERROR_APAGON_CADA, TERROR_APAGON_DURACION,
    TERROR_BALANCEO_AMPLITUD, TERROR_BALANCEO_FRECUENCIA, TERROR_COLOR_FONDO, TERROR_EMISION_FACTOR,
    TERROR_EMISION_MARCAS, TERROR_EMISION_PORTAL, TERROR_GRANO, TERROR_GRANO_TAMANO, TERROR_HALO,
    TERROR_HALO_TAMANO, TERROR_LATIDO_BPM, TERROR_LINTERNA_ANGULO_EXT, TERROR_LINTERNA_ANGULO_INT,
    TERROR_LINTERNA_ATEN_CUAD, TERROR_LINTERNA_ATEN_LINEAL, TERROR_LINTERNA_ENCENDIDA, TERROR_LINTERNA_INTENSIDAD,
    TERROR_NIEBLA_ALCANCE, TERROR_PARPADEO_INTERVALO, TERROR_PARPADEO_RAFAGA, TERROR_PARPADEO_RUIDO,
    TERROR_RESPIRACION_AMPLITUD, TERROR_RETRO, TERROR_TEX_DESATURACION, TERROR_TEX_GRIETAS, TERROR_TEX_HOLLIN,
    TERROR_TEX_HUMEDAD, TERROR_TEX_OSCURECER, TERROR_TEX_OXIDO, TERROR_TONOS, TERROR_VINETA, TERROR_VOLUMEN)
from texturas import bytes_superficie, liberar_texturas, textura_desde_array, textura_desde_superficie
from texturas_procedurales import _array_a_superficie, _bytes_a_array, _ruido_periodico, crear_superficie_musgo, \
    crear_superficie_pared

COLOR_FONDO_CLASICO = (0.08, 0.09, 0.12)       # El que usa `_configurar_opengl`.
CLAVES_TEXTURAS = ('pared', 'musgo', 'suelo', 'remate')

VERTICE = """#version 120
varying vec3 pos_ojo;
varying vec3 normal_ojo;
varying vec2 uv;
void main() {
    vec4 p = gl_ModelViewMatrix * gl_Vertex;
    pos_ojo = p.xyz;
    normal_ojo = gl_NormalMatrix * gl_Normal;      // Correcto también con escalado no uniforme.
    uv = gl_MultiTexCoord0.xy;
    gl_Position = gl_ProjectionMatrix * p;
}
"""

FRAGMENTO = """#version 120
uniform sampler2D tex;
uniform vec3  luz_pos;        // Posición de la linterna (espacio del ojo).
uniform vec3  luz_dir;        // Dirección del cono (espacio del ojo, normalizada).
uniform vec2  cono;           // cos(semiángulo exterior), cos(semiángulo interior).
uniform vec3  luz_color;      // Color * intensidad (ya con el parpadeo aplicado).
uniform vec2  aten;           // Atenuación lineal y cuadrática.
uniform vec3  ambiente;
uniform float k_niebla;       // Densidad de la niebla exponencial (exp2).
uniform vec3  color_niebla;
uniform float k_emision;
varying vec3 pos_ojo;
varying vec3 normal_ojo;
varying vec2 uv;
void main() {
    vec3 n = normalize(normal_ojo);
    vec3 v = luz_pos - pos_ojo;
    float d = length(v);
    vec3 l = v / d;
    float spot = smoothstep(cono.x, cono.y, dot(-l, luz_dir));          // Borde suave del cono.
    float att = 1.0 / (1.0 + aten.x * d + aten.y * d * d);
    float lamb = 0.25 + 0.75 * max(dot(n, l), 0.0);                     // Un poco de "wrap" para ver suelos rasantes.
    vec3 base = texture2D(tex, uv).rgb;
    vec3 color = base * (ambiente + luz_color * (spot * att * lamb))
               + base * gl_FrontMaterial.emission.rgb * k_emision;      // Luz propia (esferas, portal, marcas).
    float dist = length(pos_ojo);
    float f = exp(-(k_niebla * dist) * (k_niebla * dist));
    gl_FragColor = vec4(mix(color_niebla, color, f), 1.0);
}
"""


# --------------------------------------------------------------------------------------
# Texturas sucias
# --------------------------------------------------------------------------------------
def ensuciar_superficie(superficie, tipo, semilla):
    """Devuelve una copia oscurecida, desaturada y sucia de `superficie` (mismo tamaño, sigue siendo teselable).

    tipo: 'pared', 'musgo' (hollín en la base y óxido), 'suelo' o 'remate'. Manchas de humedad: ruido periódico;
    grietas: caminos aleatorios que no tocan el borde, para no romper la repetición de la textura.
    """
    rng = np.random.default_rng(semilla)
    a = _bytes_a_array(superficie).astype(np.float64)
    alto, ancho = a.shape[:2]
    musgo = np.clip((a[..., 1] - a[..., 0] - 6) / 30.0, 0, 1)[..., None] if tipo == 'musgo' else 0.0
    lum = (a @ np.array([0.299, 0.587, 0.114]))[..., None]
    a = (lum + (a - lum) * (1 - TERROR_TEX_DESATURACION)) * TERROR_TEX_OSCURECER
    if tipo == 'musgo':                                          # Musgo más oscuro y verdoso.
        a = a * (1 - 0.35 * musgo) + musgo * np.array([-4.0, 9.0, 2.0])
    ruido = 0.6 * _ruido_periodico(rng, alto, ancho, 5, 3) + 0.4 * _ruido_periodico(rng, alto, ancho, 12, 7)
    humedad = (np.clip((ruido - 0.5) / 0.25, 0, 1) * TERROR_TEX_HUMEDAD)[..., None]
    a = a * (1 - 0.55 * humedad) + humedad * np.array([6.0, 13.0, 15.0])
    if tipo in ('pared', 'musgo'):
        y = np.linspace(0, 1, alto)[:, None]                    # 0 arriba, 1 en la base (suelo).
        hollin = np.clip((y - 0.55) / 0.45, 0, 1) ** 1.4 * (0.6 + 0.4 * _ruido_periodico(rng, alto, ancho, 8, 6))
        a *= (1 - np.clip(hollin * TERROR_TEX_HOLLIN * 1.4, 0, 0.9))[..., None]
        vetas = _ruido_periodico(rng, alto, ancho, 2, 28)       # Pocas filas, muchas columnas: vetas verticales.
        oxido = (np.clip((vetas - 0.62) / 0.15, 0, 1) * (0.4 + 0.6 * y) * TERROR_TEX_OXIDO)[..., None]
        a = a * (1 - oxido) + oxido * np.array([70.0, 36.0, 16.0])
    for _ in range(TERROR_TEX_GRIETAS):                          # Grietas y rayones.
        x, yy = rng.uniform(10, ancho - 10), rng.uniform(10, alto - 10)
        ang = rng.uniform(0, 2 * math.pi)
        for _paso in range(int(rng.integers(30, 110))):
            ang += rng.normal(0, 0.35)
            x, yy = x + math.cos(ang) * 1.2, yy + math.sin(ang) * 1.2
            if not (3 <= x < ancho - 3 and 3 <= yy < alto - 3):
                break
            a[int(yy), int(x)] *= 0.30
            a[int(yy) + 1, int(x)] *= 0.75
    return _array_a_superficie(np.clip(a, 0, 255))


# --------------------------------------------------------------------------------------
# Sonido (generado con NumPy; se desactiva solo si no hay audio)
# --------------------------------------------------------------------------------------
class SonidoTerror:
    def __init__(self):
        self.activo = False
        self._prox_latido = 0.0
        if TERROR_VOLUMEN <= 0:
            return
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(22050, -16, 2, 512)
            frecuencia, formato, canales = pygame.mixer.get_init()
            if formato != -16 or canales not in (1, 2):
                raise pygame.error('formato de audio no soportado')
            self.frecuencia, self.canales = frecuencia, canales
            t = np.arange(int(2.0 * frecuencia)) / frecuencia                  # 2 s: ciclos enteros -> bucle sin clic.
            zumbido = (np.sin(2 * math.pi * 50 * t) + 0.5 * np.sin(2 * math.pi * 100 * t + 0.7)
                       + 0.25 * np.sin(2 * math.pi * 150 * t + 1.9)) * (0.8 + 0.2 * np.sin(2 * math.pi * 0.5 * t))
            self.zumbido = self._sonido(zumbido * 0.10)
            rng = np.random.default_rng(7)
            n = int(0.20 * frecuencia)
            ruido = np.convolve(rng.normal(0, 1, n), np.ones(24) / 24, mode='same')    # Ruido grave.
            self.paso = self._sonido(ruido * np.exp(-np.arange(n) / (0.05 * frecuencia)) * 0.9)
            n = int(0.7 * frecuencia)
            tt = np.arange(n) / frecuencia
            latido = sum(np.sin(2 * math.pi * 55 * np.clip(tt - t0, 0, None)) * np.exp(-np.clip(tt - t0, 0, None) * 18)
                         * (tt >= t0) * a for t0, a in ((0.0, 1.0), (0.24, 0.75)))
            self.latido = self._sonido(latido * 0.9)
            self.canal_zumbido = None
            self.activo = True
        except Exception as e:                  # Sin dispositivo de audio, sin numpy en mixer, etc.
            print(f'[ambiente_terror] Sonido desactivado: {e}')

    def _sonido(self, onda):
        onda = np.clip(onda * 32767, -32768, 32767).astype(np.int16)
        if self.canales == 2:
            onda = np.repeat(onda[:, None], 2, axis=1)
        s = pygame.sndarray.make_sound(np.ascontiguousarray(onda))
        s.set_volume(TERROR_VOLUMEN)
        return s

    def empezar(self):
        if self.activo and self.canal_zumbido is None:
            self.canal_zumbido = self.zumbido.play(-1)

    def parar(self):
        if self.activo:
            pygame.mixer.stop()
            self.canal_zumbido = None

    def dar_paso(self):
        if self.activo:
            self.paso.play()

    def latir(self, dt, oscuridad):
        """Latido cuya frecuencia y volumen aumentan con la oscuridad (0 = linterna encendida, 1 = apagada)."""
        if not self.activo:
            return
        self._prox_latido -= dt
        if self._prox_latido <= 0:
            bpm = TERROR_LATIDO_BPM[0] + (TERROR_LATIDO_BPM[1] - TERROR_LATIDO_BPM[0]) * oscuridad
            self._prox_latido = 60.0 / bpm
            self.latido.set_volume(TERROR_VOLUMEN * (0.25 + 0.75 * oscuridad))
            self.latido.play()


# --------------------------------------------------------------------------------------
# Ambiente
# --------------------------------------------------------------------------------------
class AmbienteTerror:
    def __init__(self, texturas, carpeta_texturas):
        """`texturas` es el diccionario vivo de Juego (se sustituyen en él las 4 texturas sucias al activar el modo)."""
        self.texturas = texturas
        self.activo = False
        self.disponible = False
        self.linterna = TERROR_LINTERNA_ENCENDIDA
        self.programa = None
        self._u = {}
        self.t = 0.0
        self.intensidad = 1.0                    # Factor de parpadeo actual (0 = apagón).
        self._azar = random.Random()
        self._prox_rafaga = self._azar.uniform(*TERROR_PARPADEO_INTERVALO)
        self._fin_rafaga = self._fin_apagon = -1.0
        self._valor_rafaga, self._cambio_rafaga = 1.0, 0.0
        self._fase_paso, self._moviendo, self._oscuridad = 0.0, 0.0, 0.0
        self._respiracion = 0.0
        self.sonido = SonidoTerror()
        self.clasicas = {k: texturas[k] for k in CLAVES_TEXTURAS}
        self.terror = {}
        self._texturas_extra = []
        try:
            self.programa = self._compilar(VERTICE, FRAGMENTO)
            self._crear_texturas(carpeta_texturas)
            self.disponible = True
        except Exception as e:                   # Nunca debe romper el juego: se queda en modo clásico.
            print(f'[ambiente_terror] No disponible, se usa el modo clásico: {e}')
        f = TERROR_EMISION_FACTOR
        self.emision_grupos_terror = {'portal': tuple(v / f for v in TERROR_EMISION_PORTAL),
                                      'entrada': tuple(v / f for v in TERROR_EMISION_MARCAS),
                                      'salida': tuple(v / f for v in TERROR_EMISION_MARCAS)}
        self.fijar(TERROR_ACTIVO_AL_INICIO)

    # ------------------------------------------------------------------ recursos
    @staticmethod
    def _compilar(fuente_v, fuente_f):
        if not bool(glCreateShader):
            raise RuntimeError('este controlador no ofrece GLSL')
        partes = []
        for tipo, fuente in ((GL_VERTEX_SHADER, fuente_v), (GL_FRAGMENT_SHADER, fuente_f)):
            sh = glCreateShader(tipo)
            glShaderSource(sh, fuente)
            glCompileShader(sh)
            if not glGetShaderiv(sh, GL_COMPILE_STATUS):
                raise RuntimeError('shader no compila: ' + str(glGetShaderInfoLog(sh)))
            partes.append(sh)
        programa = glCreateProgram()
        for sh in partes:
            glAttachShader(programa, sh)
        glLinkProgram(programa)
        for sh in partes:
            glDeleteShader(sh)
        if not glGetProgramiv(programa, GL_LINK_STATUS):
            raise RuntimeError('shader no enlaza: ' + str(glGetProgramInfoLog(programa)))
        return programa

    def _crear_texturas(self, carpeta):
        fuentes = {'pared': crear_superficie_pared(), 'musgo': crear_superficie_musgo(),
                   'suelo': pygame.image.load(str(carpeta / 'granito.png')),
                   'remate': pygame.image.load(str(carpeta / 'marmol.png'))}
        for i, (clave, sup) in enumerate(fuentes.items()):
            tex = textura_desde_superficie(ensuciar_superficie(sup, clave, 100 + i), mipmaps=True)
            if TERROR_RETRO:                                      # Píxeles visibles al acercarse.
                glBindTexture(GL_TEXTURE_2D, tex)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                glBindTexture(GL_TEXTURE_2D, 0)
            self.terror[clave] = tex
        # Viñeta (alfa negro creciente hacia los bordes), grano (gris aleatorio) y halo (degradado radial).
        y, x = np.mgrid[-1:1:256j, -1:1:256j]
        r = np.clip(np.sqrt(x * x + y * y) / 1.2, 0, 1)
        vineta = np.zeros((256, 256, 4), np.uint8)
        vineta[..., 3] = (np.clip((r - 0.35) / 0.65, 0, 1) ** 1.8 * TERROR_VINETA * 255).astype(np.uint8)
        # Grano con muchos granos oscuros y pocos claros (u^2.5): casi no levanta el negro de la oscuridad.
        ruido = (255 * np.random.default_rng(3).random((128, 128, 1)) ** 2.5).astype(np.uint8)
        grano = np.concatenate([np.repeat(ruido, 3, axis=2), np.full((128, 128, 1), int(TERROR_GRANO * 255), np.uint8)], axis=2)
        rr = np.clip(np.sqrt(x * x + y * y), 0, 1)
        halo = np.full((256, 256, 4), 255, np.uint8)
        halo[..., 3] = ((1 - rr) ** 2.5 * 255).astype(np.uint8)
        self.tex_vineta = textura_desde_array(vineta, nearest=False)
        self.tex_grano = textura_desde_array(grano, nearest=True, repetir=True)
        self.tex_halo = textura_desde_array(halo, nearest=False)
        self._texturas_extra = [self.tex_vineta, self.tex_grano, self.tex_halo]

    def liberar(self):
        """Libera shader y texturas propias (el contexto debe estar activo). Restaura las texturas clásicas en el diccionario."""
        self.texturas.update(self.clasicas)                      # Las clásicas las libera Juego.
        liberar_texturas(list(self.terror.values()) + self._texturas_extra)
        self.terror, self._texturas_extra = {}, []
        if self.programa:
            glDeleteProgram(self.programa)
            self.programa = None
        self.sonido.parar()
        self.disponible = self.activo = False

    # ------------------------------------------------------------------ modo
    def fijar(self, activo):
        """Activa o desactiva el modo terror. Sin shader disponible se queda en clásico."""
        if activo and not self.disponible:
            print('[ambiente_terror] Modo terror no disponible en este equipo: se mantiene el modo clásico.')
            activo = False
        self.activo = bool(activo)
        self.texturas.update(self.terror if self.activo else self.clasicas)
        if self.activo:
            self.sonido.empezar()
        else:
            glClearColor(*COLOR_FONDO_CLASICO, 1)
            self.sonido.parar()

    def activo_3d(self, camara):
        """True si en esta cámara se usa el aspecto de terror con shader (1ª y 3ª persona)."""
        return self.activo and camara != 2

    def tecla(self, tecla, juego):
        """Gancho de teclado. Devuelve True si la tecla se ha consumido (R siempre; E, la linterna, solo en modo terror)."""
        if tecla == pygame.K_r:
            self.fijar(not self.activo)
            juego._avisar('Modo terror' if self.activo else 'Modo clásico')
            return True
        if tecla == pygame.K_e and self.activo:
            self.linterna = not self.linterna
            juego._avisar('Linterna encendida' if self.linterna else 'Linterna apagada')
            return True
        if tecla == pygame.K_i and self.activo:     # I es la luz local del modo clásico: sin efecto en terror.
            return True
        return False

    # ------------------------------------------------------------------ simulación
    def actualizar(self, dt, caminando, juego):
        """Parpadeo de la linterna, balanceo de cámara y sonidos. Se llama una vez por fotograma de simulación."""
        self.t += dt
        if not self.activo:
            return
        # Parpadeo: ruido continuo + ráfagas ocasionales + apagón muy raro.
        t = self.t
        ruido = 0.5 * math.sin(37.1 * t) + 0.3 * math.sin(61.7 * t + 1.3) + 0.2 * math.sin(13.9 * t + 0.4)
        factor = 1.0 + TERROR_PARPADEO_RUIDO * ruido
        if t >= self._prox_rafaga:
            self._fin_rafaga = t + TERROR_PARPADEO_RAFAGA
            self._prox_rafaga = self._fin_rafaga + self._azar.uniform(*TERROR_PARPADEO_INTERVALO)
        if t < self._fin_rafaga:
            if t >= self._cambio_rafaga:                         # Cambia el nivel cada ~40 ms: parpadeo nervioso.
                self._valor_rafaga = self._azar.choice((0.05, 0.2, 0.5, 0.9, 1.0))
                self._cambio_rafaga = t + 0.04
            factor *= self._valor_rafaga
        if TERROR_APAGON_CADA > 0 and t >= self._fin_apagon and self._azar.random() < dt / TERROR_APAGON_CADA:
            self._fin_apagon = t + self._azar.uniform(*TERROR_APAGON_DURACION)
        if t < self._fin_apagon:
            factor = 0.0
        self.intensidad = factor
        # Balanceo al caminar / respiración al estar quieto; un paso suena cada vez que la fase cruza un múltiplo de pi.
        self._moviendo += ((1.0 if caminando else 0.0) - self._moviendo) * min(1.0, dt * 8)
        previa = self._fase_paso
        if caminando:
            self._fase_paso += 2 * math.pi * TERROR_BALANCEO_FRECUENCIA * dt / 2
            if int(previa / math.pi) != int(self._fase_paso / math.pi):
                self.sonido.dar_paso()
        # Latido: más rápido cuanto más oscuro (linterna apagada o en apagón).
        objetivo = 1.0 if (not self.linterna or factor < 0.2) else 0.0
        self._oscuridad += (objetivo - self._oscuridad) * min(1.0, dt * 1.5)
        self.sonido.latir(dt, self._oscuridad)

    def balanceo_y(self):
        """Desplazamiento vertical (unidades) del ojo en 1ª persona. 0 en modo clásico."""
        if not self.activo:
            return 0.0
        paso = abs(math.sin(self._fase_paso)) * TERROR_BALANCEO_AMPLITUD * self._moviendo
        respira = math.sin(2 * math.pi * 0.27 * self.t) * TERROR_RESPIRACION_AMPLITUD * (1 - self._moviendo)
        return paso + respira

    # ------------------------------------------------------------------ dibujo
    def antes_de_limpiar(self, camara):
        """Color de fondo (= color de la niebla) en modo terror 1ª/3ª; en la cenital se mantiene el clásico."""
        if self.activo:
            glClearColor(*(TERROR_COLOR_FONDO if camara != 2 else COLOR_FONDO_CLASICO), 1)

    def _tono(self, juego):
        return TERROR_TONOS[juego.tono % len(TERROR_TONOS)]

    def luces_fijas(self, juego):
        """Gancho de `_aplicar_luces`. En modo terror con cámara cenital fija una iluminación suave y devuelve True;
        en 1ª/3ª persona (shader) también devuelve True para saltarse la iluminación clásica; en modo clásico, False."""
        if not self.activo:
            return False
        if juego.camara == 2:
            color = self._tono(juego)
            glEnable(GL_LIGHT0)
            glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (*(v * TERROR_AMBIENTE_CENITAL for v in color), 1))
            glLightfv(GL_LIGHT0, GL_AMBIENT, (0, 0, 0, 1))
            glLightfv(GL_LIGHT0, GL_DIFFUSE, (*(v * 0.45 for v in color), 1))
            glLightfv(GL_LIGHT0, GL_POSITION, (0.4, 1, 0.5, 0))
            glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0)
            glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0)
            glDisable(GL_LIGHT1)
        return True

    def _linterna_en_ojo(self, juego):
        """Posición y dirección de la linterna en el espacio del ojo (la matriz de vista ya está cargada)."""
        p = juego.partida
        if juego.camara == 3:                                     # Sale de la cabeza del personaje, hacia donde mira.
            a = math.radians(juego.yaw_personaje)
            pos = (p.x + math.sin(a) * 0.15, 0.95, p.z - math.cos(a) * 0.15)
            dire = (math.sin(a), -0.20, -math.cos(a))      # Algo inclinada hacia abajo: ilumina el suelo ante el personaje.
        else:                                                     # Linterna en mano, siguiendo la mirada (yaw/pitch).
            a, inc = math.radians(juego.yaw), math.radians(juego.pitch)
            dire = (math.sin(a) * math.cos(inc), math.sin(inc), -math.cos(a) * math.cos(inc))
            derecha = (math.cos(a), 0.0, math.sin(a))
            pos = (p.x + derecha[0] * 0.12, 0.85 + self.balanceo_y() - 0.10, p.z + derecha[2] * 0.12)
        m = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float64).reshape(4, 4)   # m[columna][fila]
        pos_o = np.array([*pos, 1.0]) @ m
        dir_o = np.array([*dire, 0.0]) @ m
        return pos_o[:3], dir_o[:3] / np.linalg.norm(dir_o[:3])

    def empezar_escena(self, juego):
        """Gancho antes de dibujar sólidos y dinámicos: activa el shader en 1ª/3ª persona (si no, no hace nada)."""
        juego.escena.emision_grupos = self.emision_grupos_terror if self.activo_3d(juego.camara) else {}
        if not self.activo_3d(juego.camara):
            return
        pos, dire = self._linterna_en_ojo(juego)
        color = self._tono(juego)
        potencia = TERROR_LINTERNA_INTENSIDAD * self.intensidad * (1.0 if self.linterna else 0.0)
        glUseProgram(self.programa)
        u = self._u
        def loc(nombre):
            if nombre not in u:
                u[nombre] = glGetUniformLocation(self.programa, nombre)
            return u[nombre]
        glUniform1i(loc('tex'), 0)
        glUniform3f(loc('luz_pos'), *pos)
        glUniform3f(loc('luz_dir'), *dire)
        glUniform2f(loc('cono'), math.cos(math.radians(TERROR_LINTERNA_ANGULO_EXT)),
                    math.cos(math.radians(TERROR_LINTERNA_ANGULO_INT)))
        glUniform3f(loc('luz_color'), *(c * potencia for c in color))
        glUniform2f(loc('aten'), TERROR_LINTERNA_ATEN_LINEAL, TERROR_LINTERNA_ATEN_CUAD)
        glUniform3f(loc('ambiente'), *(c * TERROR_AMBIENTE for c in color))
        glUniform1f(loc('k_niebla'), math.sqrt(3.0) / TERROR_NIEBLA_ALCANCE)   # exp(-(k d)^2) = 5 % en d = alcance.
        glUniform3f(loc('color_niebla'), *TERROR_COLOR_FONDO)
        glUniform1f(loc('k_emision'), TERROR_EMISION_FACTOR)

    def terminar_escena(self, juego):
        """Gancho tras sólidos y dinámicos: desactiva el shader y dibuja los halos de las esferas."""
        if not self.activo_3d(juego.camara):
            return
        glUseProgram(0)
        if not TERROR_HALO:
            return
        m = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float64).reshape(4, 4)
        derecha, arriba = m[:3, 0] * TERROR_HALO_TAMANO / 2, m[:3, 1] * TERROR_HALO_TAMANO / 2
        cull = glIsEnabled(GL_CULL_FACE)
        glDisable(GL_CULL_FACE)
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)                          # Aditivo.
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.tex_halo)
        glBegin(GL_QUADS)
        for e in juego.partida.esferas:
            if e.recogida:
                continue
            y, _ = e.pose(juego.t_anim)
            c = np.array([e.x, y, e.z])
            glColor4f(1.0, 0.72, 0.22, 0.55 + 0.15 * math.sin(4.0 * juego.t_anim + e.fase))
            for (sx, sy), uv in zip(((-1, -1), (1, -1), (1, 1), (-1, 1)), ((0, 0), (1, 0), (1, 1), (0, 1))):
                glTexCoord2f(*uv)
                glVertex3f(*(c + derecha * sx + arriba * sy))
        glEnd()
        glColor4f(1, 1, 1, 1)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glDepthMask(GL_TRUE)
        if cull:
            glEnable(GL_CULL_FACE)

    def dibujar_efectos(self, juego):
        """Viñeta y grano de película a pantalla completa (antes del HUD, que no se ve afectado). Solo 1ª/3ª persona."""
        if not self.activo_3d(juego.camara):
            return
        W, H = juego.ancho, juego.alto
        cull = glIsEnabled(GL_CULL_FACE)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, W, H, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glColor4f(1, 1, 1, 1)
        capas = [(self.tex_vineta, 0.0, 0.0, 1.0, 1.0)]
        if TERROR_GRANO > 0:
            escala = TERROR_GRANO_TAMANO
            du, dv = self._azar.random(), self._azar.random()     # Desplazamiento aleatorio por fotograma.
            capas.append((self.tex_grano, du, dv, W / (128.0 * escala) + du, H / (128.0 * escala) + dv))
        for textura, u0, v0, u1, v1 in capas:
            glBindTexture(GL_TEXTURE_2D, textura)
            glBegin(GL_QUADS)
            for x, y, u, v in ((0, 0, u0, v0), (W, 0, u1, v0), (W, H, u1, v1), (0, H, u0, v1)):
                glTexCoord2f(u, v)
                glVertex2f(x, y)
            glEnd()
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

