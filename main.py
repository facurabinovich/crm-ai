"""
Asistente bancario con tool calling + RAG sobre Anthropic SDK.

Uso:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python main.py
"""
# Load env variables and create client
import sys
sys.stdin.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from anthropic import Anthropic
from anthropic.types import Message
from tools import (
    get_saldo, get_fechas, pagar_saldo,
    get_limite_tarjeta, solicitar_aumento_limite,
)
from tools import (
    get_saldo_schema, get_fechas_schema, pagar_saldo_schema,
    get_limite_tarjeta_schema, solicitar_aumento_limite_schema,
)
from rag import buscar_info_bancaria, buscar_info_bancaria_schema
import json 
load_dotenv()

client = Anthropic()
model = "claude-haiku-4-5"

TOOL_SCHEMAS = [get_saldo_schema,get_fechas_schema,pagar_saldo_schema,get_limite_tarjeta_schema,
                solicitar_aumento_limite_schema, buscar_info_bancaria_schema]

TOOL_FUNCTIONS = {
    "get_saldo": get_saldo,
    "get_fechas": get_fechas,
    "pagar_saldo": pagar_saldo,
    "get_limite_tarjeta": get_limite_tarjeta,
    "solicitar_aumento_limite": solicitar_aumento_limite,
    "buscar_info_bancaria": buscar_info_bancaria
}

# ---------- Helper functions ----------
 
def add_user_message(messages, message):
    if isinstance(message, list):
        user_message = {
            "role": "user",
            "content": message,
        }
    else:
        user_message = {
            "role": "user",
            "content": [{"type": "text", "text": message}],
        }
    messages.append(user_message)
 
 
def add_assistant_message(messages, message):
    if isinstance(message, list):
        assistant_message = {
            "role": "assistant",
            "content": message,
        }
    elif hasattr(message, "content"):
        content_list = []
        for block in message.content:
            if block.type == "text":
                content_list.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content_list.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
        assistant_message = {
            "role": "assistant",
            "content": content_list,
        }
    else:
        assistant_message = {
            "role": "assistant",
            "content": [{"type": "text", "text": message}],
        }
    messages.append(assistant_message)
 
 
# Wrapper sobre client.messages.stream(). Construye el dict de parámetros dinámicamente
# Devuelve el stream para iterar token a token. Llama a API de Anthropic y devuelve un stream de tokens. 
# Al final, se puede llamar a get_final_message() para obtener el mensaje completo.
def chat_stream(
    messages,
    system=None,
    temperature=0,
    tools=None,
    tool_choice=None,
):
    params = {
        "model": model,
        "max_tokens": 4000,
        "messages": messages,
        "temperature": temperature,
    }
 
    if tool_choice:
        params["tool_choice"] = tool_choice
 
    if tools:
        params["tools"] = tools
 
    if system:
        params["system"] = system
 
    return client.messages.stream(**params)
 
 
def text_from_message(message):
    return "\n".join(
        [block.text for block in message.content if block.type == "text"]
    )
 
 
# ---------- Tool running ----------
 
def run_tool(tool_name, tool_input):
    return TOOL_FUNCTIONS[tool_name](**tool_input)
 
 
def run_tools(message):
    tool_requests = [block for block in message.content if block.type == "tool_use"]
    tool_result_blocks = []
 
    for tool_request in tool_requests:
        try:
            tool_output = run_tool(tool_request.name, tool_request.input)
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": json.dumps(tool_output),
                "is_error": False,
            }
        except Exception as e:
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": f"Error: {e}",
                "is_error": True,
            }
 
        tool_result_blocks.append(tool_result_block)
 
    return tool_result_blocks
 
 
# ---------- Loop principal ----------
def main():
    messages = []
    system_prompt = (
        "Sos un asistente bancario del Banco Macro. Antes de decir que no tenés información sobre "
        "un producto, servicio, política o condición del banco, usá siempre la "
        "herramienta buscar_info_bancaria para verificar en la base de conocimiento."
    )

    print("Asistente bancario listo. Escribi 'salir' para terminar.\n")

    while True:
        user_input = input("Vos: ")
        if user_input.lower() in ["salir", "exit"]:
            break

        add_user_message(messages, user_input)

        # --- Primer roundtrip ---
        # Streameamos el texto que Claude manda antes de decidir si usa una tool
        print("Claude: ", end="", flush=True) # end="" para que no haga salto de linea y flush=True 
        #para que se vea en tiempo real
        with chat_stream(messages, system=system_prompt, tools=TOOL_SCHEMAS) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            print()  # salto de linea al terminar el stream
            response = stream.get_final_message()  # necesitamos el mensaje completo para chequear stop_reason

        if response.stop_reason == "tool_use": # esta afuera del with porque necesitamos el mensaje 
            # completo para chequear stop_reason
            # Paso 1: guardar la respuesta de Claude (con el tool_use) en messages
            add_assistant_message(messages, response)

            # Paso 2: ejecutar la(s) tool(s) que Claude pidio
            tool_results = run_tools(response)

            # Paso 3: guardar el resultado de la(s) tool(s) en messages
            add_user_message(messages, tool_results)

            # --- Segundo roundtrip ---
            # Claude ya sabe el resultado de la tool, ahora redacta la respuesta final
            # La streameamos tambien para que el usuario la vea token por token
            with chat_stream(messages, system=system_prompt, tools=TOOL_SCHEMAS) as stream:
                for text in stream.text_stream:
                    print(text, end="", flush=True)
                print()  # salto de linea al terminar
                final_response = stream.get_final_message()

            # Ultimo paso: guardar la respuesta final en el historial
            add_assistant_message(messages, final_response)

        else:
            # Caso simple: Claude respondio directo, sin tool
            # Ya se imprimio todo durante el stream, solo guardamos en el historial
            add_assistant_message(messages, response)


if __name__ == "__main__":
    main() 

 
