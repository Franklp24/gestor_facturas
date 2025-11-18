import os

# gunicorn_config.py
# Bind: Especifica la dirección y el puerto.
# Utilizamos el puerto 8000 que es el estándar de Render
bind = "0.0.0.0:8000"

# **CRUCIAL: Archivo de aplicación:** 'nombre_archivo:nombre_variable_app'
# Le dice a Gunicorn que cargue la aplicación 'app' desde el archivo 'app.py'
module = "app:app" 

# Workers: Número de procesos que Gunicorn usará.
workers = 4

# Timeout: Tiempo máximo que un worker puede tardar en responder.
timeout = 60

# Log Level: Nivel de detalle de los logs.
loglevel = 'info'
