"""Estado y reglas de una partida (sin OpenGL ni pygame): laberinto, jugador, esferas, puerta, mapa y reloj."""
import math
import random
import time

from configuracion import ESFERA_RADIO_RECOGIDA, FRACCION_MUSGO, RADIO_JUGADOR, VELOCIDAD_JUGADOR
from dificultad import por_clave
from exploracion import Exploracion
from laberinto import alcanzable, celda_de, colocar_esferas, generar, mascara_musgo, transitable
from objetos import Esfera, Puerta


class Partida:
    """Una partida completa. Crear una nueva (N, o cambiar de dificultad) reinicia todo, incluido el reloj."""

    def __init__(self, dificultad, semilla=None, reloj=time.perf_counter):
        if isinstance(dificultad, str):
            dificultad = por_clave(dificultad)
        self.dificultad = dificultad
        self.semilla = random.SystemRandom().randrange(1 << 31) if semilla is None else semilla
        self._reloj = reloj
        for _ in range(50):                      # Salvaguarda: reintenta si el mapa no cumpliese las garantías.
            self.mapa, self.entrada, self.salida = generar(dificultad.tam, dificultad.tam,
                                                           dificultad.aperturas, self.semilla)
            if alcanzable(self.mapa, self.entrada, self.salida):
                break
            self.semilla += 1
        else:
            raise RuntimeError('No se pudo generar un laberinto resoluble')
        azar = random.Random(self.semilla ^ 0x5EED)
        self.puerta = Puerta(self.salida)
        celdas = colocar_esferas(self.mapa, self.entrada, self.salida, dificultad.esferas, azar,
                                 dificultad.separacion_esferas)
        self.esferas = [Esfera(c, azar.uniform(0, 2 * math.pi)) for c in celdas]
        self.musgo = mascara_musgo(self.mapa, azar, FRACCION_MUSGO)
        self.x, self.z = float(self.entrada[1]), float(self.entrada[0])
        self.ruta = [(self.x, self.z)]
        self.exploracion = Exploracion(self.mapa, dificultad.radio_vision)
        self.exploracion.revelar_desde(self.celda_jugador)
        self.t_inicio = self._reloj()
        self.t_final = None
        self.terminada = False
        if not self.esferas:                     # Sin esferas que recoger la puerta nace abierta.
            self.puerta.desbloquear()

    # ---- consultas ----
    @property
    def yaw_inicial(self):
        """Rumbo (grados, 0 = norte, 90 = este) que mira por el pasillo más largo desde la entrada.

        La v5 empezaba siempre mirando al norte, es decir, de cara a un muro.
        """
        f0, c0 = self.entrada
        mejor, yaw = -1, 0.0
        for df, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):
            largo = 0
            while (0 <= f0 + df * (largo + 1) < len(self.mapa) and 0 <= c0 + dc * (largo + 1) < len(self.mapa[0])
                   and not self.mapa[f0 + df * (largo + 1)][c0 + dc * (largo + 1)]):
                largo += 1
            if largo > mejor:
                mejor, yaw = largo, math.degrees(math.atan2(dc, -df)) % 360
        return yaw

    @property
    def celda_jugador(self):
        return celda_de(self.x, self.z)

    @property
    def esferas_totales(self):
        return len(self.esferas)

    @property
    def esferas_restantes(self):
        return sum(1 for e in self.esferas if not e.recogida)

    @property
    def esferas_recogidas(self):
        return self.esferas_totales - self.esferas_restantes

    def tiempo(self):
        """Segundos de partida: corre desde su creación y se congela al completarla."""
        fin = self.t_final if self.t_final is not None else self._reloj()
        return fin - self.t_inicio

    def bloqueadas(self):
        return self.puerta.bloqueadas()

    # ---- movimiento ----
    def mover(self, dx, dz):
        """Aplica un desplazamiento con colisión por ejes (como en la v5), respetando la puerta."""
        if self.terminada:
            return False
        bloqueo = self.bloqueadas()
        movido = False
        if transitable(self.mapa, self.x + dx, self.z, RADIO_JUGADOR, bloqueo):
            self.x += dx
            movido = True
        if transitable(self.mapa, self.x, self.z + dz, RADIO_JUGADOR, bloqueo):
            self.z += dz
            movido = True
        if movido and math.hypot(self.x - self.ruta[-1][0], self.z - self.ruta[-1][1]) >= 0.15:
            self.ruta.append((self.x, self.z))
        return movido

    def mover_en_direccion(self, yaw_grados, avance, lateral, dt):
        """Movimiento relativo a la cámara (WASD). Devuelve (dx, dz) pedidos o (0, 0)."""
        norma = math.hypot(avance, lateral)
        if not norma or self.terminada:
            return 0.0, 0.0
        a = math.radians(yaw_grados)
        dx = (math.sin(a) * avance + math.cos(a) * lateral) * VELOCIDAD_JUGADOR * dt / norma
        dz = (-math.cos(a) * avance + math.sin(a) * lateral) * VELOCIDAD_JUGADOR * dt / norma
        self.mover(dx, dz)
        return dx, dz

    # ---- actualización por fotograma ----
    def actualizar(self, dt):
        """Avanza la puerta, recoge esferas, explora y comprueba la salida. Devuelve lista de eventos."""
        eventos = []
        puerta_estaba_cerrada = not self.puerta.desbloqueada
        self.puerta.actualizar(dt)
        if self.terminada:
            return eventos
        for e in self.esferas:
            if not e.recogida and math.hypot(self.x - e.x, self.z - e.z) <= ESFERA_RADIO_RECOGIDA:
                e.recogida = True
                eventos.append('esfera')
                if self.esferas_restantes == 0:
                    self.puerta.desbloquear()
                    self.exploracion.revelar_celda(self.salida)
                    eventos.append('puerta')
                self.exploracion.version += 1                    # Fuerza el repintado del minimapa.
        if self.exploracion.revelar_desde(self.celda_jugador):
            eventos.append('explorado')
        # La salida solo cuenta cuando la puerta ya no es sólida: coincide con lo que se ve.
        if not self.puerta.solida and self.celda_jugador == self.salida:
            self.terminada = True
            self.t_final = self._reloj()
            eventos.append('salida')
        return eventos
