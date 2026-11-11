# Laberinto 3D v6

Versión 6 del laberinto 3D en Python (Pygame + PyOpenGL + NumPy), construida a partir de la **v5** sin modificar sus archivos.
Conserva el laberinto generado automáticamente, el movimiento con colisiones, las cámaras 1/2/3, la iluminación y los tonos, y añade:
geometría estática agrupada en **VBO + EBO**, musgo, esferas coleccionables animadas, puerta de salida, mapa explorado, brújula,
cámara en tercera persona suavizada, tres dificultades y cronómetro con pantalla final.

## Instalación y ejecución

Requisitos: Python 3.8 o superior y una tarjeta/controlador con OpenGL 2.1 o superior (probado con OpenGL 4.5 en modo compatibilidad).
**No hace falta GLU** (las matrices de proyección y vista se calculan en `vistas.py`).

```bash
cd Laberinto3D_v6
python -m pip install -r requirements.txt
python Python/main.py
```

Se puede lanzar desde cualquier carpeta (`python /ruta/a/Laberinto3D_v6/Python/main.py`): todas las rutas de modelos y texturas son
relativas al propio programa. Opciones: `--dificultad facil|normal|dificil` y `--semilla N` (laberinto reproducible).

Dependencias (`requirements.txt`): `pygame`, `PyOpenGL`, `numpy`. No se añade ninguna otra. (Para ejecutar las pruebas con un
servidor sin pantalla, además, `xvfb` y Mesa; ver «Pruebas».)

## Controles

| Tecla | Acción |
| --- | --- |
| W A S D | Moverse (relativo a la dirección de la cámara) |
| Ratón / flechas ← → | Orientar la vista en primera y tercera persona |
| 1 / 2 / 3 | Primera persona / cenital / tercera persona |
| L | Cambiar el tono de la luz (blanco, cálido, frío, verde, violeta) |
| I | Modo clásico: alternar iluminación general y luz local. **Modo terror: encender/apagar la linterna** |
| N | Nuevo laberinto (misma dificultad, cronómetro a cero) |
| **F1 / F2 / F3** (o **4 / 5 / 6**) | **Dificultad Fácil / Normal / Difícil** (genera una partida nueva) |
| **T** | **Alternar modo terror / modo clásico** (el terror es el predeterminado) |
| **M** | Mostrar/ocultar el minimapa |
| **H** | Mostrar/ocultar la ayuda en pantalla |
| Esc | Salir |

Los controles nuevos (en negrita) aparecen también en pantalla. La dificultad activa se muestra en el panel superior izquierdo
junto con la forma de cambiarla.

## Modo terror (tecla T)

Retoque de atmósfera estilo survival horror, sin cambiar la jugabilidad. Todo el código está en `Python/ambiente_terror.py` y se
conecta con unos pocos ganchos en `juego.py`; los parámetros están en `configuracion.py` (bloque `TERROR_*`, comentados).
Con **T** se vuelve al aspecto clásico, cuya escena 3D queda idéntica píxel a píxel a la de antes (comprobado contra la versión anterior).

* **Oscuridad y niebla**: ambiente casi nulo, fondo negro azulado y niebla exponencial (`exp2`) con ~8 unidades de alcance. La cámara
  cenital sigue legible: sin niebla y con más ambiente.
* **Linterna en cono** que sigue la mirada (yaw/pitch) en primera persona y sale de la cabeza del personaje en tercera. I la
  enciende/apaga. Parpadea (ruido continuo, ráfagas nerviosas cada 5–14 s y, muy rara vez, un apagón de 0.2–0.5 s).
* **Un único par de shaders GLSL `#version 120`** (iluminación por píxel + niebla) que lee los atributos fijos (`gl_Vertex`, `gl_Normal`,
  `gl_MultiTexCoord0`, matrices `gl_*`): los VBO/EBO y el formato de vértice no cambian. Solo se activa al dibujar sólidos y objetos
  dinámicos en 1ª y 3ª persona; HUD, minimapa, brújula, líneas y cenital se dibujan con la tubería fija.
