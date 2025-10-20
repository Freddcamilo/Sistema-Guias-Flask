# db_manager.py - Adaptado para PostgreSQL

import os
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from psycopg2 import sql # Necesario para manejar identificadores y consultas dinámicas
from dotenv import load_dotenv # Opcional: para cargar DATABASE_URL localmente

# Cargar variables de entorno si usas un archivo .env local
# load_dotenv()

ADMIN_LICENCIA = 'ADMIN001'
ADMIN_PASSWORD_DEFAULT = 'admin123' 

def get_db_connection():
    """Establece la conexión con la base de datos PostgreSQL usando la URL de entorno."""
    
    # Render, Railway o cualquier hosting proporcionará esta variable.
    # Para pruebas locales, defínela manualmente o usa dotenv.
    DATABASE_URL = os.environ.get('DATABASE_URL') 
    
    if not DATABASE_URL:
        # Aquí puedes definir una URL de prueba local si lo deseas, o lanzar un error.
        raise Exception("Error de configuración: La variable de entorno 'DATABASE_URL' no está definida.")
        
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Error al conectar con PostgreSQL: {e}")
        raise e


# --------------------------------------------------------------------------
# 1. INICIALIZACIÓN Y ESQUEMAS
# --------------------------------------------------------------------------

def inicializar_db():
    """Crea todas las tablas ajustando la sintaxis a PostgreSQL."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tabla GUIAS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS GUIAS (
                licencia VARCHAR(10) PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                rol VARCHAR(50) NOT NULL DEFAULT 'guia',
                aprobado INTEGER NOT NULL DEFAULT 0,
                telefono VARCHAR(50) DEFAULT '',        
                email VARCHAR(255) DEFAULT '',           
                bio TEXT DEFAULT '',             
                fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
    
        # Tabla IDIOMAS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS IDIOMAS (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL UNIQUE
            );
        """)
        
        # Tabla GUIA_IDIOMAS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS GUIA_IDIOMAS (
                licencia VARCHAR(10) NOT NULL,
                idioma_id INTEGER NOT NULL,
                PRIMARY KEY (licencia, idioma_id),
                FOREIGN KEY (licencia) REFERENCES GUIAS (licencia) ON DELETE CASCADE,
                FOREIGN KEY (idioma_id) REFERENCES IDIOMAS (id) ON DELETE CASCADE
            );
        """)

        # Tabla QUEJAS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS QUEJAS (
                id SERIAL PRIMARY KEY,
                licencia_guia VARCHAR(10) NOT NULL,
                fecha_queja TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                descripcion TEXT NOT NULL,
                estado VARCHAR(50) NOT NULL DEFAULT 'pendiente', 
                reportado_por TEXT, 
                FOREIGN KEY (licencia_guia) REFERENCES GUIAS (licencia) ON DELETE CASCADE
            );
        """)

        # Tabla DISPONIBILIDAD_FECHAS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DISPONIBILIDAD_FECHAS (
                id SERIAL PRIMARY KEY,
                licencia_guia VARCHAR(10) NOT NULL,
                fecha DATE NOT NULL,
                hora_inicio TIME NOT NULL,
                hora_fin TIME NOT NULL,
                FOREIGN KEY (licencia_guia) REFERENCES GUIAS (licencia) ON DELETE CASCADE,
                UNIQUE (licencia_guia, fecha) 
            );
        """)

        # Asegurar Administrador Principal
        admin_password_hash = generate_password_hash(ADMIN_PASSWORD_DEFAULT)
        cursor.execute("SELECT COUNT(*) FROM GUIAS WHERE licencia = %s", (ADMIN_LICENCIA,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO GUIAS (licencia, nombre, password, rol, aprobado) 
                VALUES (%s, %s, %s, 'admin', 1)
            """, (ADMIN_LICENCIA, 'Administrador Principal', admin_password_hash))
            
        conn.commit()
    except psycopg2.Error as e:
        print(f"Error al inicializar DB: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --------------------------------------------------------------------------
# 2. FUNCIONES DE REGISTRO Y LOGIN (Cambio de ? a %s)
# --------------------------------------------------------------------------

def registrar_guia(licencia, nombre, password):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        cursor.execute("INSERT INTO GUIAS (licencia, nombre, password, rol, aprobado) VALUES (%s, %s, %s, 'guia', 0)", 
                       (licencia, nombre, password_hash))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        return False
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def get_guia_data(licencia, all_data=False):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM GUIAS WHERE licencia = %s" if all_data else "SELECT password, rol, aprobado FROM GUIAS WHERE licencia = %s"
        cursor.execute(query, (licencia,)) 
        data = cursor.fetchone()
        return data
    except psycopg2.Error:
        return None
    finally:
        if conn: conn.close()

# --------------------------------------------------------------------------
# 3. FUNCIONES DE ADMINISTRACIÓN (CRUD Guías)
# --------------------------------------------------------------------------

def obtener_todos_los_guias():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT licencia, nombre, rol, aprobado, fecha_registro, telefono, email FROM GUIAS ORDER BY fecha_registro DESC")
        guias = cursor.fetchall()
        return guias
    except psycopg2.Error:
        return []
    finally:
        if conn: conn.close()

def cambiar_aprobacion(licencia, estado):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE GUIAS SET aprobado = %s WHERE licencia = %s", (estado, licencia))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def eliminar_guia(licencia):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM GUIAS WHERE licencia = %s", (licencia,))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def promover_a_admin(licencia):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE GUIAS SET rol = 'admin' WHERE licencia = %s AND rol != 'admin'", (licencia,))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def degradar_a_guia(licencia):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if licencia == ADMIN_LICENCIA:
            return False 
        cursor.execute("UPDATE GUIAS SET rol = 'guia' WHERE licencia = %s AND rol = 'admin'", (licencia,))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

