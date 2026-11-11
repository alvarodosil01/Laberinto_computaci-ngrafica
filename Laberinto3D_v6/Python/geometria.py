"""Generación de geometría en CPU (NumPy), sin ninguna llamada a OpenGL.

Todo lo que sale de aquí es un par (vertices, indices):
  * vertices: array float32 de forma (N, 8) con [x, y, z, nx, ny, nz, u, v] por fila
              (posición, normal y coordenadas de textura intercaladas, como en el VBO de referencia);
  * indices:  array entero (uint16 o uint32 según el número de vértices) con triángulos.

Los vértices se comparten (EBO) únicamente cuando coinciden *todos* sus atributos: posición,
normal y UV. Dos esquinas en la misma posición pero con normal o UV distintos siguen siendo
vértices distintos, así que la iluminación y la textura no se ven afectadas.
"""
import numpy as np

from configuracion import ALTURA_PARED, ALTURA_REMATE, SEPARACION_LINEAS

# Direcciones de las caras laterales: (nx, nz) de la normal exterior. Vecino de (f, c) = (f+nz, c+nx).
NORMALES_LATERALES = ((0, -1), (0, 1), (-1, 0), (1, 0))

GRUPOS_PARED = ('pared', 'musgo', 'remate')


# --------------------------------------------------------------------------------------
# Utilidades de buffers
# --------------------------------------------------------------------------------------
def tipo_indice(n_vertices):
    """Tipo entero más pequeño compatible con OpenGL que puede direccionar `n_vertices`."""
    return np.uint16 if n_vertices <= 65535 else np.uint32


def compartir_vertices(vertices_sueltos, indices_sueltos):
    """Elimina vértices repetidos (iguales en posición + normal + UV) y reindexa.

    vertices_sueltos: (K, 8) con una fila por esquina de triángulo (o referenciada por indices_sueltos).
    indices_sueltos:  (M,) índices sobre `vertices_sueltos`.
    Devuelve (vertices float32 (N, 8), indices uint16/uint32 (M,)) con N <= K.
    """
    v = np.asarray(vertices_sueltos, dtype=np.float64)
    v = np.round(v, 6) + 0.0                      # +0.0 convierte -0.0 en 0.0
    unicos, inverso = np.unique(v, axis=0, return_inverse=True)
    inverso = np.asarray(inverso).reshape(-1)
    indices = inverso[np.asarray(indices_sueltos, dtype=np.int64)]
    return (np.ascontiguousarray(unicos, dtype=np.float32),
            np.ascontiguousarray(indices, dtype=tipo_indice(len(unicos))))


class ConstructorMalla:
    """Acumula quads con mapeado planar en unidades de mundo y los convierte en (vértices, índices)."""

    def __init__(self):
        self._filas = []      # filas de 8 floats, 4 por quad
        self._indices = []    # triángulos sueltos

    def quad(self, p0, a, b, eu, ev, su=1.0, sv=1.0, ou=0.0, ov=0.0):
        """Añade un quad p0, p0+a, p0+a+b, p0+b con la normal cross(a, b) (antihorario visto desde ella).

        UV = ((p·eu)*su + ou, (p·ev)*sv + ov): mapeado planar en coordenadas de mundo, de modo que
        caras contiguas y coplanares tienen UV continuas (y comparten vértices) y la textura no se
        deforma si su y sv son la inversa del tamaño en mundo del azulejo de textura.
        """
        p0, a, b = (np.asarray(x, dtype=np.float64) for x in (p0, a, b))
        eu, ev = np.asarray(eu, dtype=np.float64), np.asarray(ev, dtype=np.float64)
        n = np.cross(a, b)
        n = n / np.linalg.norm(n)
        base = len(self._filas)
        for p in (p0, p0 + a, p0 + a + b, p0 + b):
            self._filas.append((*p, *n, float(p @ eu) * su + ou, float(p @ ev) * sv + ov))
        self._indices += [base, base + 1, base + 2, base, base + 2, base + 3]

    @property
    def vacia(self):
        return not self._filas

    def construir(self):
        """(vertices_unicos, indices, n_vertices_sueltos)."""
        if not self._filas:
            return (np.zeros((0, 8), np.float32), np.zeros(0, np.uint16), 0)
        v, i = compartir_vertices(np.array(self._filas), np.array(self._indices))
        return v, i, len(self._filas)


# --------------------------------------------------------------------------------------
# Geometría estática del laberinto
# --------------------------------------------------------------------------------------
def caras_expuestas(mapa):
    """Lista de (f, c, nx, nz): caras laterales de pared que dan a una celda de suelo.

    Una cara entre dos paredes contiguas nunca se genera (queda oculta). Tampoco las caras que
    miran fuera del mapa: ninguna cámara puede situarse allí (la colisión lo impide) y la cenital
    es una vista desde arriba.
    """
    alto, ancho = len(mapa), len(mapa[0])
    caras = []
    for f in range(alto):
        for c in range(ancho):
            if not mapa[f][c]:
                continue
            for nx, nz in NORMALES_LATERALES:
                vf, vc = f + nz, c + nx
                if 0 <= vf < alto and 0 <= vc < ancho and not mapa[vf][vc]:
                    caras.append((f, c, nx, nz))
    return caras