* **Luz propia**: las esferas usan el material emisivo (brillan en la oscuridad) con un halo aditivo para verse entre la niebla;
  el portal de la puerta abierta brilla en verde; la entrada y la salida llevan un brillo tenue.
* **Texturas sucias** generadas con NumPy a partir de las originales (mismo tamaño y UV, siguen siendo teselables): desaturadas y
  oscurecidas, humedad, hollín en la base de las paredes, óxido, grietas y musgo más oscuro. `GL_NEAREST` al ampliar (look retro)
  y mipmaps al reducir (`TERROR_RETRO`). El modo clásico conserva las texturas originales.
* **Pantalla**: viñeta y grano de película animado (dos quads a pantalla completa, sin FBO) dibujados antes del HUD, que no se ve
  afectado; balanceo sutil de la cámara al caminar y respiración al estar quieto.
* **Sonido** generado por código (sin archivos): zumbido grave, pasos y un latido que se acelera al apagarse la linterna.
  Se desactiva solo si no hay dispositivo de audio; `TERROR_VOLUMEN = 0` lo silencia.
* Si el shader no compila o no hay GLSL, el juego **vuelve al modo clásico** con un aviso por consola.

Si queda demasiado oscuro o va lento, ajusta en `configuracion.py`: `TERROR_AMBIENTE`, `TERROR_LINTERNA_INTENSIDAD`,
`TERROR_NIEBLA_ALCANCE`, `TERROR_VINETA`, `TERROR_GRANO` (0 = sin grano), `TERROR_HALO`, `TERROR_TEX_*`.

## Cómo se juega

1. Recoge **todas las esferas doradas** (el panel indica cuántas quedan). Giran y suben y bajan suavemente; se recogen al pasar cerca y
   no bloquean el paso.
2. Al recoger la última, la **puerta de salida** pasa de *cerrada* (chapa gris con candado y «CERRADA») a *abierta* (chapa verde con
   flechas): se hunde en el suelo y descubre un fondo luminoso verde. Mientras está cerrada o a medio abrir **es sólida** (colisión): no
   se puede entrar ni terminar. Está en el muro exterior inferior, junto a la esquina de abajo a la derecha, y al abrirse se marca en el mapa.
3. Cruza la puerta para completar el laberinto. El **cronómetro** corre desde que empieza la partida y se detiene al completarla;
   la pantalla final muestra dificultad, tiempo y esferas recogidas, y explica cómo seguir (N, F1/F2/F3, Esc).
4. **Mapa explorado**: solo se revela lo que se ha recorrido. Regla: al entrar en una celda se revelan las celdas de suelo a ≤ *R* pasos
   de pasillo (sin atravesar paredes) y las paredes que las rodean (*R* depende de la dificultad). Lo no explorado se ve oscuro. El
   minimapa (abajo a la derecha, cámaras 1 y 3) y la **cámara cenital** (que ahora tiene «niebla» sobre lo no explorado) usan la misma
   información. Entrada en verde, salida en rojo (verde claro al abrirse; solo si se ha descubierto o ya está abierta), esferas en
   amarillo (solo si su celda está descubierta) y el jugador como una flecha orientada. Una partida nueva reinicia la exploración.
5. **Brújula** (primera y tercera persona): cinta arriba y centrada (~2 % de la pantalla) con N, NE, E, SE, S, SO, O, NO que se
   desplaza con el giro de la cámara y rumbo numérico (p. ej. «NE 043°»). Norte = arriba del mapa (−Z); yaw 90° = este (+X).
   En la cenital se indica que el norte está arriba.

### Dificultades (`Python/dificultad.py`, único lugar donde viven estos números)

| | Tamaño | Conexiones extra | Esferas | Radio de revelado del mapa |
| --- | --- | --- | --- | --- |
| Fácil | 15 × 15 | 16 | 3 | 4 pasos |
| Normal | 21 × 21 | 12 | 5 | 3 pasos |
| Difícil | 31 × 31 | 6 | 8 | 2 pasos |

