"""Modelo OBJ dibujado con VBO + EBO (glDrawElements).

Mantiene la interfaz del `Modelo` de la v5 (constructor con ruta, `dibujar(textura, t_x, ...)` y
`liberar()`), pero ahora el OBJ se convierte con `obj.cargar_obj`, que comparte vértices idénticos
y genera un array de índices para el EBO.
"""
from OpenGL.GL import *

from buffers import MallaGL
from obj import cargar_obj
from transformaciones import transformar


class Modelo:
    """Carga un .obj una vez y lo dibuja las veces que haga falta con distintas transformaciones."""

    def __init__(self, ruta, draw_type=GL_TRIANGLES):
        self.ruta = ruta
        vertices, indices, sueltos = cargar_obj(ruta)
        self.vertices_sueltos = sueltos          # Esquinas de triángulo del OBJ (lo que usaría glDrawArrays).
        self.n_vertices = len(vertices)          # Vértices únicos que acaban en el VBO.
        self.n_indices = len(indices)
        self.malla = MallaGL(vertices, indices, modo=draw_type)

    def dibujar(self, textura_id, t_x=0, t_y=0, t_z=0, angulo=0, eje_x=0, eje_y=0, eje_z=0,
                sx=1, sy=1, sz=1):
        """Traslada, rota y escala (en ese orden) y dibuja con la textura indicada."""
        transformar(t_x, t_y, t_z, angulo, eje_x, eje_y, eje_z, sx, sy, sz,
                    lambda: self._dibujar_objeto(textura_id))

    def _dibujar_objeto(self, textura_id):
        glEnable(GL_NORMALIZE)                    # Necesario con escalado no uniforme.
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, textura_id)
        self.malla.dibujar()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

    def liberar(self):
        self.malla.liberar()
