"""
Frontend web simple (Flask) para demo del asistente bancario.

Uso:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python app.py

Abre http://localhost:5000
"""
import json

from flask import Flask, Response, render_template, request, jsonify, stream_with_context

from main import (
    add_user_message,
    add_assistant_message,
    chat_stream,
    run_tools,
    TOOL_SCHEMAS,
)

app = Flask(__name__)

SYSTEM_PROMPT = (
    "Sos un asistente bancario. Antes de decir que no tenés información sobre "
    "un producto, servicio, política o condición del banco, usá siempre la "
    "herramienta buscar_info_bancaria para verificar en la base de conocimiento."
)

# Demo de un solo usuario: el historial de la conversacion vive en memoria del proceso.
conversation = []


@app.route("/")
def index():
    return render_template("index.html")


def _sse(payload):
    return f"data: {json.dumps(payload)}\n\n"


def _stream_chat_response(user_input):
    add_user_message(conversation, user_input)

    try:
        with chat_stream(conversation, system=SYSTEM_PROMPT, tools=TOOL_SCHEMAS) as stream:
            for text in stream.text_stream:
                yield _sse({"token": text})
            response = stream.get_final_message()

        # Si Claude pidio usar una tool, este mensaje incluye el bloque tool_use
        # (puede venir con o sin texto previo, que ya se streameo arriba)
        add_assistant_message(conversation, response)

        if response.stop_reason == "tool_use":
            tool_results = run_tools(response)
            add_user_message(conversation, tool_results)

            # Segundo roundtrip: Claude redacta la respuesta final con el resultado
            # de la tool. Se streamea al mismo bubble que el primer tramo de texto.
            with chat_stream(conversation, system=SYSTEM_PROMPT, tools=TOOL_SCHEMAS) as stream:
                for text in stream.text_stream:
                    yield _sse({"token": text})
                final_response = stream.get_final_message()

            add_assistant_message(conversation, final_response)
    except Exception as e:
        yield _sse({"error": str(e)})

    yield _sse({"done": True})


@app.route("/api/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Mensaje vacio"}), 400

    return Response(
        stream_with_context(_stream_chat_response(user_input)),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/reset", methods=["POST"])
def reset():
    conversation.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=False, port=5000)
