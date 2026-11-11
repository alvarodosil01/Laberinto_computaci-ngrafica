"""Comprueba que el programa arranca y se cierra sin errores, y que se puede lanzar desde otra carpeta.

Ejecutar (con pantalla, o bajo xvfb-run):   python pruebas/verificar_arranque.py
  1. compila todos los .py;
  2. lanza `main.py` como proceso independiente desde OTRO directorio y comprueba que sigue vivo y sin errores
     tras unos segundos;
  3. ejecuta el bucle principal real (`Juego.ejecutar`) con una secuencia de teclas/eventos en la cola
     (N, F3, 2, 3, M, H, L, I, Esc) y comprueba que termina limpiamente liberando todo.
"""
import compileall
import os
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(AQUI, '..', 'Python')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')


def main():
    fallos = 0
    ok = compileall.compile_dir(PYTHON, quiet=1, force=True)
    print(('OK    ' if ok else 'FALLO ') + 'compilación de todos los módulos')
    fallos += not ok

    with tempfile.TemporaryDirectory() as otra_carpeta:
        proc = subprocess.Popen([sys.executable, os.path.join(PYTHON, 'main.py'), '--dificultad', 'dificil', '--semilla', '5'],
                                cwd=otra_carpeta, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(6)
        vivo = proc.poll() is None
        proc.terminate()
        salida, errores = proc.communicate(timeout=20)
        limpio = 'Traceback' not in errores and 'Error' not in errores.replace('ALSA', '')
        print(('OK    ' if vivo and limpio else 'FALLO ') + 'main.py lanzado desde otra carpeta: sigue ejecutándose y sin errores')
        if not (vivo and limpio):
            print(errores[-1500:])
            fallos += 1

    sys.path.insert(0, PYTHON)
    import pygame
    from OpenGL.GL import glGetString, GL_VERSION
    from buffers import LoteDinamico, MallaGL
    from juego import Juego
    juego = Juego('normal', semilla=3)
    for tecla in (pygame.K_n, pygame.K_F3, pygame.K_2, pygame.K_3, pygame.K_m, pygame.K_h, pygame.K_l, pygame.K_i,
                  pygame.K_t, pygame.K_i, pygame.K_t, pygame.K_5, pygame.K_1, pygame.K_ESCAPE):   # T: terror/clásico; I: linterna
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=tecla))
    try:
        juego.ejecutar()                   # Bucle real; el Esc de la cola lo termina y cerrar() libera todo.
        terminado = True
    except Exception as e:                 # noqa: BLE001
        terminado = False
        print(e)
    limpio = MallaGL.vivas == 0 and LoteDinamico.vivos == 0
    print(('OK    ' if terminado and limpio else 'FALLO ') + 'bucle principal con teclas simuladas y cierre con Esc (0 buffers vivos)')
    fallos += not (terminado and limpio)
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