# --------------------------------------------------------------------------
# 4. FUNCIONES DE IDIOMAS (ADMIN/GUÍA)
# --------------------------------------------------------------------------

def agregar_idioma_db(nombre_idioma):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO IDIOMAS (nombre) VALUES (%s)", (nombre_idioma,))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        return False
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def obtener_todos_los_idiomas():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM IDIOMAS ORDER BY nombre ASC")
        idiomas = cursor.fetchall()
        return idiomas
    except psycopg2.Error:
        return []
    finally:
        if conn: conn.close()

def actualizar_idioma_db(idioma_id, nuevo_nombre):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE IDIOMAS SET nombre = %s WHERE id = %s", (nuevo_nombre, idioma_id))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.IntegrityError:
        return False
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def eliminar_idioma_db(idioma_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM IDIOMAS WHERE id = %s", (idioma_id,))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def obtener_idiomas_de_guia(licencia):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT idioma_id FROM GUIA_IDIOMAS WHERE licencia = %s", (licencia,))
        idiomas_ids = [row[0] for row in cursor.fetchall()]
        return idiomas_ids
    except psycopg2.Error:
        return []
    finally:
        if conn: conn.close()

def actualizar_idiomas_de_guia(licencia, idioma_ids):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM GUIA_IDIOMAS WHERE licencia = %s", (licencia,))
        if idioma_ids:
            # Preparar datos para el multi-insert
            data = [(licencia, int(idioma_id)) for idioma_id in idioma_ids]
            
            # Crear la sentencia SQL de inserción múltiple para PostgreSQL
            insert_query = "INSERT INTO GUIA_IDIOMAS (licencia, idioma_id) VALUES (%s, %s)"
            
            # Ejecutar el multi-insert
            cursor.executemany(insert_query, data)

        conn.commit()
        return True
    except psycopg2.Error:
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

def obtener_idiomas_de_multiples_guias(licencias):
    """
    Obtiene los nombres de los idiomas dominados para una lista de licencias de guías.
    Devuelve un diccionario: {licencia: 'Idioma1, Idioma2, ...'}
    """
    if not licencias:
        return {}
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Usamos sql.SQL e sql.Identifier para seguridad con la función string_agg de PostgreSQL
        # Reemplazamos GROUP_CONCAT por STRING_AGG
        placeholders = sql.SQL(',').join(sql.Placeholder() * len(licencias))
        
        query = sql.SQL("""
            SELECT 
                GI.licencia, 
                STRING_AGG(I.nombre, ', ') as idiomas_dominados
            FROM GUIA_IDIOMAS GI
            JOIN IDIOMAS I ON GI.idioma_id = I.id
            WHERE GI.licencia IN ({})
            GROUP BY GI.licencia
        """).format(placeholders)

        cursor.execute(query, licencias)
        
        idiomas_por_guia = {row[0]: row[1] for row in cursor.fetchall()}
        return idiomas_por_guia
    except psycopg2.Error:
        return {}
    finally:
        if conn: conn.close()


# --------------------------------------------------------------------------
# 5. FUNCIONES DE PERFIL EXTENDIDO (GUÍA)
# --------------------------------------------------------------------------

def actualizar_password_db(licencia, nueva_password):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        password_hash = generate_password_hash(nueva_password)
        cursor.execute("UPDATE GUIAS SET password = %s WHERE licencia = %s", (password_hash, licencia))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def actualizar_perfil_db(licencia, nuevo_nombre, nuevo_telefono, nuevo_email, nueva_bio):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE GUIAS SET nombre = %s, telefono = %s, email = %s, bio = %s WHERE licencia = %s", 
                       (nuevo_nombre, nuevo_telefono, nuevo_email, nueva_bio, licencia))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

# --------------------------------------------------------------------------
# 6. FUNCIONES DE GESTIÓN DE QUEJAS
# --------------------------------------------------------------------------

