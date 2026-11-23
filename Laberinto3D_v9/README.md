# Laberinto 3D v9

Conserva las funciones de v6 y el personaje y la camara de v8.
Pasillos de 2 unidades de ancho. Muros y personaje conservan su grosor y escala.

## Ejecutar

```sh
python -m pip install -r requirements.txt
python Python/main.py
```

Objetivo: recoger las esferas, abrir la puerta y llegar a la salida.

## Controles

- WASD: movimiento. Raton: orientar la camara.
- 1 / 2 / 3: primera persona / cenital / tercera persona.
- F1 / F2 / F3: dificultad.
- T: terror / clasico. I: iluminacion o linterna. L: tono de luz.
- M: minimapa. H: ayuda. N: nueva partida. Esc: salir.

Anchura configurada con ANCHO_PASILLO = 2 en Python/configuracion.py.
