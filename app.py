# app.py - Versión Completa con correcciones para PostgreSQL y Jinja2

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime, date
from werkzeug.security import check_password_hash

# Importar TODAS las funciones necesarias de db_manager
from db_manager import (
    inicializar_db, registrar_guia, get_guia_data, check_password_hash,
    obtener_todos_los_guias, cambiar_aprobacion, eliminar_guia, promover_a_admin, degradar_a_guia,
    obtener_todos_los_idiomas, agregar_idioma_db, actualizar_idioma_db, eliminar_idioma_db, 
    obtener_idiomas_de_guia, actualizar_idiomas_de_guia, obtener_idiomas_de_multiples_guias,
    actualizar_password_db, actualizar_perfil_db, 
    registrar_queja, obtener_todas_las_quejas, actualizar_estado_queja, eliminar_queja_db,
    agregar_disponibilidad_fecha, obtener_disponibilidad_fechas, eliminar_disponibilidad_fecha,
    buscar_guias_disponibles_por_fecha
)


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_por_defecto_y_muy_larga')

# --------------------------------------------------------------------------
# DECORADORES Y FUNCIONES GLOBALES
# --------------------------------------------------------------------------

def login_required(f):
    """Decorador para requerir inicio de sesión."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('logged_in'):
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorador para requerir rol de administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_rol') != 'admin':
            flash('Acceso denegado: Se requiere ser administrador.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


# --------------------------------------------------------------------------
# RUTAS PÚBLICAS Y DE AUTENTICACIÓN
# --------------------------------------------------------------------------

@app.before_first_request
def setup():
    """Inicializa la base de datos al inicio."""
    # Esto creará las tablas si no existen, incluyendo el administrador por defecto.
    try:
        inicializar_db()
        print("Base de datos PostgreSQL inicializada o verificada con éxito.")
    except Exception as e:
        print(f"ERROR FATAL al inicializar la DB: {e}")
        # En un entorno de producción, puedes optar por no continuar si la DB falla.

@app.route('/')
def home():
    # Obtener el catálogo de idiomas para el filtro de búsqueda
    idiomas_catalogo = obtener_todos_los_idiomas()
    return render_template('home.html', idiomas_catalogo=idiomas_catalogo)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        licencia = request.form['licencia'].strip()
        password = request.form['password']
        
        guia_data = get_guia_data(licencia, all_data=False) # Obtiene (password_hash, rol, aprobado)

        if guia_data and check_password_hash(guia_data[0], password):
            rol = guia_data[1]
            aprobado = guia_data[2]
            
            if aprobado == 0 and rol != 'admin':
                flash('Tu cuenta aún está pendiente de aprobación por el administrador.', 'warning')
                return redirect(url_for('login'))
            
            # Inicio de sesión exitoso
            session['logged_in'] = True
            session['user_licencia'] = licencia
            session['user_rol'] = rol
            
            if rol == 'admin':
                return redirect(url_for('panel_admin'))
            else:
                return redirect(url_for('panel_guia'))
        else:
            flash('Credenciales inválidas.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        licencia = request.form['licencia'].strip()
        nombre = request.form['nombre']
        password = request.form['password']
        
        if registrar_guia(licencia, nombre, password):
            flash('Registro exitoso. Tu cuenta está pendiente de aprobación por el administrador.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error al registrar: La licencia ya está en uso o datos inválidos.', 'error')
    
    return render_template('register.html')


# --------------------------------------------------------------------------
# RUTAS DE PANELES Y FUNCIONALIDAD DE GUÍA
# --------------------------------------------------------------------------

@app.route('/panel_guia')
@login_required
def panel_guia():
    if session.get('user_rol') == 'admin':
        # Redirigir si el admin accidentalmente va al panel de guía
        return redirect(url_for('panel_admin')) 
        
    return render_template('panel_guia.html')

@app.route('/editar_mi_perfil', methods=['GET', 'POST'])
@login_required
def editar_mi_perfil():
    licencia = session.get('user_licencia')
    guia_info_tuple = get_guia_data(licencia, all_data=True) 

    if not guia_info_tuple:
        flash('Error: No se pudo cargar la información del perfil.', 'error')
        return redirect(url_for('panel_guia'))

    # Crear el diccionario 'guia' que la plantilla espera (CORRECCIÓN DE ERROR JINJA)
    perfil_data = {
        'licencia': guia_info_tuple[0], 
        'nombre': guia_info_tuple[1], 
        'telefono': guia_info_tuple[5] if guia_info_tuple[5] else '', 
        'email': guia_info_tuple[6] if guia_info_tuple[6] else '',
        'bio': guia_info_tuple[7] if guia_info_tuple[7] else ''
    }
    
    idiomas_catalogo = obtener_todos_los_idiomas()
    idiomas_seleccionados_ids = obtener_idiomas_de_guia(licencia)

    if request.method == 'POST':
        # 1. Obtener datos del formulario
        nuevo_nombre = request.form.get('nombre')
        nuevo_telefono = request.form.get('telefono')
        nuevo_email = request.form.get('email')
        nueva_bio = request.form.get('bio')
        idiomas_elegidos = request.form.getlist('idiomas')
        
        # 2. Actualizar datos básicos
        if actualizar_perfil_db(licencia, nuevo_nombre, nuevo_telefono, nuevo_email, nueva_bio):
            flash('Datos del perfil actualizados correctamente.', 'success')
        else:
            flash('Error al actualizar los datos básicos.', 'error')

        # 3. Actualizar idiomas
        if actualizar_idiomas_de_guia(licencia, idiomas_elegidos):
            flash('Idiomas actualizados correctamente.', 'success')
        else:
            flash('Error al actualizar los idiomas.', 'error')
            
        return redirect(url_for('editar_mi_perfil'))

    # Método GET: Renderizar plantilla
    return render_template('editar_perfil.html', 
                           guia=perfil_data, # Pasa el objeto 'guia'
                           idiomas_catalogo=idiomas_catalogo, 
                           idiomas_seleccionados_ids=idiomas_seleccionados_ids)

@app.route('/actualizar_password', methods=['POST'])
@login_required
def actualizar_password():
    licencia = session.get('user_licencia')
    nueva_password = request.form.get('nueva_password')
    
    if len(nueva_password) < 6:
        flash('La nueva contraseña debe tener al menos 6 caracteres.', 'error')
    elif actualizar_password_db(licencia, nueva_password):
        flash('Contraseña actualizada correctamente.', 'success')
    else:
        flash('Error al actualizar la contraseña.', 'error')

    return redirect(url_for('editar_mi_perfil'))

@app.route('/disponibilidad', methods=['GET', 'POST'])
@login_required
def gestionar_disponibilidad():
    licencia = session.get('user_licencia')
    
    if request.method == 'POST':
        fecha_str = request.form.get('fecha')
        hora_inicio = request.form.get('hora_inicio')
        hora_fin = request.form.get('hora_fin')

        try:
            # Validación simple de que la fecha no esté en el pasado
            if datetime.strptime(fecha_str, '%Y-%m-%d').date() < date.today():
                 flash('No puedes agregar disponibilidad en el pasado.', 'error')
            elif agregar_disponibilidad_fecha(licencia, fecha_str, hora_inicio, hora_fin):
                flash('Disponibilidad agregada exitosamente.', 'success')
            else:
                flash('Error: La fecha ya fue marcada como disponible. Elimínala para cambiar la hora.', 'error')
        except ValueError:
             flash('Formato de fecha u hora inválido.', 'error')
        except Exception as e:
            flash(f'Error al procesar la disponibilidad: {e}', 'error')
            
        return redirect(url_for('gestionar_disponibilidad'))

    disponibilidad = obtener_disponibilidad_fechas(licencia)
    return render_template('disponibilidad.html', disponibilidad=disponibilidad)

@app.route('/eliminar_disponibilidad/<int:fecha_id>', methods=['POST'])
@login_required
def eliminar_disponibilidad(fecha_id):
    licencia = session.get('user_licencia')
    if eliminar_disponibilidad_fecha(fecha_id, licencia):
        flash('Disponibilidad eliminada.', 'success')
    else:
        flash('Error al eliminar disponibilidad.', 'error')
    return redirect(url_for('gestionar_disponibilidad'))

@app.route('/reportar_queja', methods=['GET', 'POST'])
def reportar_queja():
    guias = obtener_todos_los_guias() # Se podría optimizar, pero funciona para un listado
    
    if request.method == 'POST':
        licencia_guia = request.form.get('licencia_guia')
        descripcion = request.form.get('descripcion')
        reportado_por = request.form.get('reportado_por') or "Anónimo"
        
        if registrar_queja(licencia_guia, descripcion, reportado_por):
            flash('Queja registrada con éxito. Será revisada por la administración.', 'success')
            return redirect(url_for('home'))
        else:
            flash('Error al registrar la queja. Asegúrate de que la licencia sea correcta.', 'error')
            
    return render_template('reportar_queja.html', guias=guias)

@app.route('/buscar_guia', methods=['POST'])
def buscar_guia():
    fecha_str = request.form.get('fecha')
    idioma_id = request.form.get('idioma')
    
    if not fecha_str:
        flash('Debe seleccionar una fecha para buscar.', 'error')
        return redirect(url_for('home'))

    try:
        # Convertir a formato DATE para la DB
        fecha_buscada = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Formato de fecha inválido.', 'error')
        return redirect(url_for('home'))

    # Convertir idioma_id a entero o None
    idioma_id = int(idioma_id) if idioma_id and idioma_id != '0' else None
    
    guias_disponibles = buscar_guias_disponibles_por_fecha(fecha_buscada, idioma_id)
    
    # Obtener el nombre del idioma buscado para mostrar en el resultado
    idiomas_catalogo = {i[0]: i[1] for i in obtener_todos_los_idiomas()}
    idioma_nombre = idiomas_catalogo.get(idioma_id) if idioma_id else "Cualquier idioma"
    
    return render_template('resultados_busqueda.html', 
                           guias=guias_disponibles, 
                           fecha=fecha_buscada.strftime('%d-%m-%Y'),
                           idioma_nombre=idioma_nombre)


# --------------------------------------------------------------------------
# RUTAS DE ADMINISTRADOR
# --------------------------------------------------------------------------

@app.route('/panel_admin')
@login_required
@admin_required
def panel_admin():
    return render_template('panel_admin.html')

@app.route('/gestion_guias')
@login_required
@admin_required
def gestion_guias():
    guias = obtener_todos_los_guias()
    
    # Obtener idiomas para cada guía
    licencias = [g[0] for g in guias]
    idiomas_por_guia = obtener_idiomas_de_multiples_guias(licencias)
    
    # Fusionar idiomas con los datos de los guías (creando una lista de diccionarios)
    guias_data = []
    for guia in guias:
        guia_dict = {
            'licencia': guia[0],
            'nombre': guia[1],
            'rol': guia[2],
            'aprobado': guia[3],
            'fecha_registro': guia[4],
            'telefono': guia[5],
            'email': guia[6],
            'idiomas': idiomas_por_guia.get(guia[0], 'N/A')
        }
        guias_data.append(guia_dict)
        
    return render_template('gestion_guias.html', guias=guias_data)


@app.route('/aprobar_guia/<licencia>')
@login_required
@admin_required
def aprobar_guia(licencia):
    if cambiar_aprobacion(licencia, 1):
        flash(f'Guía {licencia} aprobado.', 'success')
    else:
        flash('Error al aprobar el guía.', 'error')
    return redirect(url_for('gestion_guias'))

@app.route('/rechazar_guia/<licencia>')
@login_required
@admin_required
def rechazar_guia(licencia):
    if cambiar_aprobacion(licencia, 0):
        flash(f'Guía {licencia} rechazado.', 'warning')
    else:
        flash('Error al rechazar el guía.', 'error')
    return redirect(url_for('gestion_guias'))

@app.route('/eliminar_guia/<licencia>')
@login_required
@admin_required
def borrar_guia(licencia):
    if eliminar_guia(licencia):
        flash(f'Guía {licencia} eliminado permanentemente.', 'success')
    else:
        flash('Error al eliminar el guía.', 'error')
    return redirect(url_for('gestion_guias'))

@app.route('/promover/<licencia>')
@login_required
@admin_required
def promover(licencia):
    if promover_a_admin(licencia):
        flash(f'Guía {licencia} promovido a Administrador.', 'success')
    else:
        flash('Error al promover o ya es administrador.', 'error')
    return redirect(url_for('gestion_guias'))

@app.route('/degradar/<licencia>')
@login_required
@admin_required
def degradar(licencia):
    if degradar_a_guia(licencia):
        flash(f'Administrador {licencia} degradado a Guía.', 'success')
    else:
        flash('Error al degradar o es el administrador principal.', 'error')
    return redirect(url_for('gestion_guias'))

@app.route('/gestion_idiomas', methods=['GET', 'POST'])
@login_required
@admin_required
def gestion_idiomas():
    if request.method == 'POST':
        nombre = request.form.get('nombre_idioma').strip()
        if nombre and agregar_idioma_db(nombre):
            flash(f'Idioma "{nombre}" agregado.', 'success')
        else:
            flash('Error: El idioma ya existe o el nombre es inválido.', 'error')
        return redirect(url_for('gestion_idiomas'))

    idiomas = obtener_todos_los_idiomas()
    return render_template('gestion_idiomas.html', idiomas=idiomas)

@app.route('/actualizar_idioma/<int:idioma_id>', methods=['POST'])
@login_required
@admin_required
def actualizar_idioma(idioma_id):
    nuevo_nombre = request.form.get('nuevo_nombre').strip()
    if nuevo_nombre and actualizar_idioma_db(idioma_id, nuevo_nombre):
        flash('Idioma actualizado correctamente.', 'success')
    else:
        flash('Error al actualizar el idioma. Ya existe un idioma con ese nombre.', 'error')
    return redirect(url_for('gestion_idiomas'))

@app.route('/eliminar_idioma/<int:idioma_id>')
@login_required
@admin_required
def eliminar_idioma(idioma_id):
    if eliminar_idioma_db(idioma_id):
        flash('Idioma eliminado. Los guías que lo tenían han sido actualizados.', 'success')
    else:
        flash('Error al eliminar el idioma.', 'error')
    return redirect(url_for('gestion_idiomas'))

@app.route('/gestion_quejas')
@login_required
@admin_required
def gestion_quejas():
    # CORRECCIÓN DE ERROR DE PLANTILLA FALTANTE (gestion_quejas.html)
    quejas = obtener_todas_las_quejas_para_guias()
    return render_template('gestion_quejas.html', quejas=quejas)

@app.route('/actualizar_estado_queja/<int:queja_id>', methods=['POST'])
@login_required
@admin_required
def cambiar_estado_queja(queja_id):
    nuevo_estado = request.form.get('estado')
    if actualizar_estado_queja(queja_id, nuevo_estado):
        flash(f'Queja {queja_id} actualizada a "{nuevo_estado}".', 'success')
    else:
        flash('Error al actualizar el estado de la queja.', 'error')
    return redirect(url_for('gestion_quejas'))

@app.route('/eliminar_queja/<int:queja_id>')
@login_required
@admin_required
def eliminar_queja(queja_id):
    if eliminar_queja_db(queja_id):
        flash(f'Queja {queja_id} eliminada.', 'success')
    else:
        flash('Error al eliminar la queja.', 'error')
    return redirect(url_for('gestion_quejas'))


if __name__ == '__main__':
    # Usamos Gunicorn para producción, pero flask run es para desarrollo local
    # Solo ejecutar flask run si no se está en un entorno de servidor como Render
    app.run(debug=True)
