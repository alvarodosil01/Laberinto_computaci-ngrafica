"""Lectura de modelos OBJ (v / vt / vn / f) y conversión a buffers listos para OpenGL.

Adaptado del `Modelo` del ejemplo VBOs: se leen posiciones, normales y UV, pero en lugar de
duplicar tres vértices por triángulo (glDrawArrays), se comparten los vértices idénticos y se
devuelve un array de índices para dibujar con un EBO.

Mejoras respecto al cargador de la v5:
  * acepta caras `v`, `v/t`, `v//n` y `v/t/n`, índices negativos y polígonos de más de 3 lados
    (se trianguliza en abanico); la v5 descartaba en silencio cualquier cara que no fuese triángulo;
  * orienta cada triángulo según su normal. Los OBJ adjuntos tienen un orden de vértices
    inconsistente (esfera.obj: 224 de 224 triángulos al revés; cubo.obj: 6 de 12), lo que haría
    desaparecer caras al activar GL_CULL_FACE.
"""
import numpy as np

from geometria import compartir_vertices


def cargar_obj(ruta, orientar_por_normales=True):
    """Devuelve (vertices float32 (N, 8), indices uint16/uint32, triangulos_sueltos)."""
    posiciones, normales, uvs = [], [], []
    esquinas = []        # (pos(3), normal(3) o None, uv(2))
    triangulos = []      # tripletas de índices sobre `esquinas`

    def indice(texto, longitud):
        i = int(texto)
        return i - 1 if i > 0 else longitud + i

    with open(ruta, encoding='utf-8') as archivo:
        for linea in archivo:
            partes = linea.split()
            if not partes:
                continue
            etiqueta = partes[0]
            if etiqueta == 'v':
                posiciones.append(tuple(map(float, partes[1:4])))
            elif etiqueta == 'vn':
                normales.append(tuple(map(float, partes[1:4])))
            elif etiqueta == 'vt':
                uvs.append(tuple(map(float, partes[1:3])))
            elif etiqueta == 'f':
                cara = []
                for token in partes[1:]:
                    campos = token.split('/')
                    p = posiciones[indice(campos[0], len(posiciones))]
                    t = uvs[indice(campos[1], len(uvs))] if len(campos) > 1 and campos[1] else (0.0, 0.0)
                    n = normales[indice(campos[2], len(normales))] if len(campos) > 2 and campos[2] else None
                    esquinas.append((p, n, t))
                    cara.append(len(esquinas) - 1)
                for k in range(1, len(cara) - 1):                  # Abanico para polígonos.
                    triangulos.append((cara[0], cara[k], cara[k + 1]))

    filas = np.zeros((len(esquinas), 8))
    for i, (p, n, t) in enumerate(esquinas):
        filas[i, 0:3] = p
        filas[i, 6:8] = t
        if n is not None:
            filas[i, 3:6] = n
    indices = np.array(triangulos, dtype=np.int64).reshape(-1, 3)

    for k, (a, b, c) in enumerate(indices):
        g = np.cross(filas[b, 0:3] - filas[a, 0:3], filas[c, 0:3] - filas[a, 0:3])
        if esquinas[a][1] is None:                                  # Sin normales: normal plana.
            if np.linalg.norm(g) > 0:
                filas[[a, b, c], 3:6] = g / np.linalg.norm(g)
        elif orientar_por_normales and g @ filas[[a, b, c], 3:6].sum(axis=0) < 0:
            indices[k] = (a, c, b)                                  # Invierte el orden de los vértices.

    vertices, idx = compartir_vertices(filas, indices.reshape(-1))
    return vertices, idx, len(esquinas)
