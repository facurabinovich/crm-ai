"""
revisar_chunks.py

Corre chunk_by_section() sobre el documento markdown del Banco Macro
y muestra un resumen para revisar visualmente los resultados.

Uso:
    python revisar_chunks.py docs/banco_macro.md
"""

import sys
from chunking import chunk_by_section, UMBRAL_MAX, UMBRAL_MIN


def main():
    if len(sys.argv) < 2:
        print("Uso: python revisar_chunks.py <ruta_al_archivo.md>")
        sys.exit(1)

    ruta = sys.argv[1]
    with open(ruta, encoding="utf-8") as f:
        texto = f.read()

    chunks = chunk_by_section(texto)

    print(f"Documento original: {len(texto)} caracteres")
    print(f"Total de chunks generados: {len(chunks)}")
    print(f"Umbral max (sub-split): {UMBRAL_MAX} | Umbral min (fusion): {UMBRAL_MIN}")
    print("=" * 70)

    largos = []
    cortos = []

    for i, chunk in enumerate(chunks):
        # primera linea = el header del chunk, util para identificarlo
        primera_linea = chunk.strip().split("\n")[0]
        largo = len(chunk)

        flag = ""
        if largo > UMBRAL_MAX:
            flag = "  <-- SIGUE LARGO (quedo asi por la regla 'no ### de fallback')"
            largos.append(i)
        elif largo < UMBRAL_MIN:
            flag = "  <-- SIGUE CORTO (era el ultimo chunk, no tenia con quien fusionarse)"
            cortos.append(i)

        print(f"[{i:02d}] ({largo:5d} chars) {primera_linea}{flag}")

    print("=" * 70)
    print(f"Chunks que superan {UMBRAL_MAX} chars: {len(largos)} -> indices {largos}")
    print(f"Chunks por debajo de {UMBRAL_MIN} chars: {len(cortos)} -> indices {cortos}")


if __name__ == "__main__":
    main()