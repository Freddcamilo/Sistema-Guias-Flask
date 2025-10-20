# db_manager.py

import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DATABASE = 'guias.db'
ADMIN_LICENCIA = 'ADMIN001'
ADMIN_PASSWORD_DEFAULT = 'admin123' 

def get_db_connection():
    """Establece la conexión con la base de datos."""
    conn = sqlite3.connect(DATABASE)
    return conn

# --------------------------------------------------------------------------
# 1. INICIALIZACIÓN Y ESQUEMAS
# --------------------------------------------------------------------------

def inicializar_db():
    """Crea todas las tablas: GUIAS, IDIOMAS, GUIA_IDIOMAS, QUEJAS y DISPONIBILIDAD_FECHAS."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla GUIAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GUIAS (
            licencia TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'guia',
            aprobado INTEGER NOT NULL DEFAULT 0,
            telefono TEXT DEFAULT '',        
            email TEXT DEFAULT '',           
            bio TEXT DEFAULT '',             
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    try:
        cursor.execute("ALTER TABLE GUIAS ADD COLUMN telefono TEXT DEFAULT ''")
        cursor.execute("ALTER TABLE GUIAS ADD COLUMN email TEXT DEFAULT ''")
        cursor.execute("ALTER TABLE GUIAS ADD COLUMN bio TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass 
    
    # Tablas IDIOMAS y GUIA_IDIOMAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS IDIOMAS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GUIA_IDIOMAS (
            licencia TEXT NOT NULL,
            idioma_id INTEGER NOT NULL,
            PRIMARY KEY (licencia, idioma_id),
            FOREIGN KEY (licencia) REFERENCES GUIAS (licencia) ON DELETE CASCADE,
            FOREIGN KEY (idioma_id) REFERENCES IDIOMAS (id) ON DELETE CASCADE
        );
    """)

    # Tabla QUEJAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS QUEJAS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            licencia_guia TEXT NOT NULL,
            fecha_queja TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            descripcion TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente', 
            reportado_por TEXT, 
            FOREIGN KEY (licencia_guia) REFERENCES GUIAS (licencia) ON DELETE CASCADE
        );
    """)

    # Tabla DISPONIBILIDAD_FECHAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS DISPONIBILIDAD_FECHAS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            licencia_guia TEXT NOT NULL,
            fecha DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fin TIME NOT NULL,
            FOREIGN KEY (licencia_guia) REFERENCES GUIAS (licencia) ON DELETE CASCADE,
            UNIQUE (licencia_guia, fecha) 
        );
    """)

    # Asegurar Administrador Principal
    admin_password_hash = generate_password_hash(ADMIN_PASSWORD_DEFAULT)
    cursor.execute("SELECT COUNT(*) FROM GUIAS WHERE licencia = ?", (ADMIN_LICENCIA,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO GUIAS (licencia, nombre, password, rol, aprobado) 
            VALUES (?, ?, ?, 'admin', 1)
        """, (ADMIN_LICENCIA, 'Administrador Principal', admin_password_hash))
        
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# 2. FUNCIONES DE REGISTRO Y LOGIN
# --------------------------------------------------------------------------

def registrar_guia(licencia, nombre, password):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        cursor.execute("INSERT INTO GUIAS (licencia, nombre, password, rol, aprobado) VALUES (?, ?, ?, 'guia', 0)", (licencia, nombre, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_guia_data(licencia, all_data=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM GUIAS WHERE licencia = ?" if all_data else "SELECT password, rol, aprobado FROM GUIAS WHERE licencia = ?"
    cursor.execute(query, (licencia,)) 
    data = cursor.fetchone()
    conn.close()
    return data

# --------------------------------------------------------------------------
# 3. FUNCIONES DE ADMINISTRACIÓN (CRUD Guías)
# --------------------------------------------------------------------------

def obtener_todos_los_guias():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT licencia, nombre, rol, aprobado, fecha_registro, telefono, email FROM GUIAS ORDER BY fecha_registro DESC")
    guias = cursor.fetchall()
    conn.close()
    return guias

def cambiar_aprobacion(licencia, estado):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE GUIAS SET aprobado = ? WHERE licencia = ?", (estado, licencia))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def eliminar_guia(licencia):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM GUIAS WHERE licencia = ?", (licencia,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def promover_a_admin(licencia):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE GUIAS SET rol = 'admin' WHERE licencia = ? AND rol != 'admin'", (licencia,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def degradar_a_guia(licencia):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if licencia == ADMIN_LICENCIA:
            return False 
        cursor.execute("UPDATE GUIAS SET rol = 'guia' WHERE licencia = ? AND rol = 'admin'", (licencia,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

# --------------------------------------------------------------------------
# 4. FUNCIONES DE IDIOMAS (ADMIN/GUÍA)
# --------------------------------------------------------------------------

def agregar_idioma_db(nombre_idioma):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO IDIOMAS (nombre) VALUES (?)", (nombre_idioma,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def obtener_todos_los_idiomas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM IDIOMAS ORDER BY nombre ASC")
    idiomas = cursor.fetchall()
    conn.close()
    return idiomas

def actualizar_idioma_db(idioma_id, nuevo_nombre):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE IDIOMAS SET nombre = ? WHERE id = ?", (nuevo_nombre, idioma_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def eliminar_idioma_db(idioma_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM IDIOMAS WHERE id = ?", (idioma_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def obtener_idiomas_de_guia(licencia):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT idioma_id FROM GUIA_IDIOMAS WHERE licencia = ?", (licencia,))
    idiomas_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return idiomas_ids

def actualizar_idiomas_de_guia(licencia, idioma_ids):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM GUIA_IDIOMAS WHERE licencia = ?", (licencia,))
        if idioma_ids:
            data = [(licencia, int(idioma_id)) for idioma_id in idioma_ids]
            cursor.executemany("INSERT INTO GUIA_IDIOMAS (licencia, idioma_id) VALUES (?, ?)", data)
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()

def obtener_idiomas_de_multiples_guias(licencias):
    """
    Obtiene los nombres de los idiomas dominados para una lista de licencias de guías.
    Devuelve un diccionario: {licencia: 'Idioma1, Idioma2, ...'}
    """
    if not licencias:
        return {}
        
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(licencias))
    
    cursor.execute(f"""
        SELECT 
            GI.licencia, 
            GROUP_CONCAT(I.nombre, ', ') as idiomas_dominados
        FROM GUIA_IDIOMAS GI
        JOIN IDIOMAS I ON GI.idioma_id = I.id
        WHERE GI.licencia IN ({placeholders})
        GROUP BY GI.licencia
    """, licencias)
    
    idiomas_por_guia = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return idiomas_por_guia


# --------------------------------------------------------------------------
# 5. FUNCIONES DE PERFIL EXTENDIDO (GUÍA)
# --------------------------------------------------------------------------

def actualizar_password_db(licencia, nueva_password):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        password_hash = generate_password_hash(nueva_password)
        cursor.execute("UPDATE GUIAS SET password = ? WHERE licencia = ?", (password_hash, licencia))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def actualizar_perfil_db(licencia, nuevo_nombre, nuevo_telefono, nuevo_email, nueva_bio):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE GUIAS SET nombre = ?, telefono = ?, email = ?, bio = ? WHERE licencia = ?", 
                       (nuevo_nombre, nuevo_telefono, nuevo_email, nueva_bio, licencia))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

# --------------------------------------------------------------------------
# 6. FUNCIONES DE GESTIÓN DE QUEJAS
# --------------------------------------------------------------------------

def registrar_queja(licencia_guia, descripcion, reportado_por=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO QUEJAS (licencia_guia, descripcion, reportado_por, estado) VALUES (?, ?, ?, 'pendiente')", 
                       (licencia_guia, descripcion, reportado_por))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def obtener_todas_las_quejas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.id, q.licencia_guia, g.nombre, q.fecha_queja, q.descripcion, q.estado, q.reportado_por
        FROM QUEJAS q JOIN GUIAS g ON q.licencia_guia = g.licencia
        ORDER BY q.fecha_queja DESC
    """)
    quejas = cursor.fetchall()
    conn.close()
    return quejas

def obtener_todas_las_quejas_para_guias():
    """Obtiene todas las quejas registradas con el nombre del guía afectado.
       Usada por los guías para ver el panorama completo."""
    conn = get_db_connection()
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
    conn.close()
    return quejas


def actualizar_estado_queja(queja_id, nuevo_estado):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE QUEJAS SET estado = ? WHERE id = ?", (nuevo_estado, queja_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def eliminar_queja_db(queja_id):
    """Elimina una queja específica de la tabla QUEJAS por su ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM QUEJAS WHERE id = ?", (queja_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

# --------------------------------------------------------------------------
# 7. FUNCIONES DE DISPONIBILIDAD (SOLO FECHAS) Y BÚSQUEDA
# --------------------------------------------------------------------------

def agregar_disponibilidad_fecha(licencia_guia, fecha, hora_inicio, hora_fin):
    """Registra una nueva fecha específica de disponibilidad."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO DISPONIBILIDAD_FECHAS (licencia_guia, fecha, hora_inicio, hora_fin) VALUES (?, ?, ?, ?)", 
                       (licencia_guia, fecha, hora_inicio, hora_fin))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def obtener_disponibilidad_fechas(licencia_guia):
    """Obtiene todas las fechas específicas de disponibilidad de un guía (solo futuras o actuales)."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, fecha, hora_inicio as inicio, hora_fin as fin
        FROM DISPONIBILIDAD_FECHAS 
        WHERE licencia_guia = ? AND fecha >= DATE('now', 'localtime')
        ORDER BY fecha ASC
    """, (licencia_guia,))
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

def eliminar_disponibilidad_fecha(fecha_id, licencia_guia):
    """Elimina una fecha específica de disponibilidad."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM DISPONIBILIDAD_FECHAS WHERE id = ? AND licencia_guia = ?", 
                       (fecha_id, licencia_guia))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def buscar_guias_disponibles_por_fecha(fecha_buscada, idioma_id=None):
    """
    Busca guías que tienen disponibilidad registrada para la fecha_buscada,
    opcionalmente filtrado por un idioma específico, y enriquece con los idiomas dominados.
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    base_query = """
        SELECT 
            G.licencia, G.nombre, G.telefono, G.email, G.bio, 
            DF.hora_inicio, DF.hora_fin
        FROM GUIAS G
        JOIN DISPONIBILIDAD_FECHAS DF ON G.licencia = DF.licencia_guia
        WHERE DF.fecha = ? AND G.aprobado = 1
    """
    params = [fecha_buscada]
    
    if idioma_id:
        base_query += """
            AND G.licencia IN (
                SELECT licencia FROM GUIA_IDIOMAS WHERE idioma_id = ?
            )
        """
        params.append(idioma_id)
        
    base_query += " ORDER BY G.nombre"
    
    cursor.execute(base_query, params)
    guias = [dict(row) for row in cursor.fetchall()]
    
    conn.close()

    licencias = [g['licencia'] for g in guias]
    idiomas_por_guia = obtener_idiomas_de_multiples_guias(licencias)
    
    for guia in guias:
        guia['idiomas_dominados'] = idiomas_por_guia.get(guia['licencia'], 'N/A')
        
    return guias


if __name__ == '__main__':
    inicializar_db()