Más conexiones extra = más rutas alternativas (más fácil). Más radio de revelado = más pista en el mapa. El generador garantiza que la
entrada, todas las esferas y la puerta son alcanzables (la puerta cierra un callejón, así que cerrarla no parte el laberinto en dos).

## Arquitectura VBO / EBO

**Formato.** Cada vértice son 8 `float32` intercalados: posición (3), normal (3) y UV (2), como en el VBO de referencia. Los índices
son `uint16` (o `uint32` si hiciera falta más de 65 535 vértices; se elige solo). Los buffers se crean con `glGenBuffers/glBufferData`
y se dibujan con `glDrawElements` (`buffers.py`, clase `MallaGL`).

**Geometría estática agrupada** (`geometria.py` + `escena.py`). Todo lo que depende solo del mapa se genera una vez en NumPy y se sube
a la GPU. Los grupos se separan por textura/material y cada uno es **una única llamada** `glDrawElements`:

| Grupo | Contenido | Textura |
| --- | --- | --- |
| `pared` | caras laterales de muro | ladrillo (procedural) |
| `musgo` | caras laterales de los muros con musgo (≈ 35 %) | ladrillo + musgo (procedural) |
| `remate` | tapa superior y franja lateral de todos los muros | `marmol.png` |
| `suelo` | una quad por celda de suelo | `granito.png` |
| `entrada`, `salida` | marcas planas del suelo | `verde.png`, `rojo.png` |
| `portal` | fondo luminoso del hueco de la puerta (solo se dibuja con la puerta desbloqueada) | degradado verde |
| `aristas` | líneas oscuras de los bordes (formato solo-posición, `GL_LINES`) | — |

En la escena de ejemplo (Normal, 229 muros) la v5 hacía unas **461** llamadas `glDrawArrays` (suelo + 2 por muro + 2 marcas);
la v6 hace **13** `glDrawElements` en primera persona con la puerta cerrada (6 sólidos + aristas + puerta + 5 esferas), 16 con la
interfaz incluida (3 lotes 2D). Los números de la v5 son un cálculo a partir de su código (no pude ejecutar la v5 en el entorno de
pruebas: necesita GLU, que no está instalada).

**Caras ocultas.** Solo se genera la cara lateral de un muro cuando su vecino es suelo (`geometria.caras_expuestas`). Entre muros
contiguos no hay caras, y tampoco hacia fuera del mapa (ninguna cámara puede estar allí: las colisiones lo impiden y la cenital mira
desde arriba). Normal 21×21: 399 caras laterales frente a las 916 de la v5 y 2 054 triángulos de muros y remates frente a 5 496.
El suelo bajo los muros tampoco se genera. Los remates de mármol se conservan (tapa + franja superior) y las aristas oscuras se
construyen sobre las mismas caras expuestas.

**EBO y vértices compartidos** (`geometria.compartir_vertices`). Se unen los vértices que coinciden en posición **y** normal **y** UV
(`numpy.unique` sobre las filas de 8 floats). Las UV se calculan en *unidades de mundo* (`u` a lo largo del muro, `v = y / altura`),
así que las caras coplanares contiguas son continuas y comparten los vértices de su arista, y el ladrillo no muestra costuras entre
celdas. Dos esquinas con la misma posición pero distinta normal (esquina de dos muros) o UV distinta **no** se unen. Ejemplo
(Normal, semilla 11): `pared` 1 064 → 786 vértices, `remate` 2 512 → 1 578, `suelo` 848 → 402, aristas 2 692 → 1 644; el cubo OBJ pasa de 36
a 24 vértices y la esfera de 672 a 151 (`modelo.py` / `obj.py`).

**Ciclo de vida.** `EscenaEstatica.construir()` libera los VBO/EBO del laberinto anterior y crea los nuevos: se ejecuta al pulsar N o
cambiar de dificultad, con el contexto OpenGL activo, y nunca por fotograma. `Juego.liberar_recursos()` borra buffers y texturas al cerrar
antes de `pygame.quit()`. `MallaGL.vivas/creadas` permiten comprobar que no se acumulan.

