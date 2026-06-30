"""
setup_db.py

Crea la base de datos SQLite del CRM bancario y la puebla con datos fake
para un (1) cliente de demo.

Uso:
    python setup_db.py

Esto genera (o recrea) el archivo crm.db en el mismo directorio.
"""

import sqlite3
from datetime import date

DB_PATH = "data/crm.db"


def crear_tablas(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS solicitudes_aumento")
    cursor.execute("DROP TABLE IF EXISTS pagos")
    cursor.execute("DROP TABLE IF EXISTS tarjetas")
    cursor.execute("DROP TABLE IF EXISTS clientes")

    cursor.execute(
        """
        CREATE TABLE clientes (
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre     TEXT NOT NULL,
            apellido   TEXT NOT NULL,
            dni        TEXT NOT NULL UNIQUE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE tarjetas (
            id_tarjeta       INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente       INTEGER NOT NULL,
            nro              TEXT NOT NULL,
            codigo           TEXT NOT NULL,
            fecha_vencimiento TEXT NOT NULL,
            fecha_cierre     TEXT NOT NULL,
            estado           TEXT NOT NULL,
            limite           REAL NOT NULL,
            saldo            REAL NOT NULL,
            FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE pagos (
            id_pago     INTEGER PRIMARY KEY AUTOINCREMENT,
            id_tarjeta  INTEGER NOT NULL,
            fecha_pago  TEXT NOT NULL,
            metodo_pago TEXT NOT NULL,
            monto       REAL NOT NULL,
            FOREIGN KEY (id_tarjeta) REFERENCES tarjetas(id_tarjeta)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE solicitudes_aumento (
            id_solicitud    INTEGER PRIMARY KEY AUTOINCREMENT,
            id_tarjeta      INTEGER NOT NULL,
            nuevo_limite    REAL NOT NULL,
            estado          TEXT NOT NULL,
            fecha_solicitud TEXT NOT NULL,
            FOREIGN KEY (id_tarjeta) REFERENCES tarjetas(id_tarjeta)
        )
        """
    )

    conn.commit()


def poblar_datos(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    # Un único cliente de demo
    cursor.execute(
        """
        INSERT INTO clientes (nombre, apellido, dni)
        VALUES (?, ?, ?)
        """,
        ("Juan", "Perez", "30123456"),
    )
    id_cliente = cursor.lastrowid

    # Una tarjeta para ese cliente
    cursor.execute(
        """
        INSERT INTO tarjetas
            (id_cliente, nro, codigo, fecha_vencimiento, fecha_cierre,
             estado, limite, saldo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id_cliente,
            "4567 **** **** 1234",
            "Gold",
            "2026-07-10",
            "2026-06-25",
            "activa",
            1500000.0,
            450000.0,
        ),
    )
    id_tarjeta = cursor.lastrowid

    # Un pago histórico de ejemplo
    cursor.execute(
        """
        INSERT INTO pagos (id_tarjeta, fecha_pago, metodo_pago, monto)
        VALUES (?, ?, ?, ?)
        """,
        (id_tarjeta, "2026-05-25", "debito_automatico", 380000.0),
    )

    conn.commit()


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        crear_tablas(conn)
        poblar_datos(conn)
        print(f"Base de datos creada en: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()