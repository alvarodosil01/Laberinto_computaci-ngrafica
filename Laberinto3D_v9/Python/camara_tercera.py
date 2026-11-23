"""Cámara en tercera persona con pértiga suavizada y sin atravesar muros (lógica pura, sin OpenGL).

La *dirección de la mirada* y el *objetivo* siguen al jugador sin retardo. Solo se suaviza la
longitud de la pértiga:
  * hacia el jugador (hay un muro detrás): la cámara se acerca rápido pero con curva exponencial;
  * hacia fuera (hay sitio libre): se aleja despacio, sin tirones.
Para que la interpolación nunca permita ver a través de un muro, la longitud final se limita
SIEMPRE por la distancia segura medida ese mismo fotograma sobre la pértiga real (recorte duro).
Además se miden dos rayos laterales (±TERCERA_ABANICO_GRADOS) para anticipar esquinas al girar:
la distancia objetivo ya ha bajado cuando el rayo central llega a la esquina.
Cuando el muro está pegado al jugador, la cámara converge a la posición de primera persona
(punto de vista a la altura de los ojos mirando hacia delante), que siempre está libre.
"""
import math

from configuracion import (RADIO_JUGADOR, TERCERA_ABANICO_GRADOS, TERCERA_DIST_MAX, TERCERA_K_ACERCAR,
                           TERCERA_K_ALEJAR, TERCERA_MARGEN)
from laberinto import transitable

ALTURA_OJOS = 0.85
ALTURA_CAMARA = 1.35
ALTURA_OBJETIVO = 0.75
PASO_RAYO = 0.02
DIST_MIXTA = 1.0          # Por debajo de esta distancia se mezcla con la vista en primera persona.
DIST_PERSONAJE = 0.70     # Por debajo de esta distancia no se dibuja el personaje (la cámara ya es casi de 1ª persona).


def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _pos(x, z, yaw, pitch, d):
    a = math.radians(yaw)
    h = math.cos(math.radians(pitch)) * d
    return x - math.sin(a) * h, z + math.cos(a) * h


def distancia_segura(mapa, x, z, yaw, pitch, bloqueadas=(), margen=TERCERA_MARGEN, maximo=TERCERA_DIST_MAX):
    """Mayor longitud de pértiga d <= maximo tal que todos los puntos de 0..d están libres (con margen)."""
    d = 0.0
    while d + PASO_RAYO <= maximo + 1e-9:
        cx, cz = _pos(x, z, yaw, pitch, d + PASO_RAYO)
        if not transitable(mapa, cx, cz, margen, bloqueadas):
            return d
        d += PASO_RAYO
    return maximo


class CamaraTercera:
    def __init__(self):
        self.distancia = 0.0
        self.posicion = (0.0, ALTURA_OJOS, 0.0)
        self.objetivo = (0.0, ALTURA_OBJETIVO, 0.0)
        self.dist_segura = 0.0
        self.inicializada = False

    def reiniciar(self):
        """Fuerza el ajuste inmediato en el próximo `actualizar` (cambio de cámara, partida nueva)."""
        self.inicializada = False

    def actualizar(self, dt, mapa, x, z, yaw, pitch, bloqueadas=()):
        central = distancia_segura(mapa, x, z, yaw, pitch, bloqueadas)
        objetivo = central
        for lado in (-TERCERA_ABANICO_GRADOS, TERCERA_ABANICO_GRADOS):
            objetivo = min(objetivo, distancia_segura(mapa, x, z, yaw + lado, pitch, bloqueadas))
        if not self.inicializada:
            self.distancia = objetivo
            self.inicializada = True
        else:
            k = TERCERA_K_ACERCAR if objetivo < self.distancia else TERCERA_K_ALEJAR
            self.distancia += (objetivo - self.distancia) * (1 - math.exp(-k * dt))
        self.distancia = max(0.0, min(self.distancia, central))        # Recorte duro: nunca más allá del muro.
        self.dist_segura = central

        d = self.distancia
        cx, cz = _pos(x, z, yaw, pitch, d)
        s = _suave(d / DIST_MIXTA)
        cy = ALTURA_OJOS + (ALTURA_CAMARA - ALTURA_OJOS) * s + math.sin(math.radians(pitch)) * d
        a = math.radians(yaw)
        adelante = (1 - s) * 2.0
        self.posicion = (cx, cy, cz)
        self.objetivo = (x + math.sin(a) * adelante,
                         ALTURA_OJOS + (ALTURA_OBJETIVO - ALTURA_OJOS) * s,
                         z - math.cos(a) * adelante)
        return self.posicion, self.objetivo

    @property
    def dibujar_personaje(self):
        return self.distancia > DIST_PERSONAJE