**Estático frente a dinámico.** Estático (en buffers entre fotogramas): suelo, muros, remates, marcas, portal y aristas. Dinámico:
la puerta (cubo OBJ con traslación según cuánto se haya hundido), las esferas (esfera OBJ con traslación/giro/escala por esfera, función
del *tiempo* real, no de los fotogramas), el personaje de la tercera persona, el rastro de la cenital (VBO dinámico `RutaGL`, que añade
puntos con `glBufferSubData` en lugar de recorrerlos con `glBegin` cada fotograma), la niebla (un quad + una textura de 1 texel por
celda que solo se resube cuando cambia lo explorado) y la interfaz (`LoteDinamico`: un VBO `GL_STREAM_DRAW` de capacidad fija con
un EBO de quads; el texto sale de un atlas de glifos creado una vez).

**Estado de OpenGL.** Cada paso de dibujo deja desenlazados los VBO/EBO, desactivados los arrays de cliente, sin textura enlazada y
con las pilas de matrices equilibradas; la emisión de las esferas se restablece; la interfaz 2D restaura profundidad, culling y
mezcla. Hay una prueba automática de ello (`interfaz_sin_fugas_de_estado_gl`).

**Modelos OBJ.** `esfera.obj` y `esfera_lr.obj` de la carpeta VBOs son **idénticos byte a byte** (224 triángulos, 153 vértices del
archivo, 151 únicos tras compartir), así que no hay diferencia de rendimiento entre ellos; se usa `esfera_lr.obj` (nombre de baja
resolución). Para las esferas, la puerta y el personaje se usa `cubo.obj`/`esfera_lr.obj` con las transformaciones de `transformaciones.py`.
`obj.cargar_obj` admite caras `v`, `v/t`, `v//n`, `v/t/n`, polígonos y orienta los triángulos según sus normales (ver correcciones).

**Texturas procedurales** (`texturas_procedurales.py`, nada que descargar): ladrillo (256×486 px = 1.0×1.9 unidades, 256 px por
unidad en ambos ejes → sin deformación, periódico en horizontal), musgo (el mismo ladrillo con musgo que crece desde la base, ruido
periódico para que encaje entre celdas contiguas), puerta cerrada/abierta, esfera dorada. No había textura de musgo en los archivos
adjuntos. Las de pared llevan mipmaps y filtrado anisotrópico si el controlador lo ofrece. El musgo es verde oscuro sobre ladrillo
beis, el suelo es granito gris y los remates mármol claro: se mantiene el contraste entre pasillos y muros.

## Cámara en tercera persona (`camara_tercera.py`)

El punto de mira y el objetivo siguen al jugador sin retardo; solo se suaviza la longitud de la «pértiga»: se acorta rápido (k = 16/s)
cuando hay un muro detrás y se alarga despacio (k = 3.5/s) cuando hay sitio. Se miden también dos rayos laterales (±14°) para anticipar
las esquinas al girar. Para que la interpolación **nunca** deje ver a través de un muro, la longitud final se recorta siempre a la
distancia libre medida ese mismo fotograma (margen 0.12 > diagonal del plano cercano, 0.084). Pegado a un muro, la cámara converge a
la posición de primera persona (y deja de dibujar el personaje) en lugar de quedar dentro de la pared como en la v5.

## Correcciones respecto a la v5 (documentadas)

* **OBJ con orientación inconsistente**: `esfera.obj` tiene 224/224 triángulos y `cubo.obj` 6/12 con el orden de vértices contrario a su
  normal (medido). Con GL_CULL_FACE habrían desaparecido caras; `obj.py` reorienta cada triángulo y la v6 activa el descarte de caras
  traseras.
