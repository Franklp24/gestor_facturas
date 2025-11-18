import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

# Configuración de la base de datos
DATABASE = 'facturas.db'

def get_db():
    """Función para obtener una conexión a la base de datos."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
    return conn

def init_db():
    """Inicializa la base de datos (crea la tabla si no existe) con las columnas correctas."""
    conn = get_db()
    # Definición de la tabla con la columna 'fecha'
    conn.execute('''
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT NOT NULL, 
            estado TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def reset_db():
    """ELIMINA Y RECREA la tabla facturas. Se usa para corregir errores de esquema antiguos."""
    conn = get_db()
    conn.execute('DROP TABLE IF EXISTS facturas')
    conn.commit()
    conn.close()
    init_db()
    print("Database reset and re-initialized.")
    
# Inicializa la aplicación Flask
app = Flask(__name__)
# Configura una clave secreta. Es necesaria para usar flash() o sesiones.
app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_por_defecto_muy_larga_y_segura_debes_cambiarla')

# Inicializa la base de datos (la crea si no existe)
init_db()

# --- Rutas de la Aplicación ---

@app.route('/')
def index():
    """Muestra la lista de facturas, con corrección automática de esquema."""
    conn = get_db()
    
    # Intenta hacer la consulta. Si falla por la columna 'fecha', resetea la DB.
    try:
        facturas = conn.execute('SELECT * FROM facturas ORDER BY fecha DESC').fetchall()
    except sqlite3.OperationalError as e:
        # Si el error es "no such column: fecha", reseteamos la base de datos.
        if "no such column: fecha" in str(e):
            print("Error de esquema detectado. La tabla será recreada.")
            reset_db()
            # Intenta la consulta de nuevo
            facturas = conn.execute('SELECT * FROM facturas ORDER BY fecha DESC').fetchall()
        else:
            # Si es otro error de SQLite, lo lanzamos.
            raise e
            
    conn.close()
    return render_template('index.html', facturas=facturas)

@app.route('/agregar', methods=['POST'])
def agregar_factura():
    """Agrega una nueva factura a la base de datos."""
    if request.method == 'POST':
        cliente = request.form['cliente']
        monto = request.form['monto']
        fecha = request.form['fecha']
        estado = request.form['estado']

        if not cliente or not monto or not fecha or not estado:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('index'))

        conn = get_db()
        conn.execute('INSERT INTO facturas (cliente, monto, fecha, estado) VALUES (?, ?, ?, ?)',
                     (cliente, monto, fecha, estado))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

@app.route('/eliminar/<int:factura_id>')
def eliminar_factura(factura_id):
    """Elimina una factura por ID."""
    conn = get_db()
    conn.execute('DELETE FROM facturas WHERE id = ?', (factura_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- CONFIGURACIÓN DE INICIO PARA ENTORNO LOCAL Y RENDER ---

if __name__ == '__main__':
    # Esta configuración lee la variable PORT que proporciona Render.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
