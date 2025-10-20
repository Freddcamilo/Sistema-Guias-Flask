# app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from werkzeug.security import check_password_hash
from datetime import datetime
import locale 
import sqlite3 

# Establecer la localización a español
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'es_ES')
    except locale.Error:
        pass 

# Importar TODAS las funciones de db_manager.py
from db_manager import (
    inicializar_db, registrar_guia, get_guia_data, 
    actualizar_password_db, actualizar_perfil_db, 
    obtener_todos_los_guias, cambiar_aprobacion, eliminar_guia, promover_a_admin, degradar_a_guia, 
    agregar_idioma_db, obtener_todos_los_idiomas, actualizar_idioma_db, eliminar_idioma_db,
    obtener_idiomas_de_guia, actualizar_idiomas_de_guia, 
    registrar_queja, obtener_todas_las_quejas, actualizar_estado_queja, 
    agregar_disponibilidad_fecha, obtener_disponibilidad_fechas, eliminar_disponibilidad_fecha,
    buscar_guias_disponibles_por_fecha,
    obtener_todas_las_quejas_para_guias,
    eliminar_queja_db # <-- NUEVA FUNCIÓN IMPORTADA
)

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui' 

# --------------------------------------------------------------------------
# Decoradores y Sesión
# --------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('menu_principal'))
        return f(*args, **kwargs)
    return decorated_function

# --------------------------------------------------------------------------
# Rutas Públicas y de Autenticación
# --------------------------------------------------------------------------

@app.route('/')
@app.route('/menu')
def menu_principal():
    return render_template('menu_principal.html')

@app.route('/registro_guia', methods=['GET', 'POST']) 
def registro_guia():
    if request.method == 'POST':
        licencia = request.form.get('licencia')
        nombre = request.form.get('nombre')
        password = request.form.get('password')
        
        if not licencia or not nombre or not password:
            flash('Todos los campos son obligatorios.', 'error')
            return render_template('registro_guia.html')

        if registrar_guia(licencia, nombre, password):
            flash('Registro exitoso. Su cuenta debe ser aprobada por un administrador antes de iniciar sesión.', 'success')
            return redirect(url_for('login_guia'))
        else:
            flash('Error: La licencia ya está registrada.', 'error')
            return render_template('registro_guia.html')

    return render_template('registro_guia.html')

@app.route('/login_guia', methods=['GET', 'POST'])
def login_guia():
    if request.method == 'POST':
        licencia = request.form.get('licencia')
        password = request.form.get('password')
        
        guia_data = get_guia_data(licencia)
        
        if guia_data:
            guia_password_hash = guia_data[0] 
            guia_rol = guia_data[1]          
            guia_aprobado = guia_data[2]     

            if check_password_hash(guia_password_hash, password):
                
                if guia_aprobado == 0:
                    flash('Su cuenta aún no ha sido aprobada por un administrador.', 'warning')
                    return render_template('login_guia.html')

                session['logged_in'] = True
                session['user_licencia'] = licencia
                session['user_rol'] = guia_rol 
                
                flash('Inicio de sesión exitoso.', 'success')
                
                if guia_rol == 'admin':
                    return redirect(url_for('panel_admin'))
                else:
                    return redirect(url_for('panel_guia'))
            else:
                flash('Licencia o Contraseña incorrecta.', 'error')
        else:
            flash('Licencia o Contraseña incorrecta.', 'error')
            
    return render_template('login_guia.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión con éxito.', 'info')
    return redirect(url_for('menu_principal'))

@app.route('/reportar_queja', methods=['GET', 'POST'])
def reportar_queja_publico():
    if request.method == 'POST':
        licencia_guia = request.form.get('licencia_guia').strip()
        nombre_reportante = request.form.get('nombre_reportante').strip()
        descripcion = request.form.get('descripcion').strip()
        
        if not licencia_guia or not descripcion:
            flash('La licencia del guía y la descripción son obligatorias.', 'error')
            return render_template('reportar_queja.html')
        
        if not get_guia_data(licencia_guia): 
            flash(f'Error: No existe un guía registrado con la licencia {licencia_guia}.', 'error')
            return render_template('reportar_queja.html', 
                                   licencia_guia=licencia_guia, 
                                   nombre_reportante=nombre_reportante, 
                                   descripcion=descripcion)

        reportado_por_tag = f"Público: {nombre_reportante}" if nombre_reportante else "Público Anónimo"

        if registrar_queja(licencia_guia, descripcion, reportado_por_tag):
            flash('Su queja ha sido registrada y será revisada por la administración.', 'success')
            return redirect(url_for('menu_principal'))
        else:
            flash('Error al intentar registrar la queja.', 'error')

    return render_template('reportar_queja.html')

