# D:\guia_mp_nuevo\db_manager.py

import sqlite3
import hashlib

DATABASE_NAME = 'machupicchu_guias.db'

def hash_password(password):
    """Cifra la contraseña usando SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def inicializar_db():
    """Crea la base de datos y todas las tablas si no existen."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Habilitar soporte para claves foráneas (clave en SQLite)
    conn.execute("PRAGMA foreign_keys = ON") 

    # --- 1. Tabla GUIAS (Guías Turísticos) ---
    # Columna 'celular' añadida aquí.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GUIAS (
            guia_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            licencia_no TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            tarifa_base REAL DEFAULT 50.00,
            celular TEXT -- ¡COLUMNA DE CELULAR AÑADIDA!
        );
    """)
    print("Tabla GUIAS creada/verificada.")

    # --- 2. Tabla IDIOMAS (Lista Maestra de Idiomas) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS IDIOMAS (
            idioma_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_idioma TEXT UNIQUE NOT NULL
        );
    """)
    print("Tabla IDIOMAS creada/verificada.")

    # --- 3. Tabla GUIAS_IDIOMAS (Relación Muchos a Muchos) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GUIAS_IDIOMAS (
            guia_id INTEGER,
            idioma_id INTEGER,
            nivel TEXT CHECK(nivel IN ('Básico', 'Intermedio', 'Avanzado', 'Nativo')),
            PRIMARY KEY (guia_id, idioma_id),
            FOREIGN KEY (guia_id) REFERENCES GUIAS(guia_id) ON DELETE CASCADE,
            FOREIGN KEY (idioma_id) REFERENCES IDIOMAS(idioma_id) ON DELETE CASCADE
        );
    """)
    print("Tabla GUIAS_IDIOMAS creada/verificada.")

    # --- 4. Tabla DISPONIBILIDAD (Turnos de Trabajo) ---
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
    
    # --- 5. Tabla RESERVAS (Historial de Servicios) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RESERVAS (
            reserva_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guia_id INTEGER NOT NULL,
            fecha_reserva TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            duracion_horas REAL NOT NULL,
            tarifa_total REAL NOT NULL,
            cliente_nombre TEXT,
            cliente_email TEXT,
            estado TEXT CHECK(estado IN ('Confirmada', 'Completada', 'Cancelada')) DEFAULT 'Confirmada',
            FOREIGN KEY (guia_id) REFERENCES GUIAS(guia_id) ON DELETE CASCADE
        );
    """)
    print("Tabla RESERVAS creada/verificada.")


    # --- DATOS INICIALES ---

    # 1. Insertar Guía de Prueba (ID 1)
    try:
        # ¡Celular y Tarifa Base Insertados!
        cursor.execute("INSERT INTO GUIAS (nombre, licencia_no, password, tarifa_base, celular) VALUES (?, ?, ?, ?, ?)", 
                       ('Guia Test', 'TEST101', hash_password('1234'), 50.00, '+51987654321'))
        print("Guía de prueba insertado.")
    except sqlite3.IntegrityError:
        print("Guía de prueba ya existe. Omitiendo inserción.")

    # 2. Insertar Idiomas Maestros
    idiomas = ['Español', 'Inglés', 'Quechua', 'Portugués', 'Alemán', 'Francés']
    for idioma in idiomas:
        try:
            cursor.execute("INSERT INTO IDIOMAS (nombre_idioma) VALUES (?)", (idioma,))
        except sqlite3.IntegrityError:
            pass # Ya existe
    print("Idiomas maestros verificados/insertados.")
    
    # 3. Asignar Idiomas al Guía de Prueba
    # Asignamos Español, Inglés, Quechua al Guía Test (asumiendo guia_id=1)
    guia_test_id = 1
    
    # Obtener IDs de idiomas
    cursor.execute("SELECT idioma_id FROM IDIOMAS WHERE nombre_idioma IN ('Español', 'Inglés', 'Quechua')")
    idioma_ids = [row[0] for row in cursor.fetchall()]
    
    # Asignar con niveles
    asignaciones = [
        (guia_test_id, idioma_ids[0], 'Nativo'), # Español
        (guia_test_id, idioma_ids[1], 'Avanzado'), # Inglés
        (guia_test_id, idioma_ids[2], 'Intermedio') # Quechua
    ]
    
    for asignacion in asignaciones:
        try:
            cursor.execute("INSERT INTO GUIAS_IDIOMAS (guia_id, idioma_id, nivel) VALUES (?, ?, ?)", asignacion)
        except sqlite3.IntegrityError:
            pass # Ya existe
            
    print("Idiomas asignados al guía de prueba.")
    
    conn.commit()
    conn.close()
    print("Base de datos inicializada con éxito.")

if __name__ == '__main__':
    inicializar_db()
