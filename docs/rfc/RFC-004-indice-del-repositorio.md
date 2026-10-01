---
rfc: RFC-004
titulo: Índice local del repositorio con CodeGraph
estado: aceptado
fecha: 2026-09-30
constitucion: 1.0.1
---

# RFC-004 — Índice local del repositorio

El usuario aceptó integrar CodeGraph el 2026-09-30: crear el índice al abrir Cuy,
comprobar su vigencia al volver a abrirlo y excluir el estado generado de Git.
Este documento concreta ese alcance antes de implementar.

## Problema y alcance

La conversación libre necesita localizar símbolos y relaciones entre archivos sin
repetir investigaciones completas. OpenCode ya admite MCP; Cuy añadirá un servidor
local con consultas de lectura a CodeGraph. No requiere comandos de inicio.

Se integra el arranque interactivo y `cuy run` local. Los subcomandos de diagnóstico,
presentación y las tareas aisladas conservan su ejecución actual: no deben descargar
dependencias ni modificar el proyecto para hacer una comprobación.

## Diseño y alternativas

Se fija CodeGraph 0.20.1, binario nativo descargado una vez con SHA-256 fijado en el
repositorio. El modo `--graph-only` evita modelos de embeddings y sus descargas.
No se instala el envoltorio npm, sus hooks ni su telemetría.

Un adaptador Python de biblioteca estándar publica una selección de herramientas de
lectura mediante MCP y ejecuta consultas nativas de una sola ejecución. Una copia
local conserva los archivos admitidos por Git, sin enlaces simbólicos, metadatos Git,
archivos ocultos, dependencias, archivos con bytes nulos ni archivos mayores de 1 MiB.
La copia se limita a 5000 archivos y 64 MiB de texto. Fuera de Git,
se recorren los archivos con las mismas exclusiones convencionales.

La copia y el estado viven en `.cuy/codegraph/`, dentro de cada repositorio/worktree.
Las rutas de resultados se traducen al proyecto original. Antes de cada consulta se
revisan los hashes: cambios y altas reutilizan el índice nativo; borrados o cambios
de raíz/versión invalidan la caché para evitar símbolos huérfanos.

Alternativas: MCP nativo directo (más simple, pero su watcher no aplica todas las
exclusiones y el barrido incremental no elimina todos los borrados); Graphify (útil
para documentación y visualización, fuera de este primer alcance); índice propio
(duplicaría analizadores existentes). El adaptador existe para resolver esos límites,
no para añadir orquestación de agentes.

## Requisitos

| ID | Requisito |
|---|---|
| RF-001 | Preparar el índice antes de abrir una conversación local, sin comandos especiales. |
| RF-002 | Reutilizar archivos intactos, actualizar cambios y eliminar símbolos de borrados. |
| RF-003 | Mantener estado separado por repositorio/worktree y traducir las rutas. |
| RF-004 | Añadir exclusiones de estado a `.gitignore` conservando contenido y sin duplicarlas. |
| RF-005 | Ofrecer solo consultas de lectura y no entregar credenciales al proceso nativo. |
| RF-006 | Descargar una versión fija con checksum; ante fallos, avisar y abrir Cuy sin índice. |

## Criterios de aceptación

| ID | Evidencia requerida |
|---|---|
| CA-001 | Arranque crea el índice; la segunda preparación no reescribe fuentes intactas. |
| CA-002 | Cambios, altas y borrados modifican correctamente la copia y la caché. |
| CA-003 | Archivos ignorados, enlaces y secretos convencionales quedan fuera de la copia. |
| CA-004 | MCP expone solo la lista permitida; rechaza herramientas administrativas. |
| CA-005 | Descargar un checksum incorrecto no sustituye un ejecutable existente. |
| CA-006 | Prueba con CodeGraph real demuestra búsqueda, cambio, borrado y rutas originales. |

## Límites

El grafo es análisis estático, no garantiza resolución de llamadas dinámicas ni cobertura
total. CodeGraph excluye también `vendor`, `fixtures`, `examples` y otras carpetas
convencionales; la lectura normal sigue disponible. No se prometen mejoras de tiempo,
tokens o calidad sin una evaluación con modelos reales.

Las exclusiones y la redacción son barreras locales, no un aislamiento de seguridad.
Los fuentes permitidos pueden contener secretos no reconocidos; los resultados de
consultas entran al contexto del modelo configurado. `.gitignore` no quita archivos
ya versionados; Cuy omite además nombres convencionales de credenciales.

La primera descarga necesita acceso al repositorio público de CodeGraph. Windows ARM64
no tiene binario nativo publicado para esta versión: se avisa y se continúa sin índice.

Fuente del contrato: [CodeGraph](https://github.com/codegraph-ai/CodeGraph), release
[v0.20.1](https://github.com/codegraph-ai/CodeGraph/releases/tag/v0.20.1).
