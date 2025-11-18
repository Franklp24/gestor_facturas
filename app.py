import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, flash
# Importamos date y datetime para la comparación de fechas
from datetime import datetime, date 

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
            estado TEXT NOT NULL -- Usaremos 'Pendiente' o 'Pagada'
        )
    ''')
    conn.commit()
    conn.close()

# --- Bloque de Inicialización Forzada ---
if os.path.exists(DATABASE):
    os.remove(DATABASE)
    print(f"Archivo de base de datos antiguo '{DATABASE}' eliminado y será recreado.")
    
init_db()
# ----------------------------------------

# Inicializa la aplicación Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_para_flash_messages')

# --- Lógica de Cálculo de Estado ---
def calcular_estado(factura):
    """
    Calcula el estado dinámico (Pagada, Vencida o Pendiente) de la factura.
    El estado 'Pagada' es manual, 'Vencida' y 'Pendiente' son automáticos por fecha.
    """
    # 1. Si ya está marcada como 'Pagada' en la DB, ese es su estado final.
    if factura['estado'] == 'Pagada':
        return 'Pagada'
    
    # 2. Si no está Pagada, comparamos la fecha de vencimiento.
    try:
        # Convertir la fecha de la DB (string YYYY-MM-DD) a objeto date
        fecha_vencimiento = datetime.strptime(factura['fecha'], '%Y-%m-%d').date()
        fecha_hoy = date.today()
        
        if fecha_vencimiento < fecha_hoy:
            return 'Vencida'
        else:
            return 'Pendiente'
    except ValueError:
        # En caso de que la fecha en la DB sea inválida
        return 'Error de Fecha'

# --- Rutas de la Aplicación ---

@app.route('/')
def index():
    """Muestra la lista de facturas con estado calculado."""
    conn = get_db()
    facturas_db = conn.execute('SELECT * FROM facturas ORDER BY fecha DESC').fetchall()
    conn.close()
    
    facturas_procesadas = []
    for factura_row in facturas_db:
        factura = dict(factura_row)
        factura['estado_calculado'] = calcular_estado(factura)
        
        # Lógica para la alerta de vencimiento inminente (próximos 7 días)
        factura['alerta_vencimiento'] = False
        factura['dias_restantes'] = None

        if factura['estado_calculado'] == 'Pendiente':
            try:
                fecha_vencimiento = datetime.strptime(factura['fecha'], '%Y-%m-%d').date()
                fecha_hoy = date.today()
                dias_restantes = (fecha_vencimiento - fecha_hoy).days
                
                if dias_restantes >= 0 and dias_restantes <= 7:
                     factura['alerta_vencimiento'] = True
                     factura['dias_restantes'] = dias_restantes
                elif dias_restantes > 7:
                     factura['dias_restantes'] = dias_restantes

            except ValueError:
                pass
            
        facturas_procesadas.append(factura)
        
    # Alerta general si hay alguna factura en riesgo (Pendiente y vence pronto o Vencida)
    hay_alerta_general = any(f['alerta_vencimiento'] or f['estado_calculado'] == 'Vencida' for f in facturas_procesadas)
    
    return render_template('index.html', 
                           facturas=facturas_procesadas,
                           hay_alerta_general=hay_alerta_general)

@app.route('/agregar', methods=['POST'])
def agregar_factura():
    """Agrega una nueva factura a la base de datos. El estado inicial siempre es 'Pendiente'."""
    if request.method == 'POST':
        cliente = request.form['cliente']
        monto = request.form['monto']
        fecha = request.form['fecha']
        # Forzamos el estado inicial a 'Pendiente'
        estado = 'Pendiente' 

        if not cliente or not monto or not fecha:
            flash('Los campos Cliente, Monto y Fecha son obligatorios.', 'error')
            return redirect(url_for('index'))

        conn = get_db()
        conn.execute('INSERT INTO facturas (cliente, monto, fecha, estado) VALUES (?, ?, ?, ?)',
                     (cliente, monto, fecha, estado))
        conn.commit()
        conn.close()
        flash('Factura agregada con éxito e inicialmente marcada como Pendiente.', 'success')
        return redirect(url_for('index'))
        
@app.route('/marcar_pagada/<int:factura_id>')
def marcar_pagada(factura_id):
    """Marca una factura como 'Pagada' manualmente."""
    conn = get_db()
    conn.execute('UPDATE facturas SET estado = ? WHERE id = ?', ('Pagada', factura_id))
    conn.commit()
    conn.close()
    flash(f'Factura #{factura_id} marcada como Pagada con éxito.', 'success')
    return redirect(url_for('index'))


@app.route('/eliminar/<int:factura_id>')
def eliminar_factura(factura_id):
    """Elimina una factura por ID."""
    conn = get_db()
    conn.execute('DELETE FROM facturas WHERE id = ?', (factura_id,))
    conn.commit()
    conn.close()
    flash('Factura eliminada con éxito.', 'success')
    return redirect(url_for('index'))

# --- CONFIGURACIÓN DE INICIO PARA ENTORNO LOCAL Y RENDER ---

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
