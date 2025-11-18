import sqlite3
import os # <-- ¡AQUÍ DEBE IR!
from flask import Flask, render_template, request, redirect, url_for

# Configuración de la base de datos
DATABASE = 'facturas.db'

def get_db():
    """Función para obtener una conexión a la base de datos."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
    return conn

def init_db():
    """Inicializa la base de datos (crea la tabla si no existe)."""
    conn = get_db()
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

# Inicializa la base de datos al inicio de la aplicación
# NOTA: En Render, la base de datos SQLite se reiniciará cada vez que la aplicación se apague.
# Esto es normal en plataformas gratuitas que no tienen un servicio de base de datos persistente.
# Para persistencia REAL, se necesitaría un servicio de PostgreSQL, que Render también ofrece (pero puede requerir tarjeta).
init_db()

# Inicializa la aplicación Flask
app = Flask(__name__)

# --- Rutas de la Aplicación ---

@app.route('/')
def index():
    """Muestra la lista de facturas."""
    conn = get_db()
    facturas = conn.execute('SELECT * FROM facturas ORDER BY fecha DESC').fetchall()
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
