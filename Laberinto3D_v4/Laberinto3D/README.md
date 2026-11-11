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
| W / S | Avanzar / retroceder según la cámara |
| A / D | Desplazarse lateralmente según la cámara |
| Ratón | Orientar la vista en primera y tercera persona |
| Flechas izquierda / derecha | Girar la vista como alternativa al ratón |
| 1 / 2 / 3 | Primera persona / cenital ortográfica / tercera persona |
| L | Cambiar tono: blanco, cálido, frío, verde, violeta |
| I | Alternar iluminación general y luz local |
| N | Crear otro laberinto |
| Esc | Salir |

La entrada se muestra en verde y la salida en rojo. Al llegar a la salida, el título de la ventana anuncia el final. La cámara cenital muestra en amarillo el recorrido realizado y en azul la posición actual. En primera y tercera persona, WASD funciona igual y el ratón orienta la cámara; en tercera, el personaje mira hacia la dirección de movimiento. La cámara sigue al personaje desde atrás y arriba, acortando su distancia si hay una pared detrás. Las paredes usan una textura de bloques generada con Pygame, juntas visibles, bordes y remates superiores. La iluminación ambiental y una luz secundaria suavizan las caras en sombra.

`laberinto.py` crea una matriz de paredes (`1`) y pasillos (`0`) mediante DFS aleatorizado. Después abre algunas conexiones para ofrecer rutas alternativas. La misma matriz se usa para dibujar paredes, comprobar colisiones y detectar la salida.
