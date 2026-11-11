"""Geometría estática del laberinto en la GPU (VBO + EBO) y su ciclo de vida.

Qué es estático y vive en buffers entre fotogramas: suelo, paredes (ladrillo y musgo), remates,
marcas de entrada/salida, fondo de la puerta y aristas oscuras. Se construye UNA vez por laberinto
(`construir`) y se libera con `liberar` al generar otro o al cerrar. Lo dinámico (puerta que se
hunde, esferas, personaje, rastro, niebla) se dibuja aparte con transformaciones o buffers propios.

Organización de los grupos de dibujo (una llamada glDrawElements cada uno):
    suelo | pared | musgo | remate | entrada | salida | portal   -> triángulos con textura
    aristas                                                      -> líneas, solo posición
"""
from OpenGL.GL import *

from buffers import MallaGL
from geometria import construir_geometria_estatica

# Grupo -> nombre de la textura con la que se dibuja.
TEXTURA_DE_GRUPO = {'suelo': 'suelo', 'pared': 'pared', 'musgo': 'musgo', 'remate': 'remate',
                    'entrada': 'entrada', 'salida': 'salida', 'portal': 'portal'}
ORDEN_SOLIDOS = ('suelo', 'pared', 'musgo', 'remate', 'entrada', 'salida')


class EscenaEstatica:
    def __init__(self, texturas):
        self.texturas = texturas
        self.mallas = {}
        self.estadisticas = {}          # grupo -> dict con vértices sueltos / únicos / índices.
        self.llamadas_ultimo_dibujo = 0
        self.emision_grupos = {}        # grupo -> color emisivo (lo rellena el modo terror; vacío = aspecto clásico).

    @property
    def construida(self):
        return bool(self.mallas)

    def construir(self, partida):
        """Libera los buffers del laberinto anterior y crea los del actual (contexto GL activo)."""
        self.liberar()
        grupos = construir_geometria_estatica(partida.mapa, partida.salida, partida.entrada, partida.musgo)
        for nombre, (vertices, indices, sueltos) in grupos.items():
            if not len(indices):
                continue
            if nombre == 'aristas':
                self.mallas[nombre] = MallaGL(vertices, indices, modo=GL_LINES, formato='p')
            else:
                self.mallas[nombre] = MallaGL(vertices, indices)
            self.estadisticas[nombre] = {'vertices_sueltos': sueltos, 'vertices_unicos': len(vertices),
                                         'indices': len(indices),
                                         'tipo_indice': str(indices.dtype)}

    def liberar(self):
        for malla in self.mallas.values():
            malla.liberar()
        self.mallas.clear()
        self.estadisticas.clear()

    # ------------------------------------------------------------------ dibujo
    def dibujar_solidos(self, puerta_desbloqueada):
        """Dibuja los grupos con textura. Requiere iluminación activa; restaura todo el estado que toca."""
        llamadas = 0
        glEnable(GL_TEXTURE_2D)
        glColor3f(1, 1, 1)
        for nombre in ORDEN_SOLIDOS:
            malla = self.mallas.get(nombre)
            if malla is None:
                continue
            glBindTexture(GL_TEXTURE_2D, self.texturas[TEXTURA_DE_GRUPO[nombre]])
            self._emision(nombre)
            malla.dibujar()
            self._emision(None)
            llamadas += 1
        if puerta_desbloqueada and 'portal' in self.mallas:
            # El fondo de la puerta brilla (sin iluminación): se ve al abrirla.
            glDisable(GL_LIGHTING)
            glBindTexture(GL_TEXTURE_2D, self.texturas['portal'])
            self._emision('portal')
            self.mallas['portal'].dibujar()
            self._emision(None)
            glEnable(GL_LIGHTING)
            llamadas += 1
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        self.llamadas_ultimo_dibujo = llamadas

    def _emision(self, grupo):
        """Fija (o quita, con None) el material emisivo del grupo, si el modo terror lo ha definido."""
        if self.emision_grupos and (grupo is None or grupo in self.emision_grupos):
            color = self.emision_grupos.get(grupo, (0, 0, 0))
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (*color, 1))

    def dibujar_aristas(self):
        """Líneas oscuras sobre los bordes de los muros (sin luz ni textura)."""
        malla = self.mallas.get('aristas')
        if malla is None:
            return
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glColor3f(0.16, 0.16, 0.16)
        glLineWidth(2)
        malla.dibujar()
        glLineWidth(1)
        glColor3f(1, 1, 1)
        glEnable(GL_LIGHTING)
        self.llamadas_ultimo_dibujo += 1
