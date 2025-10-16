import os
import psycopg2
from werkzeug.security import generate_password_hash

# --------------------------------------------------------------------------
# Conexión a PostgreSQL (usando la variable de entorno de Render)
# --------------------------------------------------------------------------
# Esta variable es proporcionada por Render cuando configuras una PostgreSQL DB
DATABASE_URL = os.environ.get('DATABASE_URL') 

def conectar_db():
    if not DATABASE_URL:
        # En caso de que se ejecute localmente sin la URL de Render, usamos un placeholder.
        # NO NECESITAS ESTO, pero lo dejamos como seguridad.
        # Si se ejecuta en Render, usará DATABASE_URL
        raise ValueError("DATABASE_URL no está configurada. ¿Estás en Render?")

    # Conexión real a PostgreSQL
    return psycopg2.connect(DATABASE_URL)

def inicializar_db():
    conn = None
    try:
        conn = conectar_db()
        cursor = conn.cursor()

        print("Conectado a PostgreSQL. Creando/verificando tablas...")

        # --------------------------------------------------------------------------
        # 1. Tabla GUIAS (ATENCIÓN: Se usa sintaxis de PostgreSQL)
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

        # (Otras tablas - IDIOMAS, GUIAS_IDIOMAS, DISPONIBILIDAD, RESERVAS - irían aquí 
        # usando sintaxis de PostgreSQL similar a la de GUIAS)

        # --- Simplificación para el ejercicio (sólo GUIAS) ---

        # --------------------------------------------------------------------------
        # Datos de Prueba
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
        else:
            print("Guía de prueba ya existe.")

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
    # Esto solo se ejecutará en Render si se configura
    if os.environ.get('DATABASE_URL'):
        inicializar_db()
    else:
        print("ADVERTENCIA: No se puede inicializar la DB de PostgreSQL localmente sin DATABASE_URL.")