* **Cargador OBJ** descartaba en silencio las caras que no eran triángulos y exigía `v/t/n`.
* **Textura de ladrillo deformada**: la v5 estiraba un azulejo cuadrado sobre un muro de 1 × 1.9. Ahora es 1 azulejo = 1 × 1.9 unidades.
* **`transitable`** usaba `int()` (redondea hacia cero con negativos) en lugar de `floor`.
* **Cámara de tercera persona** podía quedar dentro de un muro pegada a una pared (distancia mínima fija de 0.45).
* **`cargar_textura`** no fijaba `GL_UNPACK_ALIGNMENT`: con anchos no múltiplos de 4 la imagen se desplazaba.
* **Suelo con solo 8 vértices**: con la luz local la iluminación por vértice lo dejaba casi a oscuras; ahora es una quad por celda.
* **Rastro y aristas en modo inmediato** (`glBegin`/`glVertex` por fotograma, creciendo sin límite) pasan a buffers.
* Se evita depender de **GLU** (`gluPerspective`/`gluLookAt` → `vistas.py`).
* La partida empieza **mirando por el pasillo** de la entrada (la v5 empezaba mirando a un muro). La cámara cenital muestra solo lo
  explorado (lo exige el mapa explorado); el recorrido sigue en amarillo y el jugador en azul.

No se copian los archivos del ejemplo VBOs que la v5 no usaba (`camara.py`, `usuario.py`, `utilidades.py`, `luces.py`, `cilindro.obj`).

## Estructura

```
Laberinto3D_v6/
  README.md  requirements.txt
  Python/
    main.py                  punto de entrada (argumentos, sys.path)
    juego.py                 ventana, entrada, orden de dibujo, ciclo de vida
    partida.py  objetos.py   lógica: partida, jugador, esferas, puerta, cronómetro (sin OpenGL)
    laberinto.py             generación, alcanzabilidad, esferas, musgo, colisiones
    exploracion.py           mapa explorado (regla de revelado y colores)
    dificultad.py            parámetros de las tres dificultades
    geometria.py  obj.py     geometría en CPU: muros, suelo, aristas, OBJ -> (vértices, índices)
    buffers.py               MallaGL (VBO+EBO), LoteDinamico, RutaGL
    escena.py  modelo.py     geometría estática en GPU y modelos OBJ dibujables
    camara_tercera.py  vistas.py   cámara de 3ª persona; proyección y vista sin GLU
    hud.py                   interfaz 2D: texto, panel, brújula, minimapa, pantalla final
    ambiente_terror.py       modo terror: shaders, linterna, texturas sucias, viñeta/grano, sonido
    texturas.py  texturas_procedurales.py  transformaciones.py  configuracion.py
    modelos/ (cubo.obj, esfera_lr.obj)   texturas/ (7 PNG de la v5)
  pruebas/
    verificar_logica.py  verificar_gl.py  verificar_terror.py  verificar_arranque.py   capturas/
```

## Pruebas

```bash
python pruebas/verificar_logica.py                                           # sin pantalla: lógica y geometría (18 pruebas)
xvfb-run -a -s "-screen 0 1280x720x24" python pruebas/verificar_gl.py        # aspecto clásico con contexto OpenGL (17 pruebas) + capturas
xvfb-run -a -s "-screen 0 1280x720x24" python pruebas/verificar_terror.py    # modo terror: shader, linterna, texturas, fallback (18 pruebas)
xvfb-run -a -s "-screen 0 1280x720x24" python pruebas/verificar_arranque.py  # compila, arranca main.py y el bucle real
```

(`xvfb-run` solo hace falta en servidores sin pantalla; con escritorio se ejecutan directamente.)

