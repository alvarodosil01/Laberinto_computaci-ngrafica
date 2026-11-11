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
| W / flecha arriba | Avanzar |
| S | Retroceder |
| A / D | Desplazarse lateralmente |
| Flechas izquierda / derecha | Girar |
| 1 / 2 | Primera persona / cenital ortográfica |
| L | Alternar luz general y luz local |
| N | Crear otro laberinto |
| Esc | Salir |

La entrada se muestra en verde y la salida en rojo. Al llegar a la salida, el título de la ventana anuncia el final. La cámara cenital muestra en amarillo el recorrido realizado y en azul la posición actual.

`laberinto.py` crea una matriz de paredes (`1`) y pasillos (`0`) mediante DFS aleatorizado. Después abre algunas conexiones para ofrecer rutas alternativas. La misma matriz se usa para dibujar paredes, comprobar colisiones y detectar la salida.
