# Laberinto 3D v9

Pasillos de 2 unidades de ancho. Personaje y camara de v8.
Cambios de controles de v6 actualizada en GitHub. Campo de vision: 60 grados.

## Ejecutar

```sh
python -m pip install -r requirements.txt
python Python/main.py
```

Recoge todas las esferas para abrir la puerta y alcanzar la salida.

## Controles

| Control | Accion |
| --- | --- |
| WASD | Moverse |
| Raton / flechas izquierda y derecha | Orientar la vista |
| 1 / 2 / 3 | Primera persona / cenital / tercera persona |
| F1 / F2 / F3 | Facil / normal / dificil |
| Tab (mantener) | Mostrar minimapa; se cierra al soltar |
| E | Linterna en modo terror |
| R | Alternar terror / clasico |
| I | Iluminacion solo en modo clasico |
| L | Tono de luz |
| H | Ayuda |
| N | Nueva partida |
| F11 | Alternar pantalla completa / ventana |
| Esc | Salir |

La ventana también permite maximizar y cambiar de tamaño. F11 conserva la partida y vuelve al tamaño anterior al salir de pantalla completa.

Altura de paredes: 2,5 unidades. El plano de niebla cenital se sitúa automáticamente 0,2 unidades por encima de los muros y sus remates.
