import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
# from psycopg2 import sql # No es estrictamente necesario si usamos %s

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
app = Flask(__name__)
# Usamos una clave secreta con un cambio para forzar el reinicio en Render
app.secret_key = 'tu_clave_secreta_aqui_V4' 

# La URL de la DB de Render se lee desde las variables de entorno
DATABASE_URL = os.environ.get('DATABASE_URL') 

# --------------------------------------------------------------------------
# Conexión a la Base de Datos (PostgreSQL)
# --------------------------------------------------------------------------
def conectar_db():
    if not DATABASE_URL:
        # Esto solo aparecerá si intentas correr el app.py localmente sin DATABASE_URL
        raise ValueError("DATABASE_URL no está configurada. Ejecuta la app en Render.")
    
    # Conexión real a PostgreSQL. Usamos sslmode='require' por ser la nube.
    return psycopg2.connect(DATABASE_URL, sslmode='require')

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

        conn = None
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            # Usamos %s para los parámetros en PostgreSQL
            cursor.execute("SELECT password, nombre FROM GUIAS WHERE licencia = %s", (licencia,))
            guia_data = cursor.fetchone()
            
            if guia_data and check_password_hash(guia_data[0], password):
                session['logged_in'] = True
                session['licencia'] = licencia
                session['nombre'] = guia_data[1]
                flash(f'Bienvenido(a), {guia_data[1]}.', 'success')
                return redirect(url_for('panel_guia'))
            else:
                flash('Licencia o Contraseña incorrecta.', 'error')
        except Exception as e:
            flash(f'Error de conexión o consulta: {e}', 'error')
        finally:
            if conn:
                conn.close()

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
        
        hashed_password = generate_password_hash(password)

        conn = None
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO GUIAS (licencia, nombre, password, tarifa_base, celular) 
                VALUES (%s, %s, %s, %s, %s)
            """, (licencia, nombre, hashed_password, tarifa_base, celular))
            
            conn.commit()
            flash(f'Guía "{nombre}" (Licencia: {licencia}) registrado con éxito. ¡Ya puedes iniciar sesión!', 'success')
            return redirect(url_for('login_guia'))
        except psycopg2.IntegrityError:
            flash('El número de Licencia ya está registrado.', 'error')
        except Exception as e:
            flash(f'Ocurrió un error al registrar el guía: {e}', 'error')
        finally:
            if conn:
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
    conn = None
    guias = []
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        # La consulta usa sintaxis de PostgreSQL
        cursor.execute("SELECT guia_id, licencia, nombre, celular, tarifa_base FROM GUIAS")
        guias = cursor.fetchall()
    except Exception as e:
        flash(f'Error al cargar el reporte: {e}', 'error')
    finally:
        if conn:
            conn.close()

    return render_template('reporte_guias.html', guias=guias)


@app.route('/admin/eliminar_guia/<int:guia_id>', methods=['POST'])
def eliminar_guia(guia_id):
    conn = None
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        # Eliminación usando sintaxis de PostgreSQL y %s
        cursor.execute("DELETE FROM GUIAS WHERE guia_id = %s", (guia_id,))
        conn.commit()
        flash(f'Guía ID {guia_id} eliminado con éxito.', 'success')
    except Exception as e:
        flash(f'Error al eliminar el guía: {e}.', 'error')
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('reporte_guias'))

# --------------------------------------------------------------------------

# Asegúrate de que esta parte no se ejecute si Render lo corre con gunicorn
if __name__ == '__main__':
    print("ADVERTENCIA: Iniciando app localmente. Fallará si no hay DATABASE_URL en el entorno local.")
    app.run(debug=True)
