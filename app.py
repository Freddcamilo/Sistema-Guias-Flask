import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
app = Flask(__name__)
# ¡IMPORTANTE! Cambié la clave secreta levemente para forzar el reinicio en Render
app.secret_key = 'tu_clave_secreta_aqui_V2' 
DATABASE = 'machupicchu_guias.db'

# --------------------------------------------------------------------------
# Conexión a la Base de Datos
# --------------------------------------------------------------------------
def conectar_db():
    return sqlite3.connect(DATABASE)

# --------------------------------------------------------------------------
# Rutas Principales
# --------------------------------------------------------------------------

@app.route('/')
@app.route('/menu')
def menu_principal():
    return render_template('menu_principal.html')

# --------------------------------------------------------------------------
# Funciones de Guía (Login, Logout, Registro, Panel)
# --------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
@app.route('/login_guia', methods=['GET', 'POST'])
def login_guia():
    if request.method == 'POST':
        licencia = request.form['licencia']
        password = request.form['password']

        conn = conectar_db()
        cursor = conn.cursor()
        # La consulta ahora usa 'licencia' que fue corregida en db_manager.py
        cursor.execute("SELECT password, nombre FROM GUIAS WHERE licencia = ?", (licencia,))
        guia_data = cursor.fetchone()
        conn.close()

        if guia_data and check_password_hash(guia_data[0], password):
            session['logged_in'] = True
            session['licencia'] = licencia
            session['nombre'] = guia_data[1]
            flash(f'Bienvenido(a), {guia_data[1]}.', 'success')
            return redirect(url_for('panel_guia'))
        else:
            flash('Licencia o Contraseña incorrecta.', 'error')

    return render_template('login_guia.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('licencia', None)
    session.pop('nombre', None)
    flash('Has cerrado tu sesión con éxito.', 'warning')
    return redirect(url_for('menu_principal'))


@app.route('/registrar_guia', methods=['GET', 'POST'])
def registrar_guia():
    if request.method == 'POST':
        licencia = request.form['licencia']
        nombre = request.form['nombre']
        password = request.form['password']
        celular = request.form['celular']
        tarifa_base = request.form['tarifa_base']
        # observaciones ya fue incluida en db_manager.py
        
        hashed_password = generate_password_hash(password)

        conn = conectar_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO GUIAS (licencia, nombre, password, tarifa_base, celular) 
                VALUES (?, ?, ?, ?, ?)
            """, (licencia, nombre, hashed_password, tarifa_base, celular))
            
            conn.commit()
            flash(f'Guía "{nombre}" (Licencia: {licencia}) registrado con éxito. ¡Ya puedes iniciar sesión!', 'success')
            return redirect(url_for('login_guia'))
        except sqlite3.IntegrityError:
            flash('El número de Licencia ya está registrado.', 'error')
        except Exception as e:
            flash(f'Ocurrió un error al registrar el guía: {e}', 'error')
        finally:
            conn.close()

    return render_template('registro_guia.html')


@app.route('/panel_guia')
def panel_guia():
    if not session.get('logged_in'):
        flash('Debes iniciar sesión para acceder al panel.', 'error')
        return redirect(url_for('login_guia'))
    
    return render_template('panel_guia.html')


# --------------------------------------------------------------------------
# Funciones de Reporte y Eliminación (ADMIN/Público)
# --------------------------------------------------------------------------

@app.route('/admin/reporte_guias')
def reporte_guias():
    # Esta ruta es usada como listado público/agencia y por la administración
    conn = conectar_db()
    cursor = conn.cursor()
    
    # La consulta ya está corregida y coincide con db_manager.py
    cursor.execute("SELECT guia_id, licencia, nombre, celular, tarifa_base FROM GUIAS")
    guias = cursor.fetchall()
    conn.close()

    return render_template('reporte_guias.html', guias=guias)


@app.route('/admin/eliminar_guia/<int:guia_id>', methods=['POST'])
def eliminar_guia(guia_id):
    # En un sistema real, esta ruta DEBERÍA estar protegida por un login de 'admin'.
    
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        # Se asume que las tablas relacionadas (GUIAS_IDIOMAS, DISPONIBILIDAD, RESERVAS)
        # tienen ON DELETE CASCADE, por lo que borrar el guía de la tabla principal
        # también borra los datos relacionados.
        cursor.execute("DELETE FROM GUIAS WHERE guia_id = ?", (guia_id,))
        conn.commit()
        flash(f'Guía ID {guia_id} eliminado con éxito.', 'success')
    except Exception as e:
        flash(f'Error al eliminar el guía: {e}.', 'error')
    finally:
        conn.close()
    
    # Redirige de vuelta al reporte
    return redirect(url_for('reporte_guias'))

# --------------------------------------------------------------------------

if __name__ == '__main__':
    # Usamos debug=True para el desarrollo local
    app.run(debug=True)
