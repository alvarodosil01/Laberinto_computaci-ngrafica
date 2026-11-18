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
TERCERA_K_ALEJAR     = 5.0     # Recupera la distancia suavemente al salir de una esquina.
TERCERA_ABANICO_GRADOS = 14.0  # Rayos laterales para anticipar muros al girar.

# Interfaz.
DURACION_MENSAJE = 3.0


# ======================================================================================
# Ambiente de terror (ambiente_terror.py). Tecla T: modo terror / modo clásico.
# ======================================================================================
TERROR_ACTIVO_AL_INICIO = True      # True: el juego arranca en modo terror (T alterna con el aspecto clásico).

# --- Oscuridad y niebla ---
TERROR_COLOR_FONDO     = (0.010, 0.014, 0.026)   # Color de fondo y de la niebla (casi negro azulado).
TERROR_AMBIENTE        = 0.045                    # Luz ambiente en 1ª/3ª persona (0 = negro total; 0.03-0.06 recomendado).
TERROR_AMBIENTE_CENITAL = 0.42                    # Ambiente en la cámara cenital (2), para que el mapa siga siendo legible.
TERROR_NIEBLA_ALCANCE  = 8.0                      # Distancia (unidades) a la que solo se ve ~5 % de la escena. Menor = más densa.

# --- Linterna (tecla I la enciende/apaga en modo terror) ---
TERROR_LINTERNA_ENCENDIDA = True                  # Estado inicial de la linterna.
TERROR_LINTERNA_ANGULO_INT = 13.0                 # Semiángulo (grados) del cono con intensidad plena.
TERROR_LINTERNA_ANGULO_EXT = 27.0                 # Semiángulo (grados) donde la luz llega a cero (borde suave entre ambos).
TERROR_LINTERNA_INTENSIDAD = 2.2                  # Potencia de la linterna. Súbela si queda demasiado oscuro.
TERROR_LINTERNA_ATEN_LINEAL = 0.16                # Atenuación por distancia (término lineal).
TERROR_LINTERNA_ATEN_CUAD   = 0.07                # Atenuación por distancia (término cuadrático).

# --- Parpadeo de la linterna ---
TERROR_PARPADEO_RUIDO     = 0.06                  # Fluctuación continua de intensidad (0.06 = ±6 %).
TERROR_PARPADEO_INTERVALO = (5.0, 14.0)           # Segundos (mín, máx) entre ráfagas de parpadeo fuerte.
TERROR_PARPADEO_RAFAGA    = 0.35                  # Duración (s) de cada ráfaga de parpadeo.
TERROR_APAGON_CADA        = 75.0                  # Segundos de media entre apagones breves (0 = sin apagones).
TERROR_APAGON_DURACION    = (0.2, 0.5)            # Duración (s) mínima y máxima del apagón.

# --- Luces propias y halos ---
TERROR_EMISION_FACTOR = 3.0                       # Multiplicador del brillo propio de las esferas (usan el material emisivo).
TERROR_EMISION_PORTAL = (0.9, 1.3, 1.0)           # Brillo propio del portal de la puerta abierta (verde).
TERROR_EMISION_MARCAS = (0.10, 0.10, 0.10)        # Brillo tenue de las marcas de entrada y salida (orientación).
TERROR_HALO           = True                      # Halo aditivo alrededor de las esferas (se ven de lejos entre la niebla).
TERROR_HALO_TAMANO    = 1.0                       # Tamaño (unidades) del halo.
# Tonos de la tecla L en modo terror (mismo orden que TONOS: blanco, cálido, frío, verde, violeta): fríos y enfermizos.
TERROR_TONOS = ((0.78, 0.88, 0.95), (0.95, 0.85, 0.55), (0.45, 0.65, 1.00), (0.50, 0.95, 0.55), (0.70, 0.50, 0.85))

# --- Texturas sucias (se generan al arrancar; no cambian tamaño ni UV) ---
TERROR_TEX_DESATURACION = 0.45                    # 0 = color original, 1 = escala de grises.
TERROR_TEX_OSCURECER    = 0.80                    # Multiplicador de brillo del albedo.
TERROR_TEX_HOLLIN       = 0.55                    # Oscurecimiento de la base de las paredes (0-1).
TERROR_TEX_HUMEDAD      = 0.50                    # Manchas de humedad (0-1).
TERROR_TEX_OXIDO        = 0.35                    # Vetas de óxido en las paredes (0-1).
TERROR_TEX_GRIETAS      = 9                       # Número de grietas/rayones por textura.
TERROR_RETRO            = True                    # GL_NEAREST al ampliar (píxeles visibles); mipmaps al reducir.

# --- Pantalla ---
TERROR_VINETA = 0.80                              # Oscurecimiento de los bordes (0 = sin viñeta, 1 = muy fuerte).
TERROR_GRANO  = 0.07                              # Opacidad del grano de película (0 = sin grano).
TERROR_GRANO_TAMANO = 2                           # Tamaño en píxeles de cada grano.
TERROR_BALANCEO_AMPLITUD    = 0.018               # Balanceo vertical de la cámara al caminar (unidades). 0 = sin balanceo.
TERROR_BALANCEO_FRECUENCIA  = 1.9                 # Pasos por segundo.
TERROR_RESPIRACION_AMPLITUD = 0.004               # Respiración de la cámara al estar quieto (unidades).

# --- Sonido generado por código (se desactiva solo si no hay dispositivo de audio) ---
TERROR_VOLUMEN         = 0.5                      # 0 = sin sonido. Volumen general (0-1).
TERROR_LATIDO_BPM      = (52.0, 118.0)            # Latidos por minuto con la linterna encendida / en la oscuridad.
