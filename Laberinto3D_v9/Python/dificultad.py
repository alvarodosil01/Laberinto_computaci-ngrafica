"""Niveles de dificultad de Laberinto 3D v6.

Todos los parámetros que dependen de la dificultad viven aquí y solo aquí: el resto del
código recibe un objeto `Dificultad` y no contiene números fijos relacionados con ella.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Dificultad:
    clave: str               # Identificador interno ('facil', 'normal', 'dificil').
    nombre: str              # Nombre mostrado en pantalla.
    tam: int                 # Lado del laberinto en celdas (impar y >= 7).
    aperturas: int           # Conexiones extra que abren rutas alternativas (más = más fácil).
    esferas: int             # Esferas que hay que recoger para abrir la puerta.
    radio_vision: int        # Pasos de pasillo que se revelan en el mapa alrededor del jugador (pista).
    separacion_esferas: int  # Distancia Manhattan mínima deseada entre esferas.
    teclas: tuple            # Nombres de tecla de pygame que seleccionan esta dificultad.


DIFICULTADES = (
    Dificultad('facil',   'Fácil',   tam=15, aperturas=16, esferas=3, radio_vision=4,
               separacion_esferas=5, teclas=('F1', '4')),
    Dificultad('normal',  'Normal',  tam=21, aperturas=12, esferas=5, radio_vision=3,
               separacion_esferas=6, teclas=('F2', '5')),
    Dificultad('dificil', 'Difícil', tam=31, aperturas=6,  esferas=8, radio_vision=2,
               separacion_esferas=8, teclas=('F3', '6')),
)
DIFICULTAD_INICIAL = 'normal'


def por_clave(clave):
    for d in DIFICULTADES:
        if d.clave == clave:
            return d
    raise KeyError(f'Dificultad desconocida: {clave!r}. Opciones: {[d.clave for d in DIFICULTADES]}')
