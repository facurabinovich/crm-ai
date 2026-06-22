"""Tools del asistente bancario."""
from db import get_connection
from anthropic.types import ToolParam
from datetime import datetime, timedelta


def get_saldo(cliente_dni: str) -> dict:
    if not cliente_dni:
        raise ValueError("El dni del cliente no puede ser nulo")
    
    conn, cursor = get_connection()
    try:
        cursor.execute(
            """
            SELECT t.nro, t.saldo, t.fecha_vencimiento
            FROM clientes c
            JOIN tarjetas t ON c.id_cliente = t.id_cliente
            WHERE c.dni = ?
            AND t.estado = "activa"
            """,
            (cliente_dni,)
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("El cliente ingresado no existe. Reintentar")
        return {
            "nro_tarjeta": row[0],
            "saldo": row[1],
            "fecha_vencimiento": row[2]
        }
    finally:
        conn.close()

get_saldo_schema = ToolParam({
    "name": "get_saldo",
    "description": "Obtiene el saldo actual, número de tarjeta y fecha de vencimiento de la tarjeta activa de un cliente. Usar esta herramienta cuando el usuario pregunte por su saldo, deuda, o estado de cuenta de su tarjeta. Si el cliente no existe o no tiene una tarjeta activa, la herramienta devuelve un error que debe comunicarse al usuario pidiéndole que reintente.",
    "input_schema": {
        "type": "object",
        "properties": {
            "cliente_dni": {
                "type": "string",
                "description": "Número de DNI del cliente, sin puntos ni espacios. Por ejemplo: '30123456' o '45987123'. Debe obtenerse del contexto de la conversación o de la sesión autenticada del usuario, nunca debe inventarse."
            }
        },
        "required": ["cliente_dni"]
    }
})


def pagar_saldo(cliente_dni:str, monto:int) -> dict:
    if not cliente_dni:
        raise ValueError("El dni del cliente no puede ser nulo")
    if monto <= 0:
        raise ValueError("El monto ingresado no puede ser menor o igual a cero")
    try: 
        conn, cursor = get_connection()
        cursor.execute(
            """
            SELECT t.nro, t.saldo, t.fecha_cierre, t.fecha_vencimiento,t.id_tarjeta
            FROM clientes c
            JOIN tarjetas t ON c.id_cliente = t.id_cliente
            WHERE c.dni = ?
            AND t.estado = "activa"
            """,
            (cliente_dni,)
            )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("El cliente ingresado no existe. Reintentar")
        if row[1] != monto:
            raise ValueError("El monto ingresado no coincide con el saldo a pagar. Ingrese el monto correcto.")
        
        cursor.execute(
                """
                UPDATE tarjetas SET saldo = 0 
                WHERE id_tarjeta = ?       
        
            """,
            (row[4],)
            )
        hoy = str(datetime.now())
        cursor.execute(
            """
            INSERT INTO pagos(id_tarjeta, fecha_pago, metodo_pago, monto) VALUES (?, ?, ?, ?)
             
            """,(row[4],hoy,"transferencia",monto)
        )
        conn.commit()
        return ({
            "nro_tarjeta":row[0],
            "estado":"PAGADO",
            "fecha": hoy, 
            "metodo_pago":"Transferencia"
        })
    finally:
        conn.close()

pagar_saldo_schema = ToolParam({
    "name": "pagar_saldo",
    "description": "Registra el pago del saldo total de la tarjeta activa de un cliente mediante transferencia. El monto ingresado debe coincidir EXACTAMENTE con el saldo actual de la tarjeta (no se permiten pagos parciales); si no coincide, la herramienta devuelve un error indicando que el monto es incorrecto. Usar esta herramienta únicamente cuando el usuario confirme explícitamente que quiere pagar su tarjeta, idealmente después de haber consultado el saldo con get_saldo. Si el cliente no existe o no tiene tarjeta activa, devuelve un error pidiendo reintentar.",
    "input_schema": {
        "type": "object",
        "properties": {
            "cliente_dni": {
                "type": "string",
                "description": "Número de DNI del cliente, sin puntos ni espacios. Por ejemplo: '30123456' o '45987123'. Debe obtenerse del contexto de la conversación o de la sesión autenticada del usuario, nunca debe inventarse."
            },
            "monto": {
                "type": "integer",
                "description": "Monto a pagar, en la misma unidad que el saldo de la tarjeta (sin decimales, sin símbolo de moneda). Debe ser igual al saldo actual de la tarjeta del cliente; consultar primero con get_saldo si no se conoce el valor exacto. Por ejemplo: 45000."
            }
        },
        "required": ["cliente_dni", "monto"]
    }
})
        
        
    

    


def get_fechas(cliente_dni: str) -> dict:
    if not cliente_dni:
        raise ValueError("El dni del cliente no puede ser nulo")
    
    conn, cursor = get_connection()
    try:
        cursor.execute( 
            """
            SELECT t.nro, t.fecha_vencimiento, t.fecha_cierre
            FROM clientes c
            JOIN tarjetas t ON c.id_cliente = t.id_cliente
            WHERE c.dni = ?
            AND t.estado = "activa"
            """,
            (cliente_dni,)    
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("El cliente ingresado no existe. Reintentar")
        return {
            "tarjeta_nro": row[0],
            "fecha_vencimiento": row[1],
            "fecha_cierre": row[2]
        }
    finally:
        conn.close()

get_fechas_schema = ToolParam({
    "name": "get_fechas",
    "description": "Obtiene el número de tarjeta, la fecha de vencimiento y la fecha de cierre de la tarjeta activa de un cliente. Usar esta herramienta cuando el usuario pregunte cuándo vence su tarjeta, cuándo cierra el resumen, o por las fechas importantes de su cuenta. Si el cliente no existe o no tiene una tarjeta activa, la herramienta devuelve un error que debe comunicarse al usuario pidiéndole que reintente.",
    "input_schema": {
        "type": "object",
        "properties": {
            "cliente_dni": {
                "type": "string",
                "description": "Número de DNI del cliente, sin puntos ni espacios. Por ejemplo: '30123456' o '45987123'. Debe obtenerse del contexto de la conversación o de la sesión autenticada del usuario, nunca debe inventarse."
            }
        },
        "required": ["cliente_dni"]
    }
})

def get_limite_tarjeta(cliente_dni:str) -> dict:
    if not cliente_dni:
        raise ValueError("El dni del cliente no puede ser nulo") 
    conn, cursor = get_connection()
    try: 
        cursor.execute(
            """
            SELECT t.nro, t.limite, t.saldo
            FROM clientes c
            JOIN tarjetas t ON c.id_cliente = t.id_cliente
            WHERE c.dni = ?
            AND t.estado = "activa"
            """,
            (cliente_dni,)    
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("El cliente ingresado no existe. Reintentar")
        return ({
            "tarjeta_nro":row[0],
            "limite":row[1],
            "saldo":row[2]
        })
    finally:
        conn.close()

get_limite_tarjeta_schema = ToolParam({
    "name": "get_limite_tarjeta",
    "description": "Obtiene el número de tarjeta, el límite de crédito y el saldo actual de la tarjeta activa de un cliente. Usar esta herramienta cuando el usuario pregunte por su límite de compra, cuánto crédito disponible tiene, o cuánto le queda disponible en la tarjeta. Si el cliente no existe o no tiene una tarjeta activa, la herramienta devuelve un error que debe comunicarse al usuario pidiéndole que reintente.",
    "input_schema": {
        "type": "object",
        "properties": {
            "cliente_dni": {
                "type": "string",
                "description": "Número de DNI del cliente, sin puntos ni espacios. Por ejemplo: '30123456' o '45987123'. Debe obtenerse del contexto de la conversación o de la sesión autenticada del usuario, nunca debe inventarse."
            }
        },
        "required": ["cliente_dni"]
    }
})


def solicitar_aumento_limite(cliente_dni:str, monto_solicitado: float):
    if not cliente_dni:
        raise ValueError("El dni del cliente no puede ser nulo")
    if monto_solicitado <= 0: 
        raise ValueError("El monto solicitado debe ser mayor a cero")
    conn, cursor = get_connection()
    try: 
        cursor.execute(
            """
            SELECT t.nro, t.limite,t.id_tarjeta
            FROM clientes c
            JOIN tarjetas t ON c.id_cliente = t.id_cliente
            WHERE c.dni = ?
            AND t.estado = "activa"
            """,
            (cliente_dni,)    
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("El cliente ingresado no existe. Reintentar")
        if row[1] > monto_solicitado:
            raise ValueError("Tu limite actual supera ese monto! Reintentar")
        hoy = str(datetime.now())
        cursor.execute(
            """
            INSERT INTO solicitudes_aumento(id_tarjeta, nuevo_limite,
              estado,fecha_solicitud) VALUES (?,?,?,?)
            """,(row[2],monto_solicitado,"PENDIENTE_APROBACION",hoy))
        conn.commit()
        return ({
            "tarjeta_nro":row[0],
            "limite_viejo":row[1],
            "limite_nuevo_solicitado": monto_solicitado,
            "estado":"PENDIENTE_APROBACION",
            "fecha": hoy
        })
        
    finally:
        conn.close()

solicitar_aumento_limite_schema = ToolParam({
    "name": "solicitar_aumento_limite",
    "description": "Registra una solicitud de aumento de límite de crédito para la tarjeta activa de un cliente, dejándola en estado PENDIENTE_APROBACION (no la aprueba ni la rechaza automáticamente). El monto solicitado debe ser estrictamente mayor al límite actual de la tarjeta; si no lo es, la herramienta devuelve un error indicando que el límite actual ya supera ese monto. Usar esta herramienta cuando el usuario pida explícitamente aumentar su límite de tarjeta o solicitar más crédito disponible. Si no se conoce el límite actual del cliente, conviene consultarlo primero con get_limite_tarjeta. Si el cliente no existe o no tiene tarjeta activa, devuelve un error pidiendo reintentar.",
    "input_schema": {
        "type": "object",
        "properties": {
            "cliente_dni": {
                "type": "string",
                "description": "Número de DNI del cliente, sin puntos ni espacios. Por ejemplo: '30123456' o '45987123'. Debe obtenerse del contexto de la conversación o de la sesión autenticada del usuario, nunca debe inventarse."
            },
            "monto_solicitado": {
                "type": "number",
                "description": "Nuevo límite de crédito solicitado por el cliente. Debe ser estrictamente mayor al límite actual de la tarjeta (no se aceptan montos iguales o menores). Por ejemplo: 150000.50."
            }
        },
        "required": ["cliente_dni", "monto_solicitado"]
    }
})

# TODO: definir TOOLS (formato Anthropic tool use) y el dispatcher ejecutar_tool()
TOOLS = []
