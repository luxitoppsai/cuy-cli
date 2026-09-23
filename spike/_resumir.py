"""Resume la respuesta de Databricks en dos o tres líneas legibles.

Existe para que ``01-conexion.sh`` no escupa JSON crudo: lo que interesa de cada
llamada es si hubo texto, si hubo uso de herramienta y qué dicen los contadores de
cache, no la respuesta entera.

Uso: ``python3 _resumir.py '<json>'``
"""

import json
import sys

CLAVES_CACHE = ("cache_creation_input_tokens", "cache_read_input_tokens")


def main() -> int:
    crudo = sys.argv[1] if len(sys.argv) > 1 else ""
    if not crudo.strip():
        print("    (respuesta vacía)")
        return 0

    try:
        datos = json.loads(crudo)
    except json.JSONDecodeError:
        # Un error de red o un HTML de proxy corporativo caen acá.
        print(f"    no es JSON: {crudo.strip()[:300]}")
        return 0

    if isinstance(datos, dict) and (datos.get("error") or datos.get("error_code")):
        detalle = datos.get("error") or datos.get("message") or datos
        print(f"    ERROR: {str(detalle)[:400]}")
        return 0

    # Formato Anthropic: content es una lista de bloques tipados.
    bloques = datos.get("content")
    if isinstance(bloques, list):
        for bloque in bloques:
            tipo = bloque.get("type")
            if tipo == "text":
                print(f"    texto: {bloque.get('text', '').strip()[:200]}")
            elif tipo == "tool_use":
                print(f"    TOOL_USE: {bloque.get('name')} {json.dumps(bloque.get('input', {}), ensure_ascii=False)}")
            elif tipo == "thinking":
                print("    (bloque de thinking)")
        print(f"    stop_reason: {datos.get('stop_reason')}")

    # Formato OpenAI-compatible.
    elif isinstance(datos.get("choices"), list):
        for opcion in datos["choices"]:
            mensaje = opcion.get("message", {})
            if mensaje.get("content"):
                print(f"    texto: {str(mensaje['content']).strip()[:200]}")
            for llamada in mensaje.get("tool_calls") or []:
                print(f"    TOOL_CALL: {llamada.get('function', {}).get('name')}")
        print(f"    finish_reason: {datos['choices'][0].get('finish_reason') if datos['choices'] else None}")

    else:
        print(f"    forma inesperada: {json.dumps(datos, ensure_ascii=False)[:300]}")

    uso = datos.get("usage") or {}
    if uso:
        partes = [f"in={uso.get('input_tokens') or uso.get('prompt_tokens')}",
                  f"out={uso.get('output_tokens') or uso.get('completion_tokens')}"]
        cache = {k: uso[k] for k in CLAVES_CACHE if k in uso}
        if cache:
            partes += [f"{k.replace('_input_tokens', '')}={v}" for k, v in cache.items()]
        else:
            partes.append("sin contadores de cache")
        print(f"    uso: {' '.join(partes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
