# configuracion.py
'''
Es este fichero se definen las constantes que establecen la configuración general de la aplicación
'''

# Definición de colores
COLOR_ROJO      =  (1.0, 0.0, 0.0)     # Color rojo primario
COLOR_VERDE     =  (0.0, 1.0, 0.0)     # Color verde primario
COLOR_AZUL      =  (0.0, 0.0, 1.0)     # Color azul primario
COLOR_AMARILLO  =  (1.0, 1.0, 0.0)     # Color amarillo
COLOR_NARANJA   =  (1.0, 0.5, 0.0)     # Color naranja
COLOR_BLANCO    =  (1.0, 1.0, 1.0)     # Color blanco
COLOR_NEGRO     =  (0.0, 0.0, 0.0)     # Color negro

# Configuración de la ventana gráfica
SCREEN_WIDTH        = 1280                           # Anchura de la ventana gráfica
SCREEN_HEIGHT       = 720                           # Altura de la ventana gráfica
SCREEN_ASPECT_RATIO = SCREEN_WIDTH / SCREEN_HEIGHT  # Relación de aspecto de la ventana gráfica

# Configuración de la proyección
FOV         = 45    # (Field Of View) Campo o ángulo de vision desde el centro de la cámara.
NEAR_PLANE  = 0.1   # Distancia del plano más cercano a la cámara.
FAR_PLANE   = 50    # Distancia del plano más lejano a la cámara.

# Configuración del bucle de renderizado
FPS = 60
MILLISECONDS_PER_SECOND = 1000.0    # Número de milisegundos en un segundo.

# Configuración de la interacción del usuario
BOTON_IZQUIERDO_RATON   = 1     # ID del botón izquierdo del ratón.
SENSIBILIDAD_ROTACION   = 0.2   # Sensibilidad a la rotación cuando se utiliza el ratón.
SENSIBILIDAD_ZOOM       = 0.3   # Sensibilidad al zoom cuando se usa el ratón.
RADIO_MAX               = 15.0  # Distancia máxima de la cámara al origen cuando se hace zoom.
RADIO_MIN               = 1.0   # Distancia mínima de la cámara al origen cuando se hace zoom.
INVERTIR_CONTROLES      = -1    # Ajustar a 1 o -1 para invertir el sentido de los controles cuando se rota la escena.
VELOCIDAD_ROTACION      = 135   # Velocidad de rotación cuando se usa el teclado, en grados por segundo.
VELOCIDAD_ZOOM          = 10    # Velocidad de zoom cuando se usa el teclado, en unidades por segundo.

# Configuración de los ejes
LONGITUD_EJE         = 4                # Longitud de los segmentos de recta que representan los ejes
EJE_X_MIN            = -LONGITUD_EJE    # Coordenada mínima del eje X
EJE_X_MAX            =  LONGITUD_EJE    # Coordenada máxima del eje X
EJE_Y_MIN            = -LONGITUD_EJE    # Coordenada mínima del eje Y
EJE_Y_MAX            =  LONGITUD_EJE    # Coordenada máxima del eje Y
EJE_Z_MIN            = -LONGITUD_EJE    # Coordenada mínima del eje Z
EJE_Z_MAX            =  LONGITUD_EJE    # Coordenada máxima del eje Z
COLOR_EJE_X          =  COLOR_ROJO      # Color del eje X
COLOR_EJE_Y          =  COLOR_VERDE     # Color del eje Y
COLOR_EJE_Z          =  COLOR_AZUL      # Color del eje Z
EJE_FLECHA_BASE      =  0.1             # Radio de la base de la flecha
EJE_FLECHA_PUNTA     =  0.0             # Radio de la punta de la flecha
EJE_FLECHA_LONGITUD  =  0.3             # Longitud de la flecha
EJE_FLECHA_REBANADAS =  10              # Número de subdivisiones en el eje Z de la flecha
EJE_FLECHA_PILAS     =  10              # Nümero de subdivisiones en el eje Y de la flecha

# Configuración de la rejilla
REJILLA_COLOR       =   COLOR_BLANCO    # Color de las líneas de la rejilla
REJILLA_TAMANO      =   3               # Tamaño de la rejilla en cada eje (positivo y negativo)
REJILLA_PASO        =   1               # Tamaño de cada celda de la rejilla

# ======================================================================================
# Laberinto 3D v6: parámetros nuevos (todo lo anterior se conserva tal cual de la v5)
# ======================================================================================

# Proyección del juego (la v5 usaba 100 como plano lejano en main.py; aquí queda con nombre).
FAR_PLANE_JUEGO = 100

# Geometría del laberinto (unidades de mundo: una celda mide 1 x 1).
ALTURA_PARED       = 1.9     # Altura de los muros.
ALTURA_REMATE      = 0.08    # Franja de mármol que remata cada muro.
FRACCION_MUSGO     = 0.35    # Fracción aproximada de muros con musgo.
SEPARACION_LINEAS  = 0.004   # Separación de las aristas oscuras respecto a la cara (evita z-fighting).

# Esferas coleccionables.
ESFERA_ESCALA        = 0.42    # Diámetro de la esfera (el modelo OBJ tiene radio 0.5).
ESFERA_Y_BASE        = 0.55    # Altura media del centro de la esfera.
ESFERA_AMPLITUD      = 0.10    # Amplitud del movimiento vertical.
ESFERA_FRECUENCIA    = 0.55    # Oscilaciones verticales por segundo.
ESFERA_VEL_ROTACION  = 110.0   # Grados por segundo.
ESFERA_RADIO_RECOGIDA = 0.50   # Distancia horizontal a la que se recoge.

# Puerta de salida.
PUERTA_VELOCIDAD  = 1.7     # Unidades por segundo con que se hunde en el suelo al abrirse.
PUERTA_UMBRAL     = 0.15    # Altura máxima de la puerta (sobre el suelo) con la que ya se puede pasar.

# Movimiento del jugador (igual que en la v5).
VELOCIDAD_JUGADOR   = 2.8
RADIO_JUGADOR       = 0.18

# Cámara en tercera persona.
TERCERA_DIST_MAX     = 2.4     # Longitud máxima de la "pértiga" de la cámara.
TERCERA_MARGEN       = 0.12    # Holgura de la cámara respecto a los muros (> diagonal del plano cercano).
TERCERA_K_ACERCAR    = 16.0    # Rapidez con que la cámara se acerca al jugador cuando hay un muro detrás.
TERCERA_K_ALEJAR     = 3.5     # Rapidez con que se aleja de nuevo cuando hay sitio.
TERCERA_ABANICO_GRADOS = 14.0  # Rayos laterales para anticipar muros al girar.

# Interfaz.
DURACION_MENSAJE = 3.0
