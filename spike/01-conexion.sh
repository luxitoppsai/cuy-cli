#!/usr/bin/env bash
# Fase 0, punto 1: probar Databricks Model Serving sin ninguna capa intermedia.
#
# Responde cuatro preguntas, en orden de importancia para el RFC:
#   1. ¿Responde la API nativa de Anthropic Messages?  (la ventaja del proyecto)
#   2. ¿Hace tool calling real?                        (sin esto no hay agente)
#   3. ¿Funciona el prompt caching?                    (criterio de aceptación)
#   4. ¿Responde también la superficie OpenAI-compatible? (plan B)
#
# No imprime el token nunca. Uso:  bash spike/01-conexion.sh [modelo]

set -uo pipefail

HOST="https://dbc-xxxxxxxx-xxxx.cloud.databricks.com"
MODELO="${1:-databricks-claude-sonnet-4}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- Credencial: .env, variable de entorno, o el CLI de Databricks -------------
if [[ -z "${DATABRICKS_TOKEN:-}" && -f "$RAIZ/.env" ]]; then
  set -a; source "$RAIZ/.env"; set +a
fi
if [[ -z "${DATABRICKS_TOKEN:-}" ]] && command -v databricks >/dev/null 2>&1; then
  DATABRICKS_TOKEN="$(databricks auth token --host "$HOST" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null)"
fi
if [[ -z "${DATABRICKS_TOKEN:-}" ]]; then
  echo "No hay credencial. Poné el token en $RAIZ/.env o corré 'databricks auth login'."
  exit 1
fi

echo "Host:   $HOST"
echo "Modelo: $MODELO"
echo

# `jq` no siempre está; python3 sí, y ya es dependencia del resto del stack.
resumir() { python3 "$RAIZ/spike/_resumir.py" "$1"; }

# Imprime el código HTTP en la primera línea y el cuerpo en el resto. La variable no
# se puede compartir: la función corre en una subshell y su asignación no sube al padre.
llamar() {  # $1=url  $2=cuerpo
  local respuesta
  respuesta="$(curl -sS -w '\n%{http_code}' --max-time 120 \
    -H "Authorization: Bearer $DATABRICKS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$2" "$1" 2>&1)"
  tail -n1 <<<"$respuesta"
  sed '$d' <<<"$respuesta"
}

reportar() {  # $1=salida de `llamar`
  echo "    HTTP $(head -n1 <<<"$1")"
  resumir "$(tail -n +2 <<<"$1")"
}

ANTHROPIC="$HOST/serving-endpoints/anthropic/v1/messages"
OPENAI="$HOST/serving-endpoints/$MODELO/invocations"

# --- 1. API nativa de Anthropic ----------------------------------------------
echo "=== 1. API nativa de Anthropic Messages ==="
echo "    $ANTHROPIC"
CUERPO=$(python3 -c "
import json,sys
print(json.dumps({'model': sys.argv[1], 'max_tokens': 64,
                  'messages': [{'role':'user','content':'Respondé solo: ok'}]}))
" "$MODELO")
reportar "$(llamar "$ANTHROPIC" "$CUERPO")"
echo

# --- 2. Tool calling ----------------------------------------------------------
echo "=== 2. Tool calling (API nativa) ==="
CUERPO=$(python3 -c "
import json,sys
print(json.dumps({
  'model': sys.argv[1], 'max_tokens': 256,
  'tools': [{'name':'leer_archivo',
             'description':'Lee un archivo del disco y devuelve su contenido.',
             'input_schema':{'type':'object',
                             'properties':{'ruta':{'type':'string','description':'Ruta del archivo'}},
                             'required':['ruta']}}],
  'messages': [{'role':'user','content':'Necesito ver qué hay en README.md. Usá la herramienta.'}],
}))
" "$MODELO")
reportar "$(llamar "$ANTHROPIC" "$CUERPO")"
echo

# --- 3. Prompt caching --------------------------------------------------------
# Se corre dos veces: la primera crea el cache, la segunda debería leerlo. Lo que
# importa es `cache_read_input_tokens` > 0 en la segunda.
echo "=== 3. Prompt caching (cache_control) ==="
CUERPO=$(python3 -c "
import json,sys
relleno = ('Convención interna del equipo. ' * 400)  # supera el mínimo para cachear
print(json.dumps({
  'model': sys.argv[1], 'max_tokens': 32,
  'system': [{'type':'text','text': relleno, 'cache_control': {'type':'ephemeral'}}],
  'messages': [{'role':'user','content':'Respondé solo: ok'}],
}))
" "$MODELO")
for intento in 1 2; do
  echo "    intento $intento:"
  reportar "$(llamar "$ANTHROPIC" "$CUERPO")"
done
echo

# --- 4. Superficie OpenAI-compatible (plan B) ---------------------------------
echo "=== 4. OpenAI-compatible ==="
echo "    $OPENAI"
CUERPO='{"messages":[{"role":"user","content":"Respondé solo: ok"}],"max_tokens":64}'
reportar "$(llamar "$OPENAI" "$CUERPO")"
