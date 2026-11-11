"""Objetos de buffer de OpenGL: VBO + EBO para geometría estática y VBO dinámico para el resto.

`MallaGL` guarda en la GPU un array de vértices (VBO) y un array de índices (EBO) y se dibuja
con `glDrawElements`. Se crea una vez (o una vez por laberinto) y se libera explícitamente con
`liberar()` mientras el contexto OpenGL sigue activo. Los contadores de clase permiten comprobar
que no se acumulan buffers.
"""
import ctypes

import numpy as np
from OpenGL.GL import *

_TIPOS_INDICE = {np.dtype(np.uint16): GL_UNSIGNED_SHORT, np.dtype(np.uint32): GL_UNSIGNED_INT}
FLOAT = np.dtype(np.float32).itemsize


class MallaGL:
    """Malla estática en VBO + EBO.

    formato='pnt': 8 float32 por vértice (posición 3, normal 3, UV 2), con iluminación y textura.
    formato='p'  : 3 float32 por vértice (solo posición), para líneas.
    """
    vivas = 0          # Mallas actualmente en GPU.
    creadas = 0        # Mallas creadas desde que arrancó el programa.
    llamadas = 0       # glDrawElements emitidos (contador para pruebas y diagnóstico).

    def __init__(self, vertices, indices, modo=GL_TRIANGLES, formato='pnt'):
        vertices = np.ascontiguousarray(vertices, dtype=np.float32)
        indices = np.ascontiguousarray(indices)
        if indices.dtype not in _TIPOS_INDICE:
            raise TypeError(f'Tipo de índice no soportado: {indices.dtype} (use uint16 o uint32)')
        componentes = {'pnt': 8, 'p': 3}[formato]
        if vertices.ndim != 2 or vertices.shape[1] != componentes:
            raise ValueError(f'Se esperaban vértices de {componentes} floats, hay {vertices.shape}')
        if len(indices) and int(indices.max()) >= len(vertices):
            raise ValueError('Hay índices fuera del rango de vértices')
        self.modo = modo
        self.formato = formato
        self.n_vertices = len(vertices)
        self.n_indices = len(indices)
        self.tipo_gl = _TIPOS_INDICE[indices.dtype]
        self.stride = componentes * FLOAT
        self.vbo = int(glGenBuffers(1))
        self.ebo = int(glGenBuffers(1))
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        self.viva = True
        MallaGL.vivas += 1
        MallaGL.creadas += 1

    def dibujar(self):
        """Dibuja con glDrawElements y deja limpio el estado de arrays y buffers enlazados."""
        if not self.viva or not self.n_indices:
            return
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, self.stride, ctypes.c_void_p(0))
        if self.formato == 'pnt':
            glEnableClientState(GL_NORMAL_ARRAY)
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            glNormalPointer(GL_FLOAT, self.stride, ctypes.c_void_p(3 * FLOAT))
            glTexCoordPointer(2, GL_FLOAT, self.stride, ctypes.c_void_p(6 * FLOAT))
        try:
            glDrawElements(self.modo, self.n_indices, self.tipo_gl, ctypes.c_void_p(0))
            MallaGL.llamadas += 1
        finally:
            glDisableClientState(GL_VERTEX_ARRAY)
            if self.formato == 'pnt':
                glDisableClientState(GL_NORMAL_ARRAY)
                glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def liberar(self):
        """Borra VBO y EBO. Idempotente. Debe llamarse con el contexto OpenGL activo."""
        if self.viva:
            glDeleteBuffers(2, [self.vbo, self.ebo])
            self.viva = False
            MallaGL.vivas -= 1


