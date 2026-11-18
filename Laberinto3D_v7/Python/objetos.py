"""Lógica (sin OpenGL) de los objetos dinámicos: esferas coleccionables y puerta de salida."""
import math

from configuracion import (ALTURA_PARED, ALTURA_REMATE, ESFERA_AMPLITUD, ESFERA_ESCALA,
                           ESFERA_FRECUENCIA, ESFERA_VEL_ROTACION, ESFERA_Y_BASE,
                           PUERTA_UMBRAL, PUERTA_VELOCIDAD)


class Esfera:
    """Coleccionable situado en el centro de una celda transitable. No es un obstáculo."""

    def __init__(self, celda, fase):
        self.celda = celda
        self.x, self.z = float(celda[1]), float(celda[0])
        self.fase = fase                 # Desfase en radianes para que no se muevan al unísono.
        self.recogida = False

    def pose(self, t):
        """(altura del centro, ángulo de giro en grados) en el instante t (segundos).

        Depende solo del tiempo transcurrido t, nunca del número de fotogramas.
        """
        y = ESFERA_Y_BASE + ESFERA_AMPLITUD * math.sin(2 * math.pi * ESFERA_FRECUENCIA * t + self.fase)
        angulo = (ESFERA_VEL_ROTACION * t + math.degrees(self.fase)) % 360.0
        return y, angulo


class Puerta:
    """Puerta de salida: CERRADA -> ABRIENDO -> ABIERTA.

    Es un bloque que ocupa toda su celda. Al desbloquearse se hunde en el suelo; mientras su parte
    superior esté por encima de PUERTA_UMBRAL la celda es sólida (colisión) y, en cuanto baja de ese
    umbral, deja de serlo. Así lo que se ve coincide con lo que se puede atravesar.
    """
    CERRADA, ABRIENDO, ABIERTA = 'cerrada', 'abriendo', 'abierta'
    ALTURA = ALTURA_PARED + ALTURA_REMATE
    HUNDIMIENTO_FINAL = ALTURA + 0.06      # Queda por debajo del suelo (no coplanar con él).

    def __init__(self, celda):
        self.celda = celda
        self.estado = Puerta.CERRADA
        self.hundimiento = 0.0

    @property
    def desbloqueada(self):
        return self.estado != Puerta.CERRADA

    @property
    def altura_superior(self):
        """Altura sobre el suelo de la cara superior de la puerta."""
        return self.ALTURA - self.hundimiento

    @property
    def solida(self):
        return self.altura_superior > PUERTA_UMBRAL

    def bloqueadas(self):
        """Conjunto de celdas bloqueadas que hay que pasar a las colisiones."""
        return frozenset((self.celda,)) if self.solida else frozenset()

    def desbloquear(self):
        if self.estado == Puerta.CERRADA:
            self.estado = Puerta.ABRIENDO

    def actualizar(self, dt):
        if self.estado == Puerta.ABRIENDO:
            self.hundimiento = min(self.HUNDIMIENTO_FINAL, self.hundimiento + PUERTA_VELOCIDAD * dt)
            if self.hundimiento >= self.HUNDIMIENTO_FINAL:
                self.estado = Puerta.ABIERTA

    @property
    def visible(self):
        return self.estado != Puerta.ABIERTA
