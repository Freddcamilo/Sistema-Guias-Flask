import os
import psycopg2
from werkzeug.security import generate_password_hash

# La URL de la DB de Render se lee desde las variables de entorno
DATABASE_URL = os.environ.get('DATABASE_URL') 

def conectar_db():
    if not DATABASE_URL:
        # Si no hay URL (prueba local sin la variable), retorna None
        return None 
            
    # Conexión real a PostgreSQL. Usamos sslmode='require' por ser la nube.
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def inicializar_db():
    conn = None
    try:
        conn = conectar_db()
        
        # Si la conexión falló (porque es local y no definimos la variable), salimos.
        if conn is None:
            print("ADVERTENCIA: No se pudo conectar a PostgreSQL (DATABASE_URL no definida). Saltando inicialización.")
            return

        cursor = conn.cursor()
        
        print("Conectado a PostgreSQL. Creando/verificando tablas...")

        # --------------------------------------------------------------------------
        # 1. Tabla GUIAS (PostgreSQL)
        # --------------------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS GUIAS (
                guia_id SERIAL PRIMARY KEY,
                licencia TEXT UNIQUE NOT NULL,  
                nombre TEXT NOT NULL,
                password TEXT NOT NULL,
                tarifa_base NUMERIC DEFAULT 50.00,
                celular TEXT,
                observaciones TEXT
            );
        """)
        print("Tabla GUIAS creada/verificada.")

        # --------------------------------------------------------------------------
        # 2. Tabla IDIOMAS (Maestra - PostgreSQL)
        # --------------------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS IDIOMAS (
                idioma_id SERIAL PRIMARY KEY,
                nombre TEXT UNIQUE NOT NULL
            );
        """)
        print("Tabla IDIOMAS creada/verificada.")

        # --------------------------------------------------------------------------
        # 3. Tabla GUIA_IDIOMAS (Relación Muchos a Muchos - PostgreSQL)
        # --------------------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS GUIAS_IDIOMAS (
                guia_id INTEGER REFERENCES GUIAS(guia_id) ON DELETE CASCADE,
                idioma_id INTEGER REFERENCES IDIOMAS(idioma_id) ON DELETE CASCADE,
                PRIMARY KEY (guia_id, idioma_id)
            );
        """)
        print("Tabla GUIAS_IDIOMAS creada/verificada.")
        
        # --------------------------------------------------------------------------
        # 4. Tabla DISPONIBILIDAD (Para reservas - PostgreSQL)
        # --------------------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DISPONIBILIDAD (
                disponibilidad_id SERIAL PRIMARY KEY,
                guia_id INTEGER NOT NULL REFERENCES GUIAS(guia_id) ON DELETE CASCADE,
                fecha TEXT NOT NULL,
                hora_inicio TEXT NOT NULL,
                hora_fin TEXT NOT NULL,
                estado TEXT DEFAULT 'Disponible',
                UNIQUE (guia_id, fecha, hora_inicio)
            );
        """)
        print("Tabla DISPONIBILIDAD creada/verificada.")
        
        # --------------------------------------------------------------------------
        # 5. Tabla RESERVAS (PostgreSQL)
        # --------------------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS RESERVAS (
                reserva_id SERIAL PRIMARY KEY,
                guia_id INTEGER NOT NULL REFERENCES GUIAS(guia_id) ON DELETE CASCADE,
                fecha TEXT NOT NULL,
                hora_inicio TEXT NOT NULL,
                duracion_horas NUMERIC NOT NULL,
                nombre_cliente TEXT NOT NULL,
                contacto_cliente TEXT,
                estado TEXT DEFAULT 'Pendiente',
                costo_total NUMERIC NOT NULL
            );
        """)
        print("Tabla RESERVAS creada/verificada.")
        
        # --------------------------------------------------------------------------
        # Datos de Prueba (usando %s para PostgreSQL)
        # --------------------------------------------------------------------------
        
        # Insertar Guía de Prueba
        guia_test_licencia = 'TEST101'
        cursor.execute("SELECT guia_id FROM GUIAS WHERE licencia = %s", (guia_test_licencia,))
        if cursor.fetchone() is None:
            hashed_password = generate_password_hash('1234')
            cursor.execute("""
                INSERT INTO GUIAS (licencia, nombre, password, tarifa_base, celular)
                VALUES (%s, %s, %s, %s, %s)
            """, (guia_test_licencia, 'Guía de Prueba', hashed_password, 60.00, '+51999888777'))
            print("Guía de prueba insertado.")
        
        # Insertar Idiomas Maestros
        idiomas_maestros = ['Español', 'Inglés', 'Quechua', 'Portugués', 'Alemán']
        for idioma in idiomas_maestros:
            cursor.execute("SELECT idioma_id FROM IDIOMAS WHERE nombre = %s", (idioma,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO IDIOMAS (nombre) VALUES (%s)", (idioma,))
        
        # Asignar Idiomas al Guía de Prueba
        guia_test_id = cursor.execute("SELECT guia_id FROM GUIAS WHERE licencia = %s", (guia_test_licencia,)).fetchone()[0]
        
        for idioma_nombre in ['Español', 'Inglés']:
            idioma_id = cursor.execute("SELECT idioma_id FROM IDIOMAS WHERE nombre = %s", (idioma_nombre,)).fetchone()[0]
            cursor.execute("SELECT guia_id FROM GUIAS_IDIOMAS WHERE guia_id = %s AND idioma_id = %s", (guia_test_id, idioma_id))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO GUIAS_IDIOMAS (guia_id, idioma_id) VALUES (%s, %s)", (guia_test_id, idioma_id))

        conn.commit()
        print("Base de datos inicializada con éxito.")
        
    except psycopg2.Error as e:
        print(f"Error de PostgreSQL al inicializar la DB: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"Error general: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    inicializar_db()
