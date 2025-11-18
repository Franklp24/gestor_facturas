import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, g
from datetime import datetime, timedelta

# --- Configuración de la base de datos ---
DATABASE = 'facturas.db'

# --- Configuración de Flask y Rutas ---
# La inicialización de la app DEBE ir antes de usarla para decoradores (@app.route)
app = Flask(__name__)

# ------------------------------------------------------------------
# FUNCIONES AUXILIARES DE JINJA:
# Necesarias para el procesamiento de fechas y vencimientos en index.html
# ------------------------------------------------------------------
def inject_globals():
    """Inyecta funciones y filtros customizados de fecha en el contexto de Jinja."""
    
    def now_context():
        """Retorna la fecha y hora actual (objeto datetime)."""
        return datetime.now()

    def to_date_filter(value):
        """Convierte un string (YYYY-MM-DD) a un objeto datetime."""
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d')
        except (ValueError, TypeError):
            return None # Manejar strings no válidos

    # Devuelve un diccionario con las funciones y filtros que se inyectarán
    return dict(now=now_context, to_date=to_date_filter)

# Registra el context processor para que 'now()' y '| to_date' estén disponibles en todas las plantillas
app.context_processor(inject_globals) 


# --- Funciones de DB ---
def get_db():
    # Inicializa o recupera la conexión a la base de datos
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Habilita el acceso por nombres de columna (diccionarios)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    # Cierra la conexión a la DB al finalizar la solicitud
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def inicializar_db():
    # Crea la tabla de facturas si no existe
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS facturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                codigo_producto TEXT NOT NULL,
                precio REAL NOT NULL,
                fecha_expira TEXT NOT NULL,
                email_cliente TEXT
            );
        ''')
        db.commit()

@app.route('/')
def index():
    """Muestra la lista de facturas, con corrección automática de esquema."""
    inicializar_db() # Asegura que la DB exista
    db = get_db()
    
    # 1. Obtener facturas para la tabla
    cursor = db.execute('SELECT * FROM facturas ORDER BY fecha_expira ASC')
    facturas = cursor.fetchall()
    
    # 2. Calcular alertas de vencimiento
    hoy = datetime.now().date()
    siete_dias = hoy + timedelta(days=7)
    
    alertas = 0
    for factura in facturas:
        try:
            fecha_expira = datetime.strptime(factura['fecha_expira'], '%Y-%m-%d').date()
            if hoy <= fecha_expira <= siete_dias:
                alertas += 1
        except ValueError:
            # Manejar fechas mal formateadas si las hay
            pass

    return render_template('index.html', facturas=facturas, alertas=alertas)

# RUTA NUEVA: Para manejar el envío del formulario (POST)
@app.route('/guardar_factura', methods=['POST'])
def guardar_factura():
    """Inserta una nueva factura en la base de datos."""
    if request.method == 'POST':
        # 1. Obtener datos del formulario
        nombre = request.form['nombre']
        codigo = request.form['codigo_producto']
        precio = float(request.form['precio'])
        fecha_expira = request.form['fecha_expira']
        email = request.form['email_cliente']
        
        # 2. Guardar en la DB
        try:
            db = get_db()
            db.execute(
                'INSERT INTO facturas (nombre, codigo_producto, precio, fecha_expira, email_cliente) VALUES (?, ?, ?, ?, ?)',
                (nombre, codigo, precio, fecha_expira, email)
            )
            db.commit()
            # Redirigir al inicio después de guardar (para evitar reenvío)
            return redirect(url_for('index'))
        except Exception as e:
            # En caso de error (ej. precio no es un número), redirige con mensaje
            print(f"Error al guardar la factura: {e}")
            return f"Ocurrió un error al guardar la factura: {e}", 500

# --- Ejecución de la aplicación ---
if __name__ == '__main__':
    # Esta parte solo se ejecuta en local, NO en Render
    inicializar_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
