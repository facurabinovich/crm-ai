#!/bin/bash
set -e

mkdir -p data

if [ ! -f "data/crm.db" ]; then
    echo "Creando base de datos..."
    python setup_db.py
fi

if [ ! -d "data/chroma_db" ] || [ -z "$(ls -A data/chroma_db 2>/dev/null)" ]; then
    echo "Indexando base de conocimiento (puede tardar ~5 min por rate limits de VoyageAI)..."
    python -c "
from rag import indexar_documento
from chunking import chunk_by_section

with open('docs/banco_macro.md', encoding='utf-8') as f:
    texto = f.read()
indexar_documento(chunk_by_section(texto))
print('Indexado completo.')
"
fi

echo "Iniciando servidor en :5000 ..."
exec gunicorn --bind 0.0.0.0:5000 --workers 1 --timeout 120 app:app
