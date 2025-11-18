import os

# gunicorn_config.py

# Bind: Especifica la dirección y el puerto en el que Gunicorn escuchará.
# Utilizamos 0.0.0.0 para escuchar en todas las interfaces de red
# y el puerto $PORT que Render proporciona automáticamente.
bind = "0.0.0.0:{}".format(os.environ.get("PORT", "5000"))

# Workers: Número de procesos que Gunicorn usará.
# 2-4 workers es una buena práctica para empezar.
workers = 4

# Timeout: Tiempo máximo que un worker puede tardar en responder.
timeout = 60 

# Log Level: Nivel de detalle de los logs.
loglevel = 'info'
