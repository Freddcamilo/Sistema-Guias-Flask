import sqlite3
from werkzeug.security import generate_password_hash

# Configuración de la Base de Datos
DATABASE = 'machupicchu_guias.db'

def conectar_db():
    return sqlite3.connect(DATABASE)

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()

    # Habilitar claves foráneas
    cursor.execute("PRAGMA foreign_keys = ON")

    # --------------------------------------------------------------------------
    # 1. Tabla GUIAS (ATENCIÓN: Se incluye 'licencia' para corregir el error)
    # --------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GUIAS (
            guia_id INTEGER PRIMARY KEY AUTOINCREMENT,
            licencia TEXT UNIQUE NOT NULL,  
            nombre TEXT NOT NULL,
            password TEXT NOT NULL,
            tarifa_base REAL DEFAULT 50.00,
            celular TEXT,
            observaciones TEXT
        );
    """)
    print("Tabla GUIAS creada/verificada.")

    # --------------------------------------------------------------------------
    # 2. Tabla IDIOMAS (Maestra)
    # --------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS IDIOMAS (
            idioma_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        );
    """)
    print("Tabla IDIOMAS creada/verificada.")

    # --------------------------------------------------------------------------
    # 3. Tabla GUIA_IDIOMAS (Relación Muchos a Muchos)
    # --------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GUIAS_IDIOMAS (
            guia_id INTEGER,
            idioma_id INTEGER,
            PRIMARY KEY (guia_id, idioma_id),
            FOREIGN KEY (guia_id) REFERENCES GUIAS(guia_id) ON DELETE CASCADE,
            FOREIGN KEY (idioma_id) REFERENCES IDIOMAS(idioma_id) ON DELETE CASCADE
        );
    """)
    print("Tabla GUIAS_IDIOMAS creada/verificada.")
    
    # --------------------------------------------------------------------------
    # 4. Tabla DISPONIBILIDAD (Para reservas)
    # --------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS DISPONIBILIDAD (
            disponibilidad_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guia_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            estado TEXT DEFAULT 'Disponible',
            FOREIGN KEY (guia_id) REFERENCES GUIAS(guia_id) ON DELETE CASCADE,
            UNIQUE (guia_id, fecha, hora_inicio)
        );
    """)
    print("Tabla DISPONIBILIDAD creada/verificada.")
    
    # --------------------------------------------------------------------------
    # 5. Tabla RESERVAS
    # --------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RESERVAS (
            reserva_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guia_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            duracion_horas REAL NOT NULL,
            nombre_cliente TEXT NOT NULL,
            contacto_cliente TEXT,
            estado TEXT DEFAULT 'Pendiente',
            costo_total REAL NOT NULL,
            FOREIGN KEY (guia_id) REFERENCES GUIAS(guia_id) ON DELETE CASCADE
        );
    """)
    print("Tabla RESERVAS creada/verificada.")
    
    # --------------------------------------------------------------------------
    # Datos de Prueba
    # --------------------------------------------------------------------------
    
    # Insertar Guía de Prueba
    guia_test_licencia = 'TEST101'
    cursor.execute("SELECT guia_id FROM GUIAS WHERE licencia = ?", (guia_test_licencia,))
    if cursor.fetchone() is None:
        hashed_password = generate_password_hash('1234')
        cursor.execute("""
            INSERT INTO GUIAS (licencia, nombre, password, tarifa_base, celular)
            VALUES (?, ?, ?, ?, ?)
        """, (guia_test_licencia, 'Guía de Prueba', hashed_password, 60.00, '+51999888777'))
        print("Guía de prueba insertado.")
    else:
        print("Guía de prueba ya existe.")
    
    # Insertar Idiomas Maestros
    idiomas_maestros = ['Español', 'Inglés', 'Quechua', 'Portugués', 'Alemán']
    idiomas_ids = {}
    for idioma in idiomas_maestros:
        cursor.execute("SELECT idioma_id FROM IDIOMAS WHERE nombre = ?", (idioma,))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO IDIOMAS (nombre) VALUES (?)", (idioma,))
            idiomas_ids[idioma] = cursor.lastrowid
        else:
            idiomas_ids[idioma] = row[0]
    print("Idiomas maestros verificados/insertados.")

    # Asignar Idiomas al Guía de Prueba
    guia_test_id = cursor.execute("SELECT guia_id FROM GUIAS WHERE licencia = ?", (guia_test_licencia,)).fetchone()[0]
    
    # Asignar Español e Inglés al Guía de Prueba
    for idioma_nombre in ['Español', 'Inglés']:
        idioma_id = cursor.execute("SELECT idioma_id FROM IDIOMAS WHERE nombre = ?", (idioma_nombre,)).fetchone()[0]
        cursor.execute("SELECT guia_id FROM GUIAS_IDIOMAS WHERE guia_id = ? AND idioma_id = ?", (guia_test_id, idioma_id))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO GUIAS_IDIOMAS (guia_id, idioma_id) VALUES (?, ?)", (guia_test_id, idioma_id))
    print("Idiomas asignados al guía de prueba.")

    conn.commit()
    conn.close()
    print("Base de datos inicializada con éxito.")

if __name__ == '__main__':
    inicializar_db()
