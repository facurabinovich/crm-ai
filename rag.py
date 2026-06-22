"""
rag.py

Indexado y busqueda semantica sobre los documentos de docs/ usando:
- VoyageAI para generar embeddings (voyage-3-large)
- ChromaDB (PersistentClient) como vector store, guardado en chroma_db/

Uso tipico:
    from rag import indexar_documento, buscar
    from chunking import chunk_by_section

    with open("docs/banco_macro.md", encoding="utf-8") as f:
        texto = f.read()
    chunks = chunk_by_section(texto)
    indexar_documento(chunks)          # se corre una sola vez (o cuando cambie el doc)

    resultados = buscar("¿Qué incluye el paquete Macro Selecta?")
"""

import chromadb
import voyageai

import time
from dotenv import load_dotenv
from anthropic.types import ToolParam

load_dotenv()
VOYAGE_MODEL = "voyage-3-large"
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "banco_macro"
BATCH_SIZE = 5          # cantidad de chunks por llamada a VoyageAI
PAUSA_ENTRE_BATCHES = 20  # segundos, para no superar 3 RPM / 10K TPM del free tier

voyage_client = voyageai.Client()
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)


def generate_embedding(chunks, model=VOYAGE_MODEL, input_type="query"):
    is_list = isinstance(chunks, list)
    input = chunks if is_list else [chunks]
    result = voyage_client.embed(input, model=model, input_type=input_type)
    return result.embeddings if is_list else result.embeddings[0]


def _get_collection():
    return chroma_client.get_or_create_collection(name=COLLECTION_NAME)


def indexar_documento(chunks: list[str]) -> None:
    """
    Genera embeddings para todos los chunks (input_type="document") y los
    carga en la coleccion de ChromaDB. Pisa la coleccion si ya existia,
    para evitar duplicados si se corre mas de una vez.

    Procesa en batches chicos con pausa entre cada uno, para respetar
    los limites de rate del free tier de VoyageAI (3 RPM / 10K TPM).
    """
    try:
        chroma_client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    collection = _get_collection()

    total = len(chunks)
    for inicio in range(0, total, BATCH_SIZE):
        fin = min(inicio + BATCH_SIZE, total)
        batch_chunks = chunks[inicio:fin]
        batch_ids = [f"chunk_{i}" for i in range(inicio, fin)]

        batch_embeddings = generate_embedding(batch_chunks, input_type="document")

        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_chunks,
        )

        print(f"  Indexados chunks {inicio}-{fin - 1} de {total}")

        # pausamos entre batches, salvo en el ultimo
        if fin < total:
            time.sleep(PAUSA_ENTRE_BATCHES)

    print(f"Indexados {total} chunks en la coleccion '{COLLECTION_NAME}'.")


def buscar(pregunta: str, n_resultados: int = 2) -> list[str]:
    """
    Genera el embedding de la pregunta (input_type="query") y devuelve
    los n_resultados chunks mas similares de la coleccion.
    """
    collection = _get_collection()

    embedding_pregunta = generate_embedding(pregunta, input_type="query")

    resultados = collection.query(
        query_embeddings=[embedding_pregunta],
        n_results=n_resultados,
    )

    # resultados["documents"] es una lista de listas (una por cada query embedding)
    return resultados["documents"][0]


def buscar_info_bancaria(query: str) -> dict:
    """
    Wrapper de buscar() pensado para usarse como tool de Claude.
    Devuelve los 2 chunks mas relevantes, etiquetados, para que Claude
    redacte la respuesta final a partir de ellos.
    """
    chunks_encontrados = buscar(query, n_resultados=2)

    resultado = {}
    for i, chunk in enumerate(chunks_encontrados, start=1):
        resultado[f"resultado_{i}"] = chunk

    return resultado

buscar_info_bancaria_schema = ToolParam({
    "name": "buscar_info_bancaria",
    "description": "Busca información general del banco (políticas, condiciones, requisitos, definiciones, preguntas frecuentes) en una base de conocimiento, y devuelve los fragmentos de texto más relevantes para responder. Usar esta herramienta cuando el usuario pregunte algo conceptual o informativo sobre el banco o sus productos (por ejemplo: '¿qué requisitos tengo que cumplir para pedir un aumento de límite?', '¿cómo funciona el pago mínimo?', '¿qué pasa si no pago a tiempo?'). NO usar esta herramienta para consultar datos específicos de la cuenta de un cliente (saldo, límite, fechas, pagos) — para eso existen herramientas dedicadas como get_saldo, get_fechas y get_limite_tarjeta. Los resultados son fragmentos de texto que deben usarse como base para redactar la respuesta, no copiarse textualmente.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Pregunta o consulta en lenguaje natural sobre información general del banco, reformulada de forma clara y autocontenida a partir de lo que pidió el usuario. Por ejemplo: '¿cuáles son los requisitos para solicitar un aumento de límite?' o '¿qué pasa si no pago el resumen a tiempo?'."
            }
        },
        "required": ["query"]
    }
})