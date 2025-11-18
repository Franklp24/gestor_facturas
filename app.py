import os
import sqlite3
from datetime import datetime, date
from flask import Flask, render_template, g, request, redirect, url_for, flash

# --- Constantes y Configuración ---
DATABASE = 'facturas.db'
# Nota: La clave secreta debe estar en las Environment Variables de Render
SECRET_KEY = os.environ.get('SECRET_KEY', 'una_clave_secreta_fuerte_y_unica_de_backup')
DATABASE_VERSION = 1

app = Flask(__name__)
# Configuración Flask
app.config.from_object(__name__)

# --- Funciones de Base de Datos ---

def get_db():
    """Obtiene la conexión a la base de datos para la solicitud actual."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Permite acceder a las columnas por nombre
        db.row_factory = sqlite3.Row
    return db

def cerrar_db(exception):
    """Cierra la conexión a la base de datos al finalizar la solicitud."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def inicializar_db():
    """Crea la tabla 'facturas' si no existe."""
    conn = None
    try:
        # Crea la base de datos si no existe
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Crear la tabla de facturas SOLO SI NO EXISTE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                codigo_producto TEXT NOT NULL,
                precio REAL NOT NULL,
                fecha_expira TEXT NOT NULL,
                email_cliente TEXT NOT NULL
            )
        """)
        
        # Crear tabla de versión (si es necesario)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_version (version INTEGER)
        """)
        
        # Verificar si ya existe el registro de versión antes de insertar
        cursor.execute("SELECT COUNT(*) FROM db_version")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO db_version (version) VALUES (?)", (DATABASE_VERSION,))
        
        conn.commit()
        print("Esquema de base de datos verificado y listo.")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")
    finally:
        if conn:
            conn.close()

# Llamada inicial: Asegura que la DB exista antes de que Flask reciba solicitudes.
# Esto es crucial para el arranque.
inicializar_db()

# Se asegura de que la DB se cierre después de cada solicitud
app.teardown_appcontext(cerrar_db)

# --- Lógica de la Aplicación ---

def obtener_alertas(conn):
    """Devuelve las facturas que vencen en los próximos 7 días."""
    hoy = date.today().isoformat()
    cursor = conn.cursor()
    
    # Consulta: facturas que vencen hoy o en los próximos 7 días.
    cursor.execute("""
        SELECT * FROM facturas 
        WHERE date(fecha_expira) BETWEEN date(?) AND date('now', '+7 day')
        ORDER BY fecha_expira ASC
    """, (hoy,))
    
    return cursor.fetchall()

def obtener_facturas(conn):
    """Devuelve todas las facturas ordenadas por fecha de expiración."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facturas ORDER BY fecha_expira DESC")
    return cursor.fetchall()

@app.route('/', methods=['GET', 'POST'])
def index():
    """Muestra el formulario y la lista de facturas, y maneja el envío del formulario."""
    
    conn = get_db()
    
    if request.method == 'POST':
        # ... (La lógica de POST es la misma)
        nombre = request.form['nombre']
        codigo_producto = request.form['codigo_producto']
        precio = request.form['precio']
        fecha_expira = request.form['fecha_expira']
        email_cliente = request.form['email_cliente']

        # Validación básica de datos
        if not all([nombre, codigo_producto, precio, fecha_expira, email_cliente]):
            flash('Error: Todos los campos son obligatorios.', 'error')
            return redirect(url_for('index'))
        
        try:
            precio = float(precio)
            # Validación de formato de fecha simple (YYYY-MM-DD)
            datetime.strptime(fecha_expira, '%Y-%m-%d')
        except ValueError:
            flash('Error: El formato de Precio o Fecha es incorrecto. Use YYYY-MM-DD.', 'error')
            return redirect(url_for('index'))

        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO facturas (nombre, codigo_producto, precio, fecha_expira, email_cliente)
                VALUES (?, ?, ?, ?, ?)
            """, (nombre, codigo_producto, precio, fecha_expira, email_cliente))
            conn.commit()
            flash('Factura guardada con éxito.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error al guardar la factura: {e}', 'error')
        
        return redirect(url_for('index'))

    # Método GET (para mostrar la página)
    facturas = obtener_facturas(conn)
    alertas = obtener_alertas(conn)
    
    # Formateo de fechas para presentación (DD/MM/AAAA)
    facturas_con_formato = []
    for factura in facturas:
        f = dict(factura)
        try:
            fecha_obj = datetime.strptime(f['fecha_expira'], '%Y-%m-%d')
            f['fecha_expira_format'] = fecha_obj.strftime('%d/%m/%Y')
        except ValueError:
            f['fecha_expira_format'] = f['fecha_expira'] 
        facturas_con_formato.append(f)
    
    alertas_con_formato = []
    for alerta in alertas:
        a = dict(alerta)
        try:
            fecha_obj = datetime.strptime(a['fecha_expira'], '%Y-%m-%d')
            a['fecha_expira_format'] = fecha_obj.strftime('%d/%m/%Y')
        except ValueError:
            a['fecha_expira_format'] = a['fecha_expira']
        alertas_con_formato.append(a)
    
    return render_template('index.html', facturas=facturas_con_formato, alertas=alertas_con_formato)

# --- CONFIGURACIÓN DE INICIO PARA ENTORNO LOCAL Y RENDER ---

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
