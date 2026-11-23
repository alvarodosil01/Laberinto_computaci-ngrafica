"""Carga y gestión de texturas de OpenGL.

Cambios respecto a la v5: se fija GL_UNPACK_ALIGNMENT=1 durante la subida (con anchos cuyo
número de bytes por fila no es múltiplo de 4 la v5 desplazaba la imagen), se admiten mipmaps y
filtrado anisotrópico para las texturas de pared (menos parpadeo en pasillos largos) y se añaden
utilidades para crear, actualizar y liberar texturas.
"""
import numpy as np
import pygame
from OpenGL.GL import *

GL_TEXTURE_MAX_ANISOTROPY = 0x84FE
GL_MAX_TEXTURE_MAX_ANISOTROPY = 0x84FF


def bytes_superficie(superficie, formato, volteo=True):
    funcion = getattr(pygame.image, 'tobytes', None) or pygame.image.tostring   # tostring: pygame < 2.1.3
    return funcion(superficie, formato, volteo)


def _parametros(repetir, mipmaps, nearest):
    envoltura = GL_REPEAT if repetir else GL_CLAMP_TO_EDGE
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, envoltura)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, envoltura)
    if nearest:
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        return
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    if mipmaps:
        if bool(glGenerateMipmap):
            glGenerateMipmap(GL_TEXTURE_2D)
        # (Sin glGenerateMipmap, p. ej. contextos 2.1, la cadena se genera en la subida: ver GL_GENERATE_MIPMAP.)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        try:
            maximo = glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY)
            if maximo and maximo > 1:
                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY, min(8.0, float(maximo)))
        except Exception:        # La extensión no existe en todos los controladores.
            pass
    else:
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)


def textura_desde_superficie(superficie, mipmaps=False, repetir=True, alfa=False):
    """Crea una textura OpenGL a partir de una Surface de pygame. Devuelve su identificador."""
    formato = 'RGBA' if alfa else 'RGB'
    interno = GL_RGBA if alfa else GL_RGB
    datos = bytes_superficie(superficie, formato)
    previo = glGetIntegerv(GL_UNPACK_ALIGNMENT)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    textura = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, textura)
    if mipmaps and not bool(glGenerateMipmap):
        glTexParameteri(GL_TEXTURE_2D, GL_GENERATE_MIPMAP, GL_TRUE)       # Alternativa de OpenGL 1.4.
    glTexImage2D(GL_TEXTURE_2D, 0, interno, superficie.get_width(), superficie.get_height(), 0,
                 interno, GL_UNSIGNED_BYTE, datos)
    _parametros(repetir, mipmaps, nearest=False)
    glBindTexture(GL_TEXTURE_2D, 0)
    glPixelStorei(GL_UNPACK_ALIGNMENT, previo)
    return textura


def cargar_textura(ruta_textura, mipmaps=False, repetir=True):
    """Carga un archivo de imagen como textura (misma firma básica que en la v5)."""
    return textura_desde_superficie(pygame.image.load(ruta_textura), mipmaps=mipmaps, repetir=repetir)


def textura_desde_array(rgba, nearest=True, repetir=False):
    """Textura RGBA8 a partir de un array uint8 (alto, ancho, 4). La fila 0 es la coordenada t=0."""
    rgba = np.ascontiguousarray(rgba, dtype=np.uint8)
    alto, ancho = rgba.shape[:2]
    previo = glGetIntegerv(GL_UNPACK_ALIGNMENT)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    textura = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, textura)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ancho, alto, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba)
    _parametros(repetir, mipmaps=False, nearest=nearest)
    glBindTexture(GL_TEXTURE_2D, 0)
    glPixelStorei(GL_UNPACK_ALIGNMENT, previo)
    return textura


def actualizar_textura_array(textura, rgba):
    """Reescribe el contenido (mismo tamaño) de una textura creada con textura_desde_array."""
    rgba = np.ascontiguousarray(rgba, dtype=np.uint8)
    alto, ancho = rgba.shape[:2]
    previo = glGetIntegerv(GL_UNPACK_ALIGNMENT)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glBindTexture(GL_TEXTURE_2D, textura)
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, ancho, alto, GL_RGBA, GL_UNSIGNED_BYTE, rgba)
    glBindTexture(GL_TEXTURE_2D, 0)
    glPixelStorei(GL_UNPACK_ALIGNMENT, previo)


def liberar_texturas(ids):
    ids = [int(i) for i in ids if i]
    if ids:
        glDeleteTextures(ids)