Resultado de la última ejecución: **18/18, 17/17, 18/18 (terror) y 3/3**. Cubren: laberintos conexos y puerta en callejón (3 dificultades × 8 semillas);
esferas únicas, transitables y alcanzables con la puerta cerrada (640 esferas); caras laterales = exactamente las pared-suelo y ninguna entre
muros ni hacia fuera; normales unitarias, orientación antihoraria coherente con la normal y UV sin deformación; reconstrucción exacta de
los vértices compartidos; tipos `float32`/`uint16`; tamaños reales de VBO/EBO en la GPU; `glDrawElements` sin `glDrawArrays` en primera
persona; 12 pulsaciones de N sin acumular buffers (29 → 29) ni texturas (16 → 16) y sin crear buffers por fotograma; imagen idéntica con y
sin `GL_CULL_FACE` (como mucho 2–3 píxeles de silueta de 921 600 en las ejecuciones; tolerancia 16, una cara invertida cambiaría miles) en 30 vistas de las tres cámaras; **0 píxeles de fondo visibles** en 120 vistas
(1ª y 3ª persona, las tres dificultades) donde solo debe haber suelo o muro, y en 200 vistas de tercera persona pegado a paredes; partida
completa (esferas una sola vez → puerta se abre → salida, con el cronómetro congelado) y reinicio con N; la puerta cerrada o a medio
abrir no deja pasar; cambio de dificultad con F1–F3/4–6; mapa explorado (regla, sin ver a través de paredes, reinicio); brújula (N
centrada a 0°/360°, distinta a 45/90/180/270°); cámara de tercera persona en 16 200 fotogramas aleatorios con giros bruscos (el segmento
jugador-cámara siempre libre; el salto máximo de distancia por fotograma al girar baja de 1.66 a 0.20); liberación de todos los buffers y texturas
al cerrar (29 buffers y 15 texturas → 0). Las capturas de `pruebas/capturas/` salen de esas ejecuciones.

Modo terror (`verificar_terror.py`): shader enlazado y activo por defecto; brillo medio ≈ 5 veces menor que el clásico; linterna con
cono (centro más brillante que las esquinas) y apagable; T e I; **el modo clásico es idéntico píxel a píxel tras alternar T** (12 vistas
con HUD) y su escena 3D es idéntica a la de la versión anterior (24 vistas, comparadas contra el commit previo); cenital legible; texto
del HUD sin cambios de color; esferas (5 000 px dorados) y portal brillan con la linterna apagada; parpadeo, ráfagas y apagones de 0.2–0.5 s
(15 min simulados); balanceo ≤ 0.018 y nulo en clásico; texturas sucias del mismo tamaño, más oscuras, menos saturadas y sin costura;
estado GL limpio (programa 0, mezcla, máscara de profundidad, texturas y pilas); fallback con un shader roto (aviso por consola y modo
clásico); el sonido se desactiva solo sin dispositivo de audio; liberación total (shader incluido).

**Lo que NO se ha podido comprobar** (dilo expresamente quien lo ejecute en su máquina):
* Todo el dibujo se probó con **Mesa llvmpipe (renderizado por software) bajo Xvfb**, OpenGL 4.5 compatibilidad. No se ha probado en una GPU
  real, en Windows ni en macOS. Los tiempos de fotograma (≈ 13 ms a 1280×720 en software) solo son orientativos: no hay medición de
  rendimiento en GPU, y la comparación de llamadas de dibujo con la v5 es un cálculo (la v5 no se pudo ejecutar allí por faltar GLU).
* No hubo una persona jugando: el ratón (captura y sensibilidad), el teclado real y la sensación de la cámara se simularon con eventos de
  pygame y estados programáticos. Conviene dar una vuelta por las tres dificultades y revisar el aspecto del musgo y de la puerta a ojo.
* Modo terror: el shader solo se ha compilado con Mesa (GLSL 1.20 en compatibilidad); en otras GPU/controladores (Intel antiguas, macOS con
  contexto 2.1) puede comportarse distinto: en ese caso el juego vuelve al modo clásico, pero ese camino solo se probó con un shader roto
  a propósito. El sonido se probó con el controlador de audio «dummy» (se ejecuta, pero no se ha oído), y el nivel de oscuridad, el
  parpadeo y el grano son subjetivos: ajusta `TERROR_*` a tu gusto. El coste en GPU real no está medido (Mesa por software: ≈ 12 → 16 ms).
* La textura de musgo se ha creado nueva (no había una en los adjuntos); su aspecto es subjetivo.
