---
tipo: trazabilidad
spec: RFC-002
proyecto: cuy-cli
fecha: 2026-09-25
---

# Trazabilidad — RFC-002, redacción de secretos

> Spec: [`../../rfc/RFC-002-redaccion-de-secretos.md`](../../rfc/RFC-002-redaccion-de-secretos.md)
>
> `tests/test_trazabilidad.py` verifica que esta tabla esté completa y que los tests que
> nombra existan. Lo que no puede verificar es que el test *pruebe* lo que dice.

## Criterios de aceptación

| Criterio | Test | Archivo |
|---|---|---|
| CA-001 | `CA-001: bash no puede leer un archivo de credenciales` | `tests/secretos.test.mjs` |
| CA-002 | `CA-002: el valor se reemplaza y el resto del archivo queda igual` | `tests/secretos.test.mjs` |
| CA-003 | `el propio repo se lee intacto (criterio 3 del RFC)` | `tests/secretos.test.mjs` |
| CA-004 | `CA-004: la auditoria registra el hallazgo y nunca el valor` | `tests/secretos.test.mjs` |
| CA-005 | `redacta claves de AWS, GitHub, Slack, OpenAI, Anthropic y Google` | `tests/secretos.test.mjs` |

## Requisitos funcionales

| Requisito | Test | Archivo |
|---|---|---|
| RF-001 | `rechaza los archivos cuyo contenido es el secreto` | `tests/secretos.test.mjs` |
| RF-002 | `encuentra la ruta prohibida dentro de un comando` | `tests/secretos.test.mjs` |
| RF-003 | `no rechaza archivos normales que se le parecen` | `tests/secretos.test.mjs` |
| RF-004 | `redacta un bloque de clave privada entero` | `tests/secretos.test.mjs` |
| RF-005 | `conserva la forma del archivo alrededor de lo redactado` | `tests/secretos.test.mjs` |
| RF-006 | `no toca el código normal que menciona esas palabras` | `tests/secretos.test.mjs` |
| RF-007 | `no toca los placeholders de la propia configuración` | `tests/secretos.test.mjs` |
| RF-008 | `CA-004: la auditoria registra el hallazgo y nunca el valor` | `tests/secretos.test.mjs` |
| RF-009 | — sin test automático | ver nota |

## Notas

**RF-009** (no existe variable de entorno que lo desactive) es la ausencia de una
funcionalidad. Un test que compruebe que ninguna variable lo apaga tendría que enumerar
todas las variables imaginables, que no prueba nada. Queda verificado por lectura del
código y por la compuerta constitucional del plan (P7).

**Lo que este ejercicio destapó.** CA-001, CA-002 y CA-004 se habían verificado a mano el
2026-09-24 ejecutando el plugin y mirando la salida. Funcionaba, pero esa comprobación no
quedaba en ningún lado: cualquier cambio posterior podía romperlos sin que nadie se
enterara. Al completar esta tabla aparecieron los tres huecos y se escribieron los tests que
faltaban. Es exactamente para lo que sirve el documento.
