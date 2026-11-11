"""Laberinto 3D v6: punto de entrada.

Uso:  python main.py [--dificultad facil|normal|dificil] [--semilla N]
Las rutas de modelos y texturas son relativas a este archivo, así que se puede ejecutar desde
cualquier carpeta:  python /ruta/a/Laberinto3D_v6/Python/main.py
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))     # Importar los módulos desde cualquier directorio.

from dificultad import DIFICULTAD_INICIAL, DIFICULTADES
from juego import Juego


def main(argv=None):
    ap = argparse.ArgumentParser(description='Laberinto 3D v6')
    ap.add_argument('--dificultad', choices=[d.clave for d in DIFICULTADES], default=DIFICULTAD_INICIAL,
                    help='dificultad inicial (se puede cambiar en el juego con F1/F2/F3)')
    ap.add_argument('--semilla', type=int, default=None, help='semilla del primer laberinto (reproducible)')
    args = ap.parse_args(argv)
    Juego(args.dificultad, args.semilla).ejecutar()


if __name__ == '__main__':
    main()