def _cara_vertical(constructor, q, n, y0, alto, escala_u, escala_v, v_origen):
    """Quad vertical sobre el plano que pasa por q con normal exterior n=(nx, 0, nz)."""
    nx, nz = n
    a = np.array([nz, 0.0, -nx])                 # tangente tal que cross(a, arriba) = n
    p0 = np.array([q[0], y0, q[2]]) - 0.5 * a
    constructor.quad(p0, a, (0.0, alto, 0.0), eu=a, ev=(0, 1, 0), su=escala_u, sv=escala_v,
                     ov=-v_origen * escala_v)


def construir_geometria_estatica(mapa, salida, entrada, musgo):
    """Construye todos los grupos estáticos. Devuelve dict nombre -> (vertices, indices, sueltos).

    Grupos (cada uno se dibuja con UNA llamada glDrawElements):
      pared   caras laterales de muro con la textura de ladrillo;
      musgo   caras laterales de los muros marcados con musgo (misma geometría, otra textura);
      remate  tapa superior + franja lateral de mármol de todos los muros;
      suelo   suelo de las celdas transitables, una quad por celda (iluminación por vértice decente);
      entrada / salida  marcas planas sobre el suelo;
      portal  fondo luminoso del hueco de la puerta;
      aristas (formato solo-posición, GL_LINES) líneas oscuras que marcan los bordes de los muros.
    """
    alto, ancho = len(mapa), len(mapa[0])
    H, CAP = ALTURA_PARED, ALTURA_REMATE
    grupos = {nombre: ConstructorMalla() for nombre in
              ('pared', 'musgo', 'remate', 'suelo', 'entrada', 'salida', 'portal')}
    segmentos = {}        # posición -> id de vértice de línea
    posiciones = []
    aristas = set()

    def vertice_linea(p):
        clave = tuple(np.round(p, 6) + 0.0)
        if clave not in segmentos:
            segmentos[clave] = len(posiciones)
            posiciones.append(clave)
        return segmentos[clave]

    def linea(p, q):
        i, j = vertice_linea(p), vertice_linea(q)
        aristas.add((min(i, j), max(i, j)))

    for f, c, nx, nz in caras_expuestas(mapa):
        q = np.array([c + 0.5 * nx, 0.0, f + 0.5 * nz])
        destino = grupos['musgo' if (f, c) in musgo else 'pared']
        # Un azulejo de textura = 1 de ancho x ALTURA_PARED de alto (una repetición por muro): sin deformación.
        _cara_vertical(destino, q, (nx, nz), 0.0, H, 1.0, 1.0 / H, 0.0)
        # Franja de mármol: azulejo de 1 x 1 en mundo.
        _cara_vertical(grupos['remate'], q, (nx, nz), H, CAP, 1.0, 1.0, H)
        # Aristas oscuras, ligeramente separadas de la cara.
        a = np.array([nz, 0.0, -nx])
        centro = q + np.array([nx, 0.0, nz]) * SEPARACION_LINEAS
        p0, p1 = centro - 0.5 * a, centro + 0.5 * a
        for p in (p0, p1):
            linea(p, p + (0, H + CAP, 0))
        for y in (H, H + CAP):
            linea(p0 + (0, y, 0), p1 + (0, y, 0))

    for f in range(alto):
        for c in range(ancho):
            if mapa[f][c]:
                # Tapa superior del muro: azulejo de mármol de 1 x 1, UV = (x, z).
                grupos['remate'].quad((c - 0.5, H + CAP, f - 0.5), (0, 0, 1), (1, 0, 0),
                                      eu=(1, 0, 0), ev=(0, 0, 1))
            else:
                grupos['suelo'].quad((c - 0.5, 0.0, f - 0.5), (0, 0, 1), (1, 0, 0),
                                     eu=(1, 0, 0), ev=(0, 0, 1))

    # Marcas planas sobre el suelo (0.72 x 0.72, como en la v5), 4 mm por encima.
    for nombre, (f, c) in (('entrada', entrada), ('salida', salida)):
        lado = 0.72
        x0, z0 = c - lado / 2, f - lado / 2
        grupos[nombre].quad((x0, 0.004, z0), (0, 0, lado), (lado, 0, 0), eu=(1, 0, 0), ev=(0, 0, 1),
                            su=1 / lado, sv=1 / lado, ou=-x0 / lado, ov=-z0 / lado)

    # Fondo luminoso de la puerta: plano del lado exterior de la celda, mirando hacia el pasillo (-z).
    f, c = salida
    grupos['portal'].quad((c + 0.5, 0.0, f + 0.5), (-1, 0, 0), (0, H + CAP, 0),
                          eu=(1, 0, 0), ev=(0, 1, 0), su=1.0, sv=1.0 / (H + CAP))

    resultado = {}
    for nombre, constructor in grupos.items():
        resultado[nombre] = constructor.construir()
    # Líneas: solo posición (3 floats).
    pos = np.array(posiciones, dtype=np.float32).reshape(-1, 3)
    idx = np.array(sorted(aristas), dtype=np.int64).reshape(-1)
    resultado['aristas'] = (np.ascontiguousarray(pos),
                            np.ascontiguousarray(idx, dtype=tipo_indice(len(pos))), len(idx))
    return resultado
