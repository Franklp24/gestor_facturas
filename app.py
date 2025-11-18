import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, g
from datetime import datetime, timedelta

# --- Configuración de la base de datos ---
DATABASE = 'facturas.db'

# --- Configuración de Flask y Rutas ---
app = Flask(__name__)

# ------------------------------------------------------------------
# FUNCIONES Y FILTROS AUXILIARES DE JINJA:
# Separamos la inyección de la función global (now) y el filtro (to_date)
# ------------------------------------------------------------------

def to_date_filter(value):
    """Convierte un string (YYYY-MM-DD) a un objeto datetime."""
    if not value:
        return None
    try:
        # Asume que el formato guardado en DB es YYYY-MM-DD
        return datetime.strptime(value, '%Y-%m-%d')
    except (ValueError, TypeError):
        # En caso de que el dato en DB sea inválido
        return None 

def now_context():
    """Retorna la fecha y hora actual (objeto datetime)."""
    return datetime.now()

# 1. Registro del Filtro Customizado (MUY IMPORTANTE para el error 'to_date')
# Utilizamos el decorador para asegurarnos de que se registra correctamente
app.add_template_filter(to_date_filter, 'to_date')

# 2. Registro del Context Processor para la función global (now())
@app.context_processor
def inject_globals():
    """Inyecta la función now() en el contexto de Jinja."""
    # Retornamos un diccionario con las funciones que se inyectarán
    return dict(now=now_context) 


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
    """Muestra la lista de facturas."""
    # Aseguramos que la DB y la tabla existan
    inicializar_db() 
    db = get_db()
    
    # 1. Obtener facturas para la tabla
    cursor = db.execute('SELECT * FROM facturas ORDER BY fecha_expira ASC')
    facturas = cursor.fetchall()
    
    # 2. Calcular alertas de vencimiento (Lógica en Python)
    hoy = datetime.now().date()
    siete_dias = hoy + timedelta(days=7)
    
    alertas = 0
    for factura in facturas:
        fecha_str = factura['fecha_expira'] if factura and 'fecha_expira' in factura else None
        
        if fecha_str:
            try:
                fecha_expira = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                if hoy <= fecha_expira <= siete_dias:
                    alertas += 1
            except ValueError:
                # Si el formato es incorrecto, ignoramos
                pass

    # 3. Renderizar la plantilla (la plantilla usará el filtro y la función que acabamos de registrar)
    return render_template('index.html', facturas=facturas, alertas=alertas)

@app.route('/guardar_factura', methods=['POST'])
def guardar_factura():
    """Inserta una nueva factura en la base de datos y redirige."""
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            codigo = request.form['codigo_producto']
            precio = float(request.form['precio'])
            fecha_expira = request.form['fecha_expira']
            email = request.form.get('email_cliente', '') 
        except ValueError:
            return "Error: El precio debe ser un número válido.", 400
        except KeyError as e:
            return f"Error: Falta un campo requerido en el formulario: {e}", 400
        
        try:
            db = get_db()
            db.execute(
                'INSERT INTO facturas (nombre, codigo_producto, precio, fecha_expira, email_cliente) VALUES (?, ?, ?, ?, ?)',
                (nombre, codigo, precio, fecha_expira, email)
            )
            db.commit()
            return redirect(url_for('index'))
        except Exception as e:
            print(f"Error al guardar la factura: {e}")
            return f"Ocurrió un error de base de datos al guardar: {e}", 500

# --- Ejecución de la aplicación ---
if __name__ == '__main__':
    # Esta parte solo se ejecuta en local, NO en Render
    inicializar_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
