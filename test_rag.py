"""
test_rag.py

Script de prueba manual: indexa el documento del Banco Macro y corre
un par de busquedas para verificar que el RAG funciona de punta a punta.

Uso:
    python test_rag.py
"""

import time
from chunking import chunk_by_section
from rag import indexar_documento, buscar


def main():
    # 1. Leer y chunkear el documento
    with open("docs/banco_macro.md", encoding="utf-8") as f:
        texto = f.read()

    chunks = chunk_by_section(texto)
    print(f"Documento dividido en {len(chunks)} chunks.\n")

    # 2. Indexar (genera embeddings con VoyageAI y carga en ChromaDB)
    print("Indexando...")
    indexar_documento(chunks)
    print()
    print("Esperando 20s para no chocar con el rate limit de VoyageAI...")
    time.sleep(20)

    # 3. Probar algunas busquedas
    preguntas = [
        "¿Qué incluye el paquete Macro Selecta?",
        "¿Cuál es la tasa de interés de la tarjeta Visa Oro?",
        "¿Qué pasa si pierdo mi tarjeta de crédito?",
        "¿Cómo se calcula el pago mínimo de la tarjeta?",
    ]

    for i, pregunta in enumerate(preguntas):
        print("=" * 70)
        print(f"PREGUNTA: {pregunta}")
        print("=" * 70)
        resultados = buscar(pregunta, n_resultados=2)
        for j, chunk in enumerate(resultados):
            print(f"\n--- resultado {j + 1} ---")
            print(chunk[:300])
            print("..." if len(chunk) > 300 else "")
        print()

        if i < len(preguntas) - 1:
            time.sleep(5)  # pausa entre preguntas para no chocar rate limit


if __name__ == "__main__":
    main()