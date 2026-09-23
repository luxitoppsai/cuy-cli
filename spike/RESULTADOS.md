# Fase 0 — Resultados

Fecha: 2026-09-23. Workspace: `dbc-xxxxxxxx-xxxx.cloud.databricks.com`.

## Resumen

| # | Pregunta | Resultado |
|---|---|---|
| 0 | ¿El token autentica? | **Sí.** Los fallos fueron 404, no 401 |
| 1 | ¿API nativa de Anthropic Messages? | **No.** 404: no hay endpoint `anthropic` |
| 2 | ¿Hay modelos Claude servidos? | **No.** Ninguno de los 11 endpoints es Claude |
| 3 | ¿Superficie OpenAI-compatible? | **Sí**, funciona |
| 4 | ¿Tool calling? | **Sí**, en los tres modelos grandes probados |
| 5 | ¿Prompt caching? | **No verificable**: sin contadores de cache en las respuestas |

## El hallazgo que cambia el RFC

Los modelos Claude que aparecen en el catálogo `system.ai` **no están desplegados como
serving endpoints** en este workspace. Estar listado en Unity Catalog y estar servido son
cosas distintas: lo primero es el catálogo de lo que Databricks ofrece, lo segundo es lo
que este workspace tiene levantado.

`GET /api/2.0/serving-endpoints` devuelve 11 endpoints, todos `READY`, ninguno Claude:

| Endpoint | Tarea |
|---|---|
| `databricks-gpt-oss-120b` | llm/v1/chat |
| `databricks-gpt-oss-20b` | llm/v1/chat |
| `databricks-qwen3-next-80b-a3b-instruct` | llm/v1/chat |
| `databricks-qwen35-122b-a10b` | llm/v1/chat |
| `databricks-llama-4-maverick` | llm/v1/chat |
| `databricks-meta-llama-3-3-70b-instruct` | llm/v1/chat |
| `databricks-meta-llama-3-1-8b-instruct` | llm/v1/chat |
| `databricks-gemma-3-12b` | llm/v1/chat |
| `databricks-gte-large-en` | llm/v1/embeddings |
| `databricks-bge-large-en` | llm/v1/embeddings |
| `databricks-qwen3-embedding-0-6b` | llm/v1/embeddings |

Son **modelos de pesos abiertos**, no frontera. Es exactamente la categoría sobre la que
advertía §2.4 del RFC: modelos no post-entrenados para uso agéntico tienden a derivar de
las instrucciones y a caer en loops de herramientas.

## Tool calling: funciona

Probado con una herramienta `leer_archivo` sobre la superficie OpenAI-compatible:

| Modelo | Resultado | Tokens (in/out) |
|---|---|---|
| `databricks-gpt-oss-120b` | `TOOL_CALL: leer_archivo`, `finish_reason: tool_calls`, con bloque de razonamiento | 166 / 54 |
| `databricks-qwen35-122b-a10b` | igual, razonamiento en español | 302 / 59 |
| `databricks-llama-4-maverick` | igual, sin razonamiento explícito | 437 / 11 |

Los tres eligieron la herramienta correcta al primer intento. **Una llamada suelta no
prueba uso agéntico**: lo que falla en estos modelos suele aparecer en sesiones largas
(deriva, loops), no en el primer turno.

## Prompt caching

Ninguna respuesta trae `cache_creation_input_tokens` ni `cache_read_input_tokens`. El
prompt caching de Databricks está documentado **para modelos Claude**; sobre modelos de
pesos abiertos no hay evidencia de que exista. El criterio de aceptación que lo pedía hay
que revisarlo.


## Hallazgo 1: el "cuelgue" era backoff de reintentos

**Corrección de una conclusión previa.** Se escribió acá que el agente colgaba por el
formato de respuesta. Era falso. El log de OpenCode
(`~/.local/share/opencode/log/opencode.log`) muestra la causa real: ante un `Bad Request`
reintenta con **backoff exponencial** — 3s, 6s, 10s, 19s, 36s… Por eso *parecía* pensar
durante 25 minutos cuando en realidad esperaba entre reintentos de una request inválida.

La lección es de método: **el síntoma (lentitud) no se parecía a la causa (request
inválida)**. Se perdió tiempo midiendo latencia de Databricks (1,4 s), probando streaming
(funciona) y sospechando de cuotas de Community. El log del harness lo decía desde el
principio y fue lo último que se miró.

## Hallazgo 2: dos errores de configuración que no se anuncian

1. **Límite de tokens por modelo, no global.** OpenCode pide 32000 de salida; los
   endpoints tienen topes distintos: `gpt-oss-120b` acepta 25000, `llama-4-maverick`
   solo **8192**. El error no dice qué modelo ni de dónde sale el número. Se resuelve con
   `limit: {context, output}` por modelo — **configuración, no fork**.
2. **`small_model` apunta a un modelo inexistente.** OpenCode usa un modelo "pequeño"
   para tareas auxiliares (títulos de sesión) y por defecto elige
   `databricks-gemini-3-flash`, que no existe en este workspace → `Not Found` en cada
   sesión. Se arregla declarando `small_model` en la config. **Nadie lo documenta**: solo
   aparece en el log.

## Hallazgo 3: "OpenAI-compatible" no es uniforme

La especificación de OpenAI define `choices[].message.content` como **string**. Algunos
endpoints de Databricks devuelven una **lista de bloques tipados**:

```json
"content": [
  {"type": "reasoning", "summary": [{"type": "summary_text", "text": "..."}]},
  {"type": "text", "text": "ok"}
]
```

| Modelo | `content` |
|---|---|
| `databricks-gpt-oss-120b` | lista (`reasoning`,`text`) |
| `databricks-gpt-oss-20b` | lista (`reasoning`,`text`) |
| `databricks-qwen35-122b-a10b` | lista (`reasoning`,`text`) |
| `databricks-qwen3-next-80b-a3b-instruct` | string |
| `databricks-llama-4-maverick` | string |
| `databricks-meta-llama-3-3-70b-instruct` | string |
| `databricks-gemma-3-12b` | string |

El corte es por **modelo con razonamiento**, no por familia. **Aún no está probado** que
esto rompa a OpenCode: era la hipótesis del cuelgue y resultó ser otra cosa. Queda como
riesgo a verificar, no como hecho.

Importa igual para el trabajo: los Claude de Databricks con *extended thinking* podrían
devolver una forma análoga.

## Lo que Databricks sí hace bien

Descartado como fuente de problemas, todo verificado:

| | |
|---|---|
| Latencia | **1,4 s** en una llamada simple |
| Streaming | **Funciona**, SSE con chunks correctos |
| Tool calling | **Funciona** en los tres modelos probados |
| Autenticación | Bearer token, sin fricción |

## Reproducir

```bash
bash spike/01-conexion.sh [endpoint]          # las 4 pruebas contra un endpoint
```

## Pendiente

1. **Preguntar al admin de Databricks si se puede habilitar Claude** (pay-per-token o
   provisioned throughput) en este workspace. Es la pregunta que más cambia el proyecto.
2. Probar sesión larga (>30 turnos) con `gpt-oss-120b` y `qwen35-122b` para ver si
   derivan o entran en loops.
3. Medir costo por token de los endpoints disponibles.