@app.route('/buscar_guia', methods=['GET', 'POST'])
def buscar_guia():
    idiomas = obtener_todos_los_idiomas()
    resultados = []
    
    fecha_actual_str = datetime.now().strftime('%Y-%m-%d')
    fecha_actual_formateada = datetime.now().strftime('%A, %d de %B').title()
    
    fecha_buscada = fecha_actual_str 
    fecha_buscada_formateada = fecha_actual_formateada 
    idioma_id = None
    
    if request.method == 'POST':
        fecha_buscada = request.form.get('fecha_buscada')
        idioma_id = request.form.get('idioma_id')
        
        if not fecha_buscada:
            flash('Por favor, ingrese una fecha válida.', 'error')
            fecha_buscada = fecha_actual_str 
        
        try:
            fecha_buscada_obj = datetime.strptime(fecha_buscada, '%Y-%m-%d')
            fecha_buscada_formateada = fecha_buscada_obj.strftime('%A, %d de %B').title()
        except ValueError:
            flash('Formato de fecha inválido. Usando la fecha actual.', 'error')
            fecha_buscada = fecha_actual_str
            fecha_buscada_formateada = fecha_actual_formateada
    
    if fecha_buscada:
        idioma_id_int = int(idioma_id) if idioma_id and idioma_id.isdigit() else None
        
        resultados = buscar_guias_disponibles_por_fecha(fecha_buscada, idioma_id_int)
        
        if request.method == 'POST':
            if not resultados:
                flash(f"No se encontraron guías disponibles para la fecha {fecha_buscada_formateada}.", 'info')
            else:
                 flash(f"Se encontraron {len(resultados)} guías disponibles para el {fecha_buscada_formateada}.", 'success')

    return render_template(
        'buscar_guia.html', 
        idiomas=idiomas, 
        resultados=resultados, 
        fecha_buscada=fecha_buscada, 
        fecha_buscada_formateada=fecha_buscada_formateada,
        idioma_id=idioma_id,
        fecha_actual=fecha_actual_str 
    )

# --------------------------------------------------------------------------
# Rutas de Paneles Principales
# --------------------------------------------------------------------------

@app.route('/panel_guia')
@login_required
def panel_guia():
    return render_template('panel_guia.html')

@app.route('/panel_admin')
@login_required
def panel_admin():
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores.', 'error')
        return redirect(url_for('panel_guia'))
        
    return render_template('panel_admin.html') 

# --------------------------------------------------------------------------
# Rutas de Gestión de Perfil
# --------------------------------------------------------------------------

@app.route('/cambiar_contrasena', methods=['GET', 'POST'])
@login_required
def cambiar_contrasena():
    if request.method == 'POST':
        licencia = session.get('user_licencia')
        actual_password = request.form.get('actual_password')
        nueva_password = request.form.get('nueva_password')
            
        guia_data = get_guia_data(licencia)
        
        if guia_data and check_password_hash(guia_data[0], actual_password):
            if actualizar_password_db(licencia, nueva_password):
                flash('Contraseña actualizada con éxito. Por favor, vuelva a iniciar sesión.', 'success')
                session.clear() 
                return redirect(url_for('login_guia'))
            else:
                flash('Error al intentar actualizar la contraseña.', 'error')
        else:
            flash('Contraseña actual incorrecta.', 'error')
            
    return render_template('cambiar_contrasena.html')

@app.route('/editar_mi_perfil', methods=['GET', 'POST'])
@login_required
def editar_mi_perfil():
    licencia = session.get('user_licencia')
    guia_info = get_guia_data(licencia, all_data=True) 

    if not guia_info:
        flash('Error al cargar la información del perfil.', 'error')
        return redirect(url_for('panel_guia'))
    
    perfil_data = {'nombre': guia_info[1], 'telefono': guia_info[5], 'email': guia_info[6], 'bio': guia_info[7]}
    
    if request.method == 'POST':
        nuevo_nombre = request.form.get('nombre')
        nuevo_telefono = request.form.get('telefono')
        nuevo_email = request.form.get('email')
        nueva_bio = request.form.get('bio')
        
        if actualizar_perfil_db(licencia, nuevo_nombre, nuevo_telefono, nuevo_email, nueva_bio): 
            flash('Perfil actualizado con éxito.', 'success')
            return redirect(url_for('panel_admin') if session.get('user_rol') == 'admin' else url_for('panel_guia'))
        else:
            flash('Error al actualizar el perfil.', 'error')
            perfil_data.update({'nombre': nuevo_nombre, 'telefono': nuevo_telefono, 'email': nuevo_email, 'bio': nueva_bio})
            return render_template('editar_perfil.html', **perfil_data)
    
    return render_template('editar_perfil.html', **perfil_data) 

@app.route('/gestion_mis_idiomas', methods=['GET', 'POST'])
@login_required
def gestion_mis_idiomas():
    licencia = session.get('user_licencia')
    
    if request.method == 'POST':
        idiomas_seleccionados_ids = request.form.getlist('idiomas_seleccionados')
        
        if actualizar_idiomas_de_guia(licencia, idiomas_seleccionados_ids):
            flash('Sus idiomas han sido actualizados con éxito.', 'success')
        else:
            flash('Error al actualizar sus idiomas.', 'error')
            
        return redirect(url_for('panel_admin') if session.get('user_rol') == 'admin' else url_for('panel_guia'))

    todos_los_idiomas = obtener_todos_los_idiomas() 
    idiomas_actuales_ids = obtener_idiomas_de_guia(licencia) 
    
    idiomas_para_plantilla = []
    for id_idioma, nombre_idioma in todos_los_idiomas:
        idiomas_para_plantilla.append({
            'id': id_idioma,
            'nombre': nombre_idioma,
            'seleccionado': id_idioma in idiomas_actuales_ids
        })

    return render_template(
        'gestion_mis_idiomas.html', 
        idiomas_disponibles=idiomas_para_plantilla
    ) 

@app.route('/ver_quejas_comunidad')
@login_required
def ver_quejas_comunidad():
    rol = session.get('user_rol')
    if rol == 'admin':
        flash('Acceso denegado. Use el panel de administración para gestionar las quejas.', 'error')
        return redirect(url_for('gestion_quejas'))
    
    if rol != 'guia':
        flash('Acceso denegado: Solo para guías registrados.', 'error')
        return redirect(url_for('menu_principal'))

    quejas = obtener_todas_las_quejas_para_guias()
    
    licencia_actual = session.get('user_licencia') 
    
    return render_template('ver_quejas_comunidad.html', 
                           quejas=quejas, 
                           licencia_actual=licencia_actual)

# --------------------------------------------------------------------------
# Rutas de Gestión de Disponibilidad
# --------------------------------------------------------------------------

@app.route('/gestionar_disponibilidad', methods=['GET'])
@login_required
def gestionar_disponibilidad():
    licencia = session.get('user_licencia')
    
    fechas_especificas = obtener_disponibilidad_fechas(licencia) 
    
    datos_fechas = []
    for fecha_data in fechas_especificas:
        fecha_obj = datetime.strptime(fecha_data['fecha'], '%Y-%m-%d')
        fecha_formateada = fecha_obj.strftime('%A, %d de %B').title()
        
        datos_fechas.append({
            'id': fecha_data['id'],
            'fecha': fecha_formateada,
            'inicio': fecha_data['inicio'],
            'fin': fecha_data['fin']
        })
        
    fecha_actual_str = datetime.now().strftime('%Y-%m-%d')

    return render_template(
        'gestionar_disponibilidad.html', 
        fechas_especificas=datos_fechas,
        fecha_actual=fecha_actual_str 
    )

