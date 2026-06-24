import re

UMBRAL_MAX = 1000   # si un chunk de nivel 1 supera esto, se sub-divide por nivel 2
UMBRAL_MIN = 200    # si un chunk queda por debajo de esto, se fusiona con el siguiente
NOTA_FUSION = (
    "\n\n[Nota: Este chunk se fusiono con su vecino por no superar el "
    "umbral de 200 caracteres. Tener en cuenta antes de responder/citar]\n\n"
)


def split_por_header(texto: str, nivel: str) -> list[str]:
    """
    Divide el texto por headers de markdown del nivel indicado ("# " o "## ").
    Reconstruye el header al inicio de cada chunk (excepto el primero,
    que es el contenido antes del primer header de ese nivel).
    """
    pattern = f"\n{nivel} "
    partes = re.split(pattern, texto)

    chunks = [partes[0]]  # contenido previo al primer header (si existe)
    for parte in partes[1:]:
        chunks.append(f"{nivel} {parte}")
    return chunks


def chunk_by_section(document_text: str) -> list[str]:
    # Paso 1: split por nivel 1 (#)
    chunks_nivel1 = split_por_header(document_text, "#")

    # Paso 2: sub-dividir los que superen el umbral, usando nivel 2 (##)
    chunks_procesados = []
    for chunk in chunks_nivel1:
        if len(chunk) > UMBRAL_MAX:
            sub_chunks = split_por_header(chunk, "##")
            chunks_procesados.extend(sub_chunks)
        else:
            chunks_procesados.append(chunk)

    # Paso 3: fusionar chunks por debajo del umbral minimo con el siguiente
    chunks_finales = []
    i = 0
    while i < len(chunks_procesados):
        chunk_actual = chunks_procesados[i]

        if len(chunk_actual) < UMBRAL_MIN and i + 1 < len(chunks_procesados):
            chunk_siguiente = chunks_procesados[i + 1]
            chunk_fusionado = chunk_actual + NOTA_FUSION + chunk_siguiente
            chunks_finales.append(chunk_fusionado)
            i += 2  # saltamos los dos, ya que se consumieron juntos
        else:
            chunks_finales.append(chunk_actual)
            i += 1

    # filtramos chunks vacios o solo espacios (puede pasar con el chunk[0] inicial)
    chunks_finales = [c for c in chunks_finales if c.strip()]

    return chunks_finales