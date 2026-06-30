# CRM AI - Asistente bancario

Asistente conversacional para un CRM bancario que combina **tool calling**
y **RAG** sobre el SDK de Anthropic (Claude). Incluye una version de consola
y un frontend web simple (Flask) para demo.

## Demo

**Tool calling** — consulta de saldo, pagos y límite de tarjeta:

![Tool calling demo](gifs/tool-calling%20example.gif)

**RAG** — búsqueda semántica sobre la base de conocimiento del banco:

![RAG demo](gifs/rag%20example.gif)

## Estructura

- `main.py` — loop de chat por consola, orquesta tool calling y RAG.
- `app.py` — frontend web (Flask) que reutiliza la logica de `main.py` con streaming SSE.
- `tools.py` — definicion y ejecucion de las tools del banco.
- `rag.py` — indexado y busqueda semantica sobre `docs/` con ChromaDB y Voyage AI.
- `chunking.py` — division de los documentos en chunks para indexar.
- `setup_db.py` — creacion e inicializacion de `crm.db` (datos del CRM).
- `docs/` — base de conocimiento (politicas, FAQ) usada por el RAG.
- `templates/` — vistas HTML del frontend Flask.

## Tools disponibles

- `get_saldo()` — saldo actual de la tarjeta.
- `pagar_saldo(monto)` — aplica un pago al saldo.
- `get_fechas()` — fecha de cierre y vencimiento del resumen.
- `get_limite_tarjeta()` — limite y disponible de la tarjeta.
- `solicitar_aumento_limite(monto_solicitado)` — registra una solicitud de aumento.
- `buscar_info_bancaria(query)` — busqueda semantica (RAG) sobre la base de conocimiento.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Crear un archivo `.env` con las API keys necesarias:

```
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
```

Crear la base de datos del CRM (una sola vez):

```bash
python setup_db.py
```

Indexar la base de conocimiento para el RAG (una sola vez, o cuando cambien los docs):

```bash
python -c "
from rag import indexar_documento
from chunking import chunk_by_section

with open('docs/banco_macro.md', encoding='utf-8') as f:
    texto = f.read()
indexar_documento(chunk_by_section(texto))
"
```

## Uso

Version consola:

```bash
python main.py
```

Version web (http://localhost:5000):

```bash
python app.py
```

## Arquitectura 
El proyecto se contextualizó como un Workflow tipo menu(como suelen hacer la mayoria de los bancos).
Este era el diagrama original(ejemplo tool get_saldo())

![alt text](<Diagrama Ejemplo Tool Calling.png>)

Sin embargo, organicamente el sistema se transformó en un agente autonomo capaz de decidir por su cuenta que tools usar y cuando. La clave de esto esta en especificar las tools en JSON SCHEMAS claros y directos para que Claude sepa exactamente cuando usarlas y cuando no. Por lo tanto, en este crm-ai uno puede hablar directamente con Claude lo que da una sensacion más humana y menos robotizada. Al ser una demo sencilla para una entrevista laboral, se eligió esta implementación, aunque para un banco real lo mejor seria implementar el workflow con menu ya que hay mucha responsabilidad financiera y social por lo que habria que limitar a Claude lo más posible

## Decisiones de diseño


**Command + Registry (TOOL_FUNCTIONS + run_tool)**
Cada tool tiene función Python + JSON schema separados. Claude decide, tu código ejecuta. ("El modelo no ejecuta herramientas, el modelo decide qué herramienta usar y mi aplicación la ejecuta.") El patron hace muy facil la incorporacion de nuevas tools ya que no se modifica la función principal, solo se carga el schema y nombre de la tool en TOOL_FUNCTION y run_tool los recupera. Esto es mucho mas mantenible y nos salva de crear varios if/elif con cada tool.

**RAG como Tool (Adapter)**
Por simplificidad, una vez que se eligió el modo agente, se eligió implementar el RAG como si fuera una tool más (buscar_info_bancaria) y se reforzó el system_prompt para que ante la duda use esta tool. El patrón Adapter resuelve un problema de interfaz: buscar() en rag.py devuelve una lista de strings, pero el sistema de tool calling de Claude espera una función con firma simple y que devuelva un diccionario. buscar_info_bancaria() adapta esa interfaz — recibe query: str, llama a buscar(), y empaqueta los resultados en {"resultado_1": ..., "resultado_2": ...} que Claude puede consumir directamente como tool_result.

**Pipeline de chunking**
Se implementó lo siguiente: Se transformó el pdf a formato markdown usando claude(modo conversación). La razón fue que el pdf contenia muchas tablas dificiles de parsear. Luego se implementó el Chunking por secciónes del markdown file. Se usó este separador # inicilamente. Nos dimos cuenta, de que algunas secciones quedaban muy largas y otras muy cortas. En consiguiente, se decidió:
- Secciones de más de 1000 caracteres(Largas): usar el separador ##
- Secciones de menos de 200 caracteres(cortas): Fusionar con vecino proximo (Incluyendo nota explicativa para Claude)

Esto nos dio un total de 61 chunks logicos y coherentes para que Claude consuma. 

**Facade (app.py)**
app.py envuelve toda la orquestación de main.py (mensajes, streaming, tools) detrás de tres
endpoints Flask simples (/, /api/chat, /api/reset), ocultando la complejidad del protocolo de conversación. Esto nos permite que app.py sea totalmente independiente del backend con la logica de crm-ai haciendo todo más mantenible.

**Repository (db.py)**
Se centralizó la conexión de la db en capas reutilizables para gestionar de forma eficiente la db y evitar la duplicación de codigo. El try/finally implementado en cada una de las funciones tools donde nos conectamos a la db nos da la oportunidad del correcto manejo de errores.

Por último, se decidió implementar Streaming via el SDK de Anthropic y el manejo de eventos entre el backend y el frontend para que el chat parezca más humano. Sin streaming, Claude "escupia" toda la respuesta de una desnaturalizando la conversación

## Roadmap
- Citations en RAG: Seria un nice-to-have que permitiria al cliente tener trazabilidad transparente de donde sale la información pedida.
- MCP para conectar tools a sistemas reales: Hoy, no es necesario ya que nos conectamos a una simple base de datos fake, pero la capa MCP nos permitiria tener un sistema más profesional.
- Pagos parciales con planes: Claude solo acepta pagos totales cuando la realidad de un banco es distinta (Se eligió esta alternativa por cuestiones de tiempos)
- Workflow con menú para producción real: Como dije anteriormente, en un sistema bancario por cuestiones de seguridad lo más sensato es ofrecer un workflow con un menu definido para restringir al usuario a que interactue exactamente como el banco quiere.
- Manejo de múltiples clientes (sesiones): Solo hay un usuario en bd (dni=30123456). El manejo de más clientes seria el obvio paso a seguir.

## Notas

- `crm.db` se genera con `setup_db.py` y contiene los datos de ejemplo del CRM.
- `chroma_db/` se genera al indexar `docs/` con `rag.py` y no se versiona (ver `.gitignore`).
