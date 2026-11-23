"""Matrices de proyección y de vista sin depender de GLU.

Sustituyen a gluPerspective y gluLookAt con las mismas fórmulas. Así el programa solo necesita
OpenGL y no la biblioteca GLU (libGLU), que falta en muchas instalaciones de Linux.
"""
import math

import numpy as np
from OpenGL.GL import glMultMatrixf, glTranslatef


def perspectiva(fov_y_grados, aspecto, cerca, lejos):
    """Equivalente a gluPerspective sobre la matriz actual."""
    f = 1.0 / math.tan(math.radians(fov_y_grados) / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspecto
    m[1, 1] = f
    m[2, 2] = (lejos + cerca) / (cerca - lejos)
    m[2, 3] = 2.0 * lejos * cerca / (cerca - lejos)
    m[3, 2] = -1.0
    glMultMatrixf(np.ascontiguousarray(m.T))


def mirar_a(ojo, objetivo, arriba):
    """Equivalente a gluLookAt(ojo, objetivo, arriba) sobre la matriz actual."""
    ojo = np.asarray(ojo, dtype=np.float64)
    f = np.asarray(objetivo, dtype=np.float64) - ojo
    f /= np.linalg.norm(f)
    s = np.cross(f, np.asarray(arriba, dtype=np.float64))
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    glMultMatrixf(np.ascontiguousarray(m.T))
    glTranslatef(*(-ojo))
