# D:\guia_mp_nuevo\app.py 

from flask import Flask, render_template, session, redirect, url_for, flash, request
import sqlite3
import hashlib
import datetime 

# Definimos el nombre de la DB directamente 
DATABASE_NAME = 'machupicchu_guias.db' 

# --- CONFIGURACIÓN DE LA APLICACIÓN FLASK ---
app = Flask(__name__)
# ¡CLAVE DE SEGURIDAD! CÁMBIALA por una más larga y compleja.
app.secret_key = 'UNA_CLAVE_SECRETA_MUY_LARGA_Y_UNICA_AQUI' 
# ---------------------------------------------

# --- UTILIDADES ---
def conectar_db():
    """Establece la conexión a la base de datos y activa las claves foráneas."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.execute("PRAGMA foreign_keys = ON") 
    return conn

def hash_password(password):
    """Cifra la contraseña usando SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()
    
# --- FUNCIÓN AUXILIAR PARA INSERTAR RESERVAS DE PRUEBA ---
def insertar_reservas_prueba(guia_id):
    """Inserta datos de ejemplo en la tabla RESERVAS."""
    conn = conectar_db()
    cursor = conn.cursor()
    
    hoy = datetime.date.today()
    fecha_futura = (hoy + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    fecha_pasada = (hoy - datetime.timedelta(days=15)).strftime('%Y-%m-%d')
    
    reservas_ejemplo = [
        (guia_id, fecha_futura, '10:00', 4.0, 200.00, 'Alex Johnson', 'alex@ejemplo.com', 'Confirmada'),
        (guia_id, (hoy + datetime.timedelta(days=5)).strftime('%Y-%m-%d'), '14:30', 3.5, 175.00, 'Maria Lopez', 'maria@ejemplo.com', 'Confirmada'),
        (guia_id, fecha_pasada, '08:00', 5.0, 250.00, 'Chen Wei', 'chen@ejemplo.com', 'Completada'),
    ]

    try:
        for r in reservas_ejemplo:
            cursor.execute("""
                INSERT INTO RESERVAS (guia_id, fecha_reserva, hora_inicio, duracion_horas, tarifa_total, cliente_nombre, cliente_email, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, r)
        conn.commit()
        flash('Datos de reservas de prueba cargados automáticamente.', 'info')
    except Exception as e:
        print(f"Error al insertar reservas de prueba: {e}")
        flash('Error al cargar datos de prueba. Inténtalo de nuevo.', 'error')
        
    conn.close()


# --- RUTAS PÚBLICAS ---

@app.route('/')
def index():
    """Ruta de inicio, redirige al menú principal."""
    return redirect(url_for('menu_principal'))

@app.route('/menu')
def menu_principal():
    """Menú Principal para el público."""
    return render_template('menu_principal.html')

# --- INICIO DE SESIÓN Y CIERRE DE SESIÓN DEL GUÍA ---

@app.route('/login', methods=['GET', 'POST'])
def login_guia():
    """Maneja el inicio de sesión para los guías."""
    if 'guia_id' in session:
        flash('Ya tienes una sesión activa.', 'info') 
        return redirect(url_for('panel_guia')) 
        
    if request.method == 'POST':
        licencia = request.form['licencia'].strip()
        password = request.form['password']
        
        conn = conectar_db()
        cursor = conn.cursor()
        
        # 1. Buscar el guía por número de licencia
        cursor.execute("SELECT guia_id, nombre, password FROM GUIAS WHERE licencia_no = ?", (licencia,))
        guia_data = cursor.fetchone()
        conn.close()
        
        if guia_data:
            guia_id, nombre, hashed_password_db = guia_data
            
            # 2. Verificar la contraseña cifrada
            if hash_password(password) == hashed_password_db:
                session['guia_id'] = guia_id
                session['guia_nombre'] = nombre
                flash(f'¡Bienvenido, {nombre}! Sesión iniciada con éxito.', 'success')
                return redirect(url_for('panel_guia')) 
            else:
                flash('Contraseña incorrecta. Intenta de nuevo.', 'error')
        else:
            flash('Número de Licencia no encontrado.', 'error')

    return render_template('login_guia.html')

@app.route('/logout')
def logout_guia():
    """Cierra la sesión del guía."""
    session.pop('guia_id', None)
    session.pop('guia_nombre', None)
    flash('Has cerrado tu sesión con éxito.', 'info')
    return redirect(url_for('menu_principal'))

# --- PANEL DE CONTROL DEL GUÍA ---

@app.route('/panel_guia')
def panel_guia():
    """Muestra el panel de control del guía logueado."""
    if 'guia_id' not in session:
        flash('Debes iniciar sesión para acceder al panel.', 'warning')
        return redirect(url_for('login_guia'))
    
    guia_id = session['guia_id']
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Obtener tarifa base y licencia no (para mostrar en el panel)
    cursor.execute("SELECT tarifa_base, licencia_no FROM GUIAS WHERE guia_id = ?", (guia_id,))
    data = cursor.fetchone()
    conn.close()
    
    if data:
        tarifa_base, licencia_no = data
    else:
        tarifa_base, licencia_no = 0.0, "N/A"
    
    return render_template('panel_guia.html', 
                           guia_nombre=session['guia_nombre'],
                           licencia_no=licencia_no,
                           tarifa_base=tarifa_base)

# --- GESTIÓN DE PERFIL DEL GUÍA (ACTUALIZAR DATOS) ---

@app.route('/perfil', methods=['GET', 'POST'])
def gestionar_perfil():
    """Permite al guía ver y actualizar sus datos personales (nombre, tarifa, celular)."""
    if 'guia_id' not in session:
        flash('Debes iniciar sesión para gestionar tu perfil.', 'warning')
        return redirect(url_for('login_guia'))
        
    guia_id = session['guia_id']
    conn = conectar_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # 1. Obtener datos del formulario
        nuevo_nombre = request.form['nombre'].strip()
        nueva_tarifa = request.form.get('tarifa_base')
        nuevo_celular = request.form.get('celular', '').strip()

        try:
            tarifa_float = float(nueva_tarifa)
        except ValueError:
            flash('La tarifa debe ser un número válido.', 'error')
            conn.close()
            return redirect(url_for('gestionar_perfil'))

        if not nuevo_nombre:
            flash('El nombre no puede estar vacío.', 'error')
            conn.close()
            return redirect(url_for('gestionar_perfil'))

        # 2. Actualizar la base de datos
        try:
            cursor.execute("""
                UPDATE GUIAS 
                SET nombre = ?, tarifa_base = ?, celular = ?
                WHERE guia_id = ?
            """, (nuevo_nombre, tarifa_float, nuevo_celular, guia_id))
            
            conn.commit()
            
            # 3. Actualizar la sesión si el nombre cambió
            session['guia_nombre'] = nuevo_nombre
            
            flash('Perfil actualizado con éxito.', 'success')
            
            conn.close()
            return redirect(url_for('panel_guia'))

        except Exception as e:
            flash(f'Error al actualizar el perfil: {e}', 'error')
            conn.close()
            return redirect(url_for('gestionar_perfil'))

    # Método GET: Cargar datos actuales del guía para el formulario
    cursor.execute("SELECT nombre, licencia_no, tarifa_base, celular FROM GUIAS WHERE guia_id = ?", (guia_id,))
    perfil = cursor.fetchone()
    conn.close()

    if perfil:
        # Los datos son: (nombre, licencia_no, tarifa_base, celular)
        datos_perfil = {
            'nombre': perfil[0],
            'licencia_no': perfil[1],
            'tarifa_base': perfil[2],
            'celular': perfil[3]
        }
        return render_template('gestionar_perfil.html', datos=datos_perfil)
    
    flash('No se pudieron cargar los datos del perfil.', 'error')
    return redirect(url_for('panel_guia'))


# --- REGISTRO DE NUEVO GUÍA (PÚBLICO) ---

@app.route('/registrar_guia', methods=['GET', 'POST'])
def registrar_guia():
    """Permite registrar un nuevo guía en el sistema de forma pública."""
    
    if 'guia_id' in session:
        flash('Ya tienes una sesión activa. No necesitas registrarte.', 'info') 
        return redirect(url_for('panel_guia')) 

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        licencia = request.form['licencia'].strip()
        password = request.form['password']
        celular = request.form.get('celular', '').strip() 
        
        try:
            tarifa_base = float(request.form.get('tarifa_base') or 50.00)
        except ValueError:
            flash('La tarifa base debe ser un número válido.', 'error')
            data_to_pass = {k: v for k, v in request.form.items() if k != 'password'}
            return render_template('registrar_guia.html', data=data_to_pass)

        if not all([nombre, licencia, password]):
            flash('Todos los campos obligatorios deben ser llenados.', 'error')
            data_to_pass = {k: v for k, v in request.form.items() if k != 'password'}
            return render_template('registrar_guia.html', data=data_to_pass)

        try:
            hashed_pass = hash_password(password)
            conn = conectar_db()
            cursor = conn.cursor()
            
            # Consulta SQL para registro incluyendo 'celular'
            cursor.execute("""
                INSERT INTO GUIAS (nombre, licencia_no, password, tarifa_base, celular)
                VALUES (?, ?, ?, ?, ?)
            """, (nombre, licencia, hashed_pass, tarifa_base, celular))
            
            conn.commit()
            flash(f'Guía "{nombre}" (Licencia: {licencia}) registrado con éxito. ¡Ya puedes iniciar sesión!', 'success')
            conn.close()
            return redirect(url_for('login_guia')) 

        except sqlite3.IntegrityError:
            flash(f'Error: El número de licencia "{licencia}" ya está registrado.', 'error')
        except Exception as e:
            flash(f'Ocurrió un error al registrar el guía: {e}', 'error')
            
    return render_template('registrar_guia.html')

# --- GESTIÓN DE DISPONIBILIDAD (CREAR Y VISUALIZAR) ---

@app.route('/disponibilidad', methods=['GET', 'POST'])
def gestionar_disponibilidad():
    """Permite al guía registrar y ver su disponibilidad."""
    if 'guia_id' not in session:
        flash('Debes iniciar sesión para gestionar tu disponibilidad.', 'warning')
        return redirect(url_for('login_guia'))
        
    guia_id = session['guia_id']
    conn = conectar_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        fecha = request.form.get('fecha')
        hora_inicio = request.form.get('hora_inicio')
        hora_fin = request.form.get('hora_fin')
        
        try:
            cursor.execute("""
                INSERT INTO DISPONIBILIDAD (guia_id, fecha, hora_inicio, hora_fin) 
                VALUES (?, ?, ?, ?)
            """, (guia_id, fecha, hora_inicio, hora_fin))
            conn.commit()
            flash('Disponibilidad registrada con éxito.', 'success')
        except sqlite3.IntegrityError:
            flash('Ya existe una disponibilidad registrada para esta fecha y hora de inicio.', 'error')
        except Exception as e:
            flash(f'Error al registrar la disponibilidad: {e}', 'error')

    # Obtener todas las disponibilidades futuras 
    cursor.execute("""
        SELECT disponibilidad_id, fecha, hora_inicio, hora_fin, estado 
        FROM DISPONIBILIDAD 
        WHERE guia_id = ? AND fecha >= date('now') 
        ORDER BY fecha, hora_inicio
    """, (guia_id,))
    disponibilidades = cursor.fetchall()
    conn.close()
    
    return render_template('disponibilidad.html', disponibilidades=disponibilidades)

# --- GESTIÓN DE DISPONIBILIDAD (ELIMINAR) ---

@app.route('/disponibilidad/eliminar/<int:disponibilidad_id>', methods=['POST'])
def eliminar_disponibilidad(disponibilidad_id):
    """Permite al guía eliminar un registro de disponibilidad."""
    if 'guia_id' not in session:
        flash('Debes iniciar sesión para realizar esta acción.', 'warning')
        return redirect(url_for('login_guia'))
    
    guia_id = session['guia_id']
    conn = conectar_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM DISPONIBILIDAD WHERE disponibilidad_id = ? AND guia_id = ?", 
                       (disponibilidad_id, guia_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            flash('Turno de disponibilidad eliminado con éxito.', 'success')
        else:
            flash('Error al eliminar: El registro no existe o no te pertenece.', 'error')
            
    except Exception as e:
        flash(f'Error de base de datos al eliminar: {e}', 'error')
        
    conn.close()
    return redirect(url_for('gestionar_disponibilidad'))


# --- GESTIÓN DE IDIOMAS ---

@app.route('/idiomas', methods=['GET', 'POST'])
def gestionar_idiomas():
    """Permite al guía registrar y modificar los idiomas que habla."""
    if 'guia_id' not in session:
        flash('Debes iniciar sesión para gestionar tus idiomas.', 'warning')
        return redirect(url_for('login_guia'))
        
    guia_id = session['guia_id']
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Obtener todos los idiomas disponibles (MAESTROS)
    cursor.execute("SELECT idioma_id, nombre_idioma FROM IDIOMAS ORDER BY nombre_idioma")
    idiomas_maestros = cursor.fetchall()
    
    # Obtener los idiomas y niveles actuales del guía
    cursor.execute("""
        SELECT T2.idioma_id, T2.nombre_idioma, T1.nivel 
        FROM GUIAS_IDIOMAS AS T1
        JOIN IDIOMAS AS T2 ON T1.idioma_id = T2.idioma_id
        WHERE T1.guia_id = ?
    """, (guia_id,))
    idiomas_actuales = {idioma_id: nivel for idioma_id, nombre, nivel in cursor.fetchall()}
    
    if request.method == 'POST':
        cursor.execute("DELETE FROM GUIAS_IDIOMAS WHERE guia_id = ?", (guia_id,))
        
        idiomas_seleccionados = request.form.getlist('idiomas')
        
        exito = False
        for idioma_id_str in idiomas_seleccionados:
            idioma_id = int(idioma_id_str)
            nivel = request.form.get(f'nivel_{idioma_id}')
            
            if nivel and nivel != "":
                cursor.execute("""
                    INSERT INTO GUIAS_IDIOMAS (guia_id, idioma_id, nivel) 
                    VALUES (?, ?, ?)
                """, (guia_id, idioma_id, nivel))
                exito = True

        conn.commit()
        
        if exito:
            flash('Idiomas actualizados con éxito.', 'success')
        else:
            flash('No se seleccionaron idiomas con nivel válido. No se realizó ningún cambio.', 'info')
            
        return redirect(url_for('gestionar_idiomas')) 

    conn.close()
    
    return render_template('gestionar_idiomas.html', 
                           idiomas_maestros=idiomas_maestros,
                           idiomas_actuales=idiomas_actuales)
                           
# --- GESTIÓN DE RESERVAS (HISTORIAL) ---

@app.route('/historial_reservas')
def historial_reservas():
    """Muestra el historial de reservas confirmadas para el guía logueado."""
    if 'guia_id' not in session:
        flash('Debes iniciar sesión para ver tu historial de reservas.', 'warning')
        return redirect(url_for('login_guia'))
        
    guia_id = session['guia_id']
    conn = conectar_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            reserva_id, fecha_reserva, hora_inicio, duracion_horas, tarifa_total, 
            cliente_nombre, cliente_email, estado
        FROM RESERVAS
        WHERE guia_id = ?
        ORDER BY fecha_reserva DESC, hora_inicio DESC
    """, (guia_id,))
    
    reservas = cursor.fetchall()
    conn.close()

    if not reservas and guia_id == 1: 
        insertar_reservas_prueba(guia_id)
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                reserva_id, fecha_reserva, hora_inicio, duracion_horas, tarifa_total, 
                cliente_nombre, cliente_email, estado
            FROM RESERVAS
            WHERE guia_id = ?
            ORDER BY fecha_reserva DESC, hora_inicio DESC
        """, (guia_id,))
        reservas = cursor.fetchall()
        conn.close()


    return render_template('historial_reservas.html', reservas=reservas)
    
# --- GESTIÓN MAESTRA DE IDIOMAS (ADMIN) ---

@app.route('/admin/idiomas_maestros', methods=['GET', 'POST'])
def gestionar_idiomas_maestros():
    """Permite al administrador agregar nuevos idiomas a la lista maestra."""
    if 'guia_id' not in session or session.get('guia_nombre') != 'Guia Test':
        flash('Acceso denegado: Esta es una función administrativa.', 'error')
        return redirect(url_for('panel_guia'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        nuevo_idioma = request.form.get('nuevo_idioma', '').strip()
        
        if nuevo_idioma:
            try:
                cursor.execute("INSERT INTO IDIOMAS (nombre_idioma) VALUES (?)", (nuevo_idioma,))
                conn.commit()
                flash(f'El idioma "{nuevo_idioma}" ha sido añadido a la lista maestra.', 'success')
            except sqlite3.IntegrityError:
                flash(f'El idioma "{nuevo_idioma}" ya existe en la lista maestra.', 'warning')
            except Exception as e:
                flash(f'Ocurrió un error al añadir el idioma: {e}', 'error')
        else:
            flash('Por favor, ingresa un nombre de idioma válido.', 'warning')

    cursor.execute("SELECT nombre_idioma, idioma_id FROM IDIOMAS ORDER BY nombre_idioma")
    idiomas_maestros = cursor.fetchall()
    conn.close()
    
    return render_template('admin_idiomas.html', idiomas_maestros=idiomas_maestros)


# --- BÚSQUEDA DE GUÍAS ---

@app.route('/buscar_guias', methods=['GET', 'POST'])
def buscar_guias():
    """Permite al cliente buscar guías disponibles por fecha e idioma."""
    resultados = []
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Obtener la lista de idiomas para el menú desplegable (dropdown)
    cursor.execute("SELECT idioma_id, nombre_idioma FROM IDIOMAS ORDER BY nombre_idioma")
    idiomas_maestros = cursor.fetchall()

    if request.method == 'POST':
        fecha_busqueda = request.form.get('fecha_busqueda')
        idioma_busqueda_id = request.form.get('idioma_busqueda')
        
        if fecha_busqueda and idioma_busqueda_id:
            
            # Consulta SQL para buscar guías y obtener el celular
            consulta_sql = """
                SELECT 
                    T1.nombre, T1.licencia_no, T3.hora_inicio, T3.hora_fin, 
                    T1.tarifa_base, T2.nivel, T4.nombre_idioma, T1.celular 
                FROM GUIAS AS T1
                JOIN GUIAS_IDIOMAS AS T2 ON T1.guia_id = T2.guia_id
                JOIN DISPONIBILIDAD AS T3 ON T1.guia_id = T3.guia_id
                JOIN IDIOMAS AS T4 ON T2.idioma_id = T4.idioma_id 
                WHERE 
                    T3.fecha = ? 
                    AND T3.estado = 'Disponible'
                    AND T2.idioma_id = ? 
                ORDER BY T1.nombre, T3.hora_inicio
            """
            
            cursor.execute(consulta_sql, (fecha_busqueda, idioma_busqueda_id))
            resultados = cursor.fetchall()

            if not resultados:
                 flash('No se encontraron guías disponibles con la fecha y el idioma solicitados.', 'info')
            else:
                 nombre_idioma = resultados[0][6] 
                 flash(f'Mostrando {len(resultados)} turnos disponibles para el {fecha_busqueda} que hablan {nombre_idioma}.', 'success')
        else:
            flash('Por favor, selecciona una fecha y un idioma de búsqueda.', 'warning')

    conn.close()
    
    return render_template('buscar_guias.html', resultados=resultados, idiomas_maestros=idiomas_maestros)

# --- EJECUCIÓN DEL SERVIDOR ---
if __name__ == '__main__':
    print("--- Servidor Flask listo para recibir conexiones ---")
    app.run(debug=True, host='0.0.0.0', port=8000)