@app.route('/agregar_fecha_disponible', methods=['POST'])
@login_required
def agregar_fecha_disponible():
    licencia = session.get('user_licencia')
    fecha = request.form.get('fecha')
    hora_inicio = request.form.get('hora_inicio')
    hora_fin = request.form.get('hora_fin')

    if not (fecha and hora_inicio and hora_fin):
        flash('Debe seleccionar una fecha, hora de inicio y hora de fin.', 'error')
    elif agregar_disponibilidad_fecha(licencia, fecha, hora_inicio, hora_fin):
        flash(f'Disponibilidad añadida para el {fecha}.', 'success')
    else:
        flash(f'Error: Ya existe una disponibilidad para el {fecha} o la fecha no es válida.', 'error')
        
    return redirect(url_for('gestionar_disponibilidad'))

@app.route('/eliminar_fecha_disponible/<int:fecha_id>', methods=['POST'])
@login_required
def eliminar_fecha_disponible(fecha_id):
    licencia = session.get('user_licencia')

    if eliminar_disponibilidad_fecha(fecha_id, licencia):
        flash('Fecha de disponibilidad eliminada con éxito.', 'info')
    else:
        flash('Error al eliminar la fecha de disponibilidad. (ID no encontrado o no autorizado)', 'error')

    return redirect(url_for('gestionar_disponibilidad'))

# --------------------------------------------------------------------------
# Rutas de Gestión del Administrador (Guías, Idiomas, Quejas)
# --------------------------------------------------------------------------

@app.route('/gestion_guias')
@login_required
def gestion_guias():
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores.', 'error')
        return redirect(url_for('panel_guia'))
        
    guias = obtener_todos_los_guias()
    return render_template('gestion_guias.html', guias=guias)

@app.route('/toggle_aprobacion/<licencia>/<int:estado>', methods=['POST'])
@login_required
def toggle_aprobacion(licencia, estado):
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores.', 'error')
        return redirect(url_for('panel_guia'))
    
    if cambiar_aprobacion(licencia, estado):
        accion = "aprobada" if estado == 1 else "desaprobada"
        flash(f'La cuenta {licencia} ha sido {accion} con éxito.', 'success')
    else:
        flash(f'Error al cambiar el estado de aprobación de {licencia}.', 'error')
        
    return redirect(url_for('gestion_guias'))

@app.route('/promover_guia/<licencia>', methods=['POST'])
@login_required
def promover_guia(licencia):
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo los administradores pueden promover guías.', 'error')
        return redirect(url_for('panel_admin'))

    if promover_a_admin(licencia):
        flash(f'La licencia {licencia} ha sido promovida a Administrador.', 'success')
    else:
        flash(f'Error al promover la licencia {licencia}. (Podría ya ser administrador)', 'error')

    return redirect(url_for('gestion_guias'))

@app.route('/degradar_guia/<licencia>', methods=['POST'])
@login_required
def degradar_guia(licencia):
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo los administradores pueden degradar guías.', 'error')
        return redirect(url_for('panel_admin'))

    if degradar_a_guia(licencia):
        flash(f'La licencia {licencia} ha sido degradada a Guía regular.', 'success')
    else:
        flash(f'Error al degradar la licencia {licencia}. (Podría ser ADMIN001 o ya era Guía)', 'error')

    return redirect(url_for('gestion_guias'))

@app.route('/eliminar_guia/<licencia>', methods=['POST'])
@login_required
def eliminar_guia_ruta(licencia):
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores.', 'error')
        return redirect(url_for('panel_guia'))
        
    if licencia == 'ADMIN001':
        flash('Error de seguridad: No se puede eliminar la cuenta del Administrador Principal (ADMIN001).', 'error')
        return redirect(url_for('gestion_guias'))

    if eliminar_guia(licencia):
        flash(f'La cuenta {licencia} ha sido eliminada con éxito.', 'success')
    else:
        flash(f'Error al eliminar la cuenta {licencia}.', 'error')
        
    return redirect(url_for('gestion_guias'))
    
