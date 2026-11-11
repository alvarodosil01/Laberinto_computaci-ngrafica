# Laberinto 3D

Adaptación del ejercicio del pórtico. Usa su cargador de modelos OBJ, sus transformaciones y su sistema de texturas con Pygame y OpenGL. Las paredes, el suelo y los marcadores se construyen escalando el cubo unitario incluido.

## Ejecución

Desde la carpeta `Python`:

```powershell
python -m pip install pygame PyOpenGL numpy
python main.py
```

## Controles

| Tecla | Acción |
| --- | --- |
| W / S | Avanzar / retroceder |
| A / D | Girar a la izquierda / derecha |
| Q / E | Desplazarse lateralmente (opcional) |
| 1 / 2 / 3 | Primera persona / cenital ortográfica / tercera persona |
| L | Cambiar tono: blanco, cálido, frío, verde, violeta |
| I | Alternar iluminación general y luz local |
| N | Crear otro laberinto |
| Esc | Salir |

La entrada se muestra en verde y la salida en rojo. Al llegar a la salida, el título de la ventana anuncia el final. La cámara cenital muestra en amarillo el recorrido realizado y en azul la posición actual. La tercera persona sigue al personaje desde atrás y arriba, acortando la distancia de la cámara si hay una pared detrás. Las paredes tienen contornos oscuros para distinguir sus límites.

`laberinto.py` crea una matriz de paredes (`1`) y pasillos (`0`) mediante DFS aleatorizado. Después abre algunas conexiones para ofrecer rutas alternativas. La misma matriz se usa para dibujar paredes, comprobar colisiones y detectar la salida.
