---
tipo: plan
spec: RFC-002
proyecto: cuy-cli
fecha: 2026-09-25
constitucion: 1.0.0
---

# Plan — RFC-002, redacción de secretos

> Spec: [`docs/rfc/RFC-002-redaccion-de-secretos.md`](../../rfc/RFC-002-redaccion-de-secretos.md)
>
> Reconstruido el 2026-09-25 sobre la implementación ya entregada, como ejemplo trabajado de
> la adopción de SDD. El diseño que describe es el que se implementó, no uno propuesto.

## Resumen

Dos mecanismos independientes sobre los hooks de OpenCode: uno rechaza rutas antes de
leerlas, otro redacta patrones en la salida de cualquier herramienta. La lógica testeable
vive fuera del archivo de plugin porque OpenCode invoca cada export como fábrica de plugins.

## Contexto técnico

| | |
|---|---|
| Lenguaje | JavaScript (ESM, Node 20+) para el plugin; Python 3.11+ para las utilidades |
| Dependencias nuevas | ninguna |
| Punto de integración | hooks `tool.execute.before` y `tool.execute.after` de OpenCode |
| Almacenamiento | `~/.local/share/cuy-cli/auditoria.jsonl`, ya existente |
| Pruebas | runner propio en `tests/secretos.test.mjs` |
| Escala | regex sobre texto ya en memoria; una salida de herramienta por llamada |

## Compuerta constitucional

Recorrida antes de implementar. Cada principio dice cómo se cumple o por qué no aplica.

| Principio | Cumplimiento |
|---|---|
| **P1** Verificar, no deducir | Los cinco criterios se cierran ejecutando el plugin con las firmas reales de los hooks, no leyendo el código. |
| **P2** Descubrir, no asumir | No aplica: nada acá depende del workspace. |
| **P3** Camino sin cubrir | El hook se ejerce en test con las firmas reales; no requiere un motor vivo. |
| **P4** API que ignora en silencio | `tests/hooks.test.mjs` valida los nombres de hook contra la interfaz `Hooks` **leída del vendor**. Es el principio que más pesa acá: los dos hooks que usa este plugin son de los que se descartan sin avisar. |
| **P5** Precisión sobre cobertura | Central al diseño. La asignación solo se redacta entrecomillada (RF-006) y CA-003 exige cero falsos positivos sobre este repositorio. |
| **P6** Fallar cerrado | `mensajeDeRechazo` explica el siguiente paso, no solo prohíbe. Un patrón dudoso no se redacta a medias: o se redacta entero o no se toca. |
| **P7** Barrera vs control | Declarado explícitamente en §2 del RFC y repetido en el README: es barrera. El control duro vive en el Gateway. |
| **P8** El secreto no toca el disco | Los fixtures se construyen (`"dapi" + "0123456789abcdef".repeat(2)`); la auditoría registra tipo y cantidad, nunca el valor (RF-008). |
| **P9** KISS / YAGNI | Sin dependencias ni escáner externo. `rutaProhibidaEnComando` parte por palabras y no intenta entender la sintaxis del shell: lo que se le escapa lo agarra la redacción de la salida. |
| **P10** El porqué donde vive el código | Docstrings en `secretos-core.js` y nota en el README sobre qué **no** cubre. |

**Violaciones declaradas:** ninguna.

## Diseño

### Dónde se intercepta

`tool.execute.after` recibe el objeto de salida **antes** de entregárselo al modelo y lo deja
mutar. Verificado en `vendor/opencode/packages/opencode/src/session/tools.ts`: OpenCode
devuelve el mismo objeto que el hook modificó.

```
herramienta → resultado → [tool.execute.after] → modelo
                               ↑ acá se redacta
```

`tool.execute.before` puede lanzar, y lanzar aborta la llamada. Es el único punto donde el
contenido todavía no se leyó.

### Módulos

| Archivo | Responsabilidad |
|---|---|
| `plugin/secretos.js` | Solo los hooks. **Un único export**, porque OpenCode invoca cada export como fábrica de plugins. |
| `plugin/lib/secretos-core.js` | Detección y redacción. Es lo que se prueba. |

### Decisiones de diseño

**Rechazar rutas en vez de redactarlas.** Un `.env` redactado es un archivo de marcadores:
no le sirve al modelo y le hace creer que lo leyó. El error dice la verdad.

**La asignación exige comillas.** Sin esa restricción el patrón se dispara contra
`token = response.token`, que en un agente de código aparece todo el tiempo. Es el precio
de P5: se pierde el secreto sin comillas, se gana no envenenar el contexto.

**Las plantillas se excluyen antes que nada.** `PLANTILLAS` se evalúa primero en
`rutaProhibida`, porque `.env.example` coincide con el patrón de `.env` y existe justamente
para versionarse.

### Efecto de segundo orden

Si el agente intenta reescribir una línea redactada, su `oldString` no coincide con el
archivo real y la edición falla. La redacción **no puede** pisar un secreto con
`[REDACTADO]` en disco. Falla cerrado sin haberlo programado.

## Estructura

```
plugin/
  secretos.js                 hooks, un solo export
  lib/secretos-core.js        detección, redacción, rutas
tests/
  secretos.test.mjs           casos positivos y negativos por patrón
  hooks.test.mjs              los nombres de hook existen en el vendor
docs/specs/002-redaccion-de-secretos/
  plan.md  tareas.md  trazabilidad.md
```

## Riesgos

Los del RFC §7, sin cambios. El de mayor probabilidad sigue siendo el falso positivo, y
CA-003 es el que lo vigila: se rompe en cuanto un patrón nuevo toque este repositorio.