@app.route('/gestion_idiomas')
@login_required
def gestion_idiomas():
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores.', 'error')
        return redirect(url_for('panel_guia')) 
    
    idiomas = obtener_todos_los_idiomas()
        
    return render_template('gestion_idiomas.html', idiomas=idiomas) 

@app.route('/agregar_idioma', methods=['POST'])
@login_required
def agregar_idioma():
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores.', 'error')
        return redirect(url_for('panel_admin'))
        
    nombre_idioma = request.form.get('nombre_idioma').strip()
    
    if not nombre_idioma:
        flash('El nombre del idioma no puede estar vacío.', 'error')
    elif agregar_idioma_db(nombre_idioma):
        flash(f'El idioma "{nombre_idioma}" ha sido agregado con éxito.', 'success')
    else:
        flash(f'Error: El idioma "{nombre_idioma}" ya existe o hubo un error.', 'error')
        
    return redirect(url_for('gestion_idiomas'))

@app.route('/editar_idioma/<int:idioma_id>', methods=['POST'])
@login_required
def editar_idioma(idioma_id):
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores.', 'error')
        return redirect(url_for('panel_admin'))
        
    nuevo_nombre = request.form.get('nombre_idioma_edit').strip()
    
    if not nuevo_nombre:
        flash('El nombre del idioma no puede estar vacío.', 'error')
    elif actualizar_idioma_db(idioma_id, nuevo_nombre):
        flash(f'El idioma ha sido actualizado a "{nuevo_nombre}" con éxito.', 'success')
    else:
        flash(f'Error al actualizar el idioma. (El nombre podría ya existir).', 'error')
        
    return redirect(url_for('gestion_idiomas'))

@app.route('/eliminar_idioma/<int:idioma_id>', methods=['POST'])
@login_required
def eliminar_idioma(idioma_id):
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores.', 'error')
        return redirect(url_for('panel_admin'))
        
    if eliminar_idioma_db(idioma_id):
        flash('Idioma eliminado con éxito.', 'success')
    else:
        flash('Error al intentar eliminar el idioma.', 'error')
        
    return redirect(url_for('gestion_idiomas'))

@app.route('/gestion_quejas')
@login_required
def gestion_quejas():
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores.', 'error')
        return redirect(url_for('panel_guia'))
        
    quejas = obtener_todas_las_quejas()
    estados_posibles = ['pendiente', 'en revision', 'resuelta']
    
    return render_template('gestion_quejas.html', 
                           quejas=quejas,
                           estados_posibles=estados_posibles)

@app.route('/actualizar_estado_queja/<int:queja_id>/<nuevo_estado>', methods=['POST'])
@login_required
def actualizar_estado(queja_id, nuevo_estado):
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores pueden cambiar el estado.', 'error')
        return redirect(url_for('gestion_quejas'))
        
    if nuevo_estado not in ['pendiente', 'en revision', 'resuelta']:
        flash('Estado no válido.', 'error')
        return redirect(url_for('gestion_quejas'))
        
    if actualizar_estado_queja(queja_id, nuevo_estado):
        flash(f'El estado de la queja #{queja_id} se actualizó a "{nuevo_estado}".', 'success')
    else:
        flash(f'Error al actualizar el estado de la queja #{queja_id}.', 'error')
        
    return redirect(url_for('gestion_quejas'))

# RUTA NUEVA: ELIMINACIÓN DE QUEJAS
@app.route('/eliminar_queja/<int:queja_id>', methods=['POST'])
@login_required
def eliminar_queja(queja_id):
    if session.get('user_rol') != 'admin':
        flash('Acceso denegado: Solo administradores pueden eliminar quejas.', 'error')
        return redirect(url_for('gestion_quejas'))
        
    if eliminar_queja_db(queja_id):
        flash(f'La queja #{queja_id} ha sido eliminada permanentemente.', 'success')
    else:
        flash(f'Error al intentar eliminar la queja #{queja_id}.', 'error')
        
    return redirect(url_for('gestion_quejas'))


# --------------------------------------------------------------------------
# Inicialización
# --------------------------------------------------------------------------

if __name__ == '__main__':
    inicializar_db() 
    app.run(debug=True)