class LoteDinamico:
    """VBO dinámico (GL_STREAM_DRAW) con EBO fijo para quads: texto, interfaz y similares.

    Cada vértice son 8 float32: posición 2D, UV 2D y color RGBA. El contenido se reescribe cada
    fotograma con glBufferSubData en un buffer creado una sola vez (no se crean buffers por frame).
    """
    vivos = 0

    def __init__(self, max_quads):
        if max_quads * 4 > 65535:
            raise ValueError('max_quads demasiado grande para índices uint16')
        self.max_quads = max_quads
        self._filas = []
        base = np.arange(max_quads, dtype=np.uint32)[:, None] * 4
        indices = (base + np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)).astype(np.uint16).reshape(-1)
        self.vbo = int(glGenBuffers(1))
        self.ebo = int(glGenBuffers(1))
        self.capacidad_bytes = max_quads * 4 * 8 * FLOAT
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.capacidad_bytes, None, GL_STREAM_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        self.viva = True
        LoteDinamico.vivos += 1

    # --- construcción en CPU ---
    def limpiar(self):
        self._filas.clear()

    def quad(self, x0, y0, x1, y1, uv, color):
        """Rectángulo (x0, y0)-(x1, y1) con uv=(u0, v0, u1, v1) y color RGBA."""
        if len(self._filas) >= self.max_quads * 4:
            return                                         # Lote lleno: se ignora el exceso.
        u0, v0, u1, v1 = uv
        r, g, b, a = color
        self._filas += [(x0, y0, u0, v0, r, g, b, a), (x1, y0, u1, v0, r, g, b, a),
                        (x1, y1, u1, v1, r, g, b, a), (x0, y1, u0, v1, r, g, b, a)]

    def quad_libre(self, puntos, uv, color):
        """Cuadrilátero con 4 puntos (x, y) arbitrarios (p. ej. el marcador del jugador rotado)."""
        if len(self._filas) >= self.max_quads * 4:
            return
        r, g, b, a = color
        for (x, y), (u, v) in zip(puntos, uv):
            self._filas.append((x, y, u, v, r, g, b, a))

    @property
    def n_quads(self):
        return len(self._filas) // 4

    # --- GPU ---
    def dibujar(self):
        """Sube los quads acumulados y los dibuja con una sola llamada glDrawElements."""
        n = self.n_quads
        if not n or not self.viva:
            return
        datos = np.array(self._filas, dtype=np.float32)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.capacidad_bytes, None, GL_STREAM_DRAW)   # "orphaning"
        glBufferSubData(GL_ARRAY_BUFFER, 0, datos.nbytes, datos)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        stride = 8 * FLOAT
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointer(2, GL_FLOAT, stride, ctypes.c_void_p(0))
        glTexCoordPointer(2, GL_FLOAT, stride, ctypes.c_void_p(2 * FLOAT))
        glColorPointer(4, GL_FLOAT, stride, ctypes.c_void_p(4 * FLOAT))
        try:
            glDrawElements(GL_TRIANGLES, n * 6, GL_UNSIGNED_SHORT, ctypes.c_void_p(0))
        finally:
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            glDisableClientState(GL_COLOR_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def liberar(self):
        if self.viva:
            glDeleteBuffers(2, [self.vbo, self.ebo])
            self.viva = False
            LoteDinamico.vivos -= 1


class RutaGL:
    """Rastro del jugador para la cámara cenital: VBO dinámico de crecimiento por duplicación.

    La v5 recorría toda la ruta con glBegin/glVertex en cada fotograma. Aquí cada punto nuevo se
    añade al VBO con glBufferSubData y se dibuja con una única llamada glDrawArrays(GL_LINE_STRIP).
    Cuando se llena, el *mismo* buffer se reasigna con el doble de capacidad (no se crean más objetos).
    """

    def __init__(self, capacidad=1024):
        self.capacidad = capacidad
        self.n = 0
        self.reasignaciones = 0
        self._cpu = np.zeros((capacidad, 3), np.float32)     # Copia en CPU para poder crecer.
        self.vbo = int(glGenBuffers(1))
        self._reservar()
        self.viva = True

    def _reservar(self):
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.capacidad * 3 * FLOAT, None, GL_DYNAMIC_DRAW)
        if self.n:
            glBufferSubData(GL_ARRAY_BUFFER, 0, self._cpu[:self.n].nbytes, self._cpu[:self.n])
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def reiniciar(self):
        self.n = 0

    def añadir(self, x, y, z):
        if self.n >= self.capacidad:
            self.capacidad *= 2
            nueva = np.zeros((self.capacidad, 3), np.float32)
            nueva[:self.n] = self._cpu[:self.n]
            self._cpu = nueva
            self.reasignaciones += 1
            self._reservar()
        self._cpu[self.n] = (x, y, z)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferSubData(GL_ARRAY_BUFFER, self.n * 3 * FLOAT, 3 * FLOAT, self._cpu[self.n:self.n + 1])
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.n += 1

    def dibujar(self):
        if self.n < 2 or not self.viva:
            return
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, 3 * FLOAT, ctypes.c_void_p(0))
        try:
            glDrawArrays(GL_LINE_STRIP, 0, self.n)
        finally:
            glDisableClientState(GL_VERTEX_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, 0)

    def liberar(self):
        if self.viva:
            glDeleteBuffers(1, [self.vbo])
            self.viva = False