def registrar_queja(licencia_guia, descripcion, reportado_por=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO QUEJAS (licencia_guia, descripcion, reportado_por, estado) VALUES (%s, %s, %s, 'pendiente')", 
                       (licencia_guia, descripcion, reportado_por))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        return False
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def obtener_todas_las_quejas():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT q.id, q.licencia_guia, g.nombre, q.fecha_queja, q.descripcion, q.estado, q.reportado_por
            FROM QUEJAS q JOIN GUIAS g ON q.licencia_guia = g.licencia
            ORDER BY q.fecha_queja DESC
        """)
        quejas = cursor.fetchall()
        return quejas
    except psycopg2.Error:
        return []
    finally:
        if conn: conn.close()

def obtener_todas_las_quejas_para_guias():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                q.id, 
                q.licencia_guia, 
                g.nombre as nombre_guia,
                q.fecha_queja, 
                q.descripcion, 
                q.estado, 
                q.reportado_por
            FROM QUEJAS q
            JOIN GUIAS g ON q.licencia_guia = g.licencia
            ORDER BY q.fecha_queja DESC
        """)
        quejas = cursor.fetchall()
        return quejas
    except psycopg2.Error:
        return []
    finally:
        if conn: conn.close()


def actualizar_estado_queja(queja_id, nuevo_estado):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE QUEJAS SET estado = %s WHERE id = %s", (nuevo_estado, queja_id))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def eliminar_queja_db(queja_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM QUEJAS WHERE id = %s", (queja_id,))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

# --------------------------------------------------------------------------
# 7. FUNCIONES DE DISPONIBILIDAD (SOLO FECHAS) Y BÚSQUEDA
# --------------------------------------------------------------------------

def agregar_disponibilidad_fecha(licencia_guia, fecha, hora_inicio, hora_fin):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO DISPONIBILIDAD_FECHAS (licencia_guia, fecha, hora_inicio, hora_fin) VALUES (%s, %s, %s, %s)", 
                       (licencia_guia, fecha, hora_inicio, hora_fin))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        return False
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def obtener_disponibilidad_fechas(licencia_guia):
    conn = get_db_connection()
    data = []
    try:
        cursor = conn.cursor()
        # En PostgreSQL, usamos AGE para comparar fechas/tiempos, pero aquí DATE(NOW()) es suficiente para comparar solo la fecha.
        cursor.execute("""
            SELECT id, fecha, hora_inicio as inicio, hora_fin as fin
            FROM DISPONIBILIDAD_FECHAS 
            WHERE licencia_guia = %s AND fecha >= CURRENT_DATE
            ORDER BY fecha ASC
        """, (licencia_guia,))
        
        # Obtenemos los nombres de las columnas para crear diccionarios (similar a row_factory)
        column_names = [desc[0] for desc in cursor.description]
        data = [dict(zip(column_names, row)) for row in cursor.fetchall()]
        return data
    except psycopg2.Error:
        return []
    finally:
        if conn: conn.close()

def eliminar_disponibilidad_fecha(fecha_id, licencia_guia):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM DISPONIBILIDAD_FECHAS WHERE id = %s AND licencia_guia = %s", 
                       (fecha_id, licencia_guia))
        conn.commit()
        return cursor.rowcount > 0
    except psycopg2.Error:
        return False
    finally:
        if conn: conn.close()

def buscar_guias_disponibles_por_fecha(fecha_buscada, idioma_id=None):
    conn = get_db_connection()
    guias = []
    try:
        cursor = conn.cursor()
        
        base_query = """
            SELECT 
                G.licencia, G.nombre, G.telefono, G.email, G.bio, 
                TO_CHAR(DF.hora_inicio, 'HH24:MI') as hora_inicio, 
                TO_CHAR(DF.hora_fin, 'HH24:MI') as hora_fin
            FROM GUIAS G
            JOIN DISPONIBILIDAD_FECHAS DF ON G.licencia = DF.licencia_guia
            WHERE DF.fecha = %s AND G.aprobado = 1
        """
        params = [fecha_buscada]
        
        if idioma_id:
            base_query += """
                AND G.licencia IN (
                    SELECT licencia FROM GUIA_IDIOMAS WHERE idioma_id = %s
                )
            """
            params.append(idioma_id)
            
        base_query += " ORDER BY G.nombre"
        
        cursor.execute(base_query, params)
        
        column_names = [desc[0] for desc in cursor.description]
        guias = [dict(zip(column_names, row)) for row in cursor.fetchall()]

        licencias = [g['licencia'] for g in guias]
        idiomas_por_guia = obtener_idiomas_de_multiples_guias(licencias)
        
        for guia in guias:
            guia['idiomas_dominados'] = idiomas_por_guia.get(guia['licencia'], 'N/A')
            
        return guias
    except psycopg2.Error as e:
        print(f"Error en búsqueda: {e}")
        return []
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    # Esto solo funcionará si tienes la variable DATABASE_URL definida localmente para pruebas.
    try:
        print("Intentando inicializar la DB con PostgreSQL...")
        inicializar_db()
        print("Inicialización de la base de datos completada (o tablas ya existían).")
    except Exception as e:
        print(f"FALLO: No se pudo inicializar la DB. Asegúrate de definir la variable DATABASE_URL. Error: {e}")
