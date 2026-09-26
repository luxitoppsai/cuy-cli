---
tipo: tareas
spec: RFC-002
proyecto: cuy-cli
fecha: 2026-09-25
---

# Tareas — RFC-002, redacción de secretos

> Plan: [`plan.md`](plan.md) · Spec: [`../../rfc/RFC-002-redaccion-de-secretos.md`](../../rfc/RFC-002-redaccion-de-secretos.md)
>
> Reconstruidas sobre la implementación entregada el 2026-09-24. Todas cerradas.

Formato: `TNNN [P] [RF-NNN] descripción`. `[P]` marca las que pueden ir en paralelo dentro
de su bloque —archivos distintos, sin dependencia entre ellas—.

## Bloque 1 — Base

Nada de lo demás compila sin esto.

- [x] **T001** Crear `plugin/lib/secretos-core.js` con un único punto de entrada por
      mecanismo: `rutaProhibida`, `rutaProhibidaEnComando`, `redactar`.
- [x] **T002** Crear `plugin/secretos.js` con **un solo export**. Sin esto el plugin no
      carga y la configuración queda nula, en cascada y sin mensaje útil.

## Bloque 2 — Rechazo de rutas (RF-001, RF-002, RF-003)

Entregable independiente: sirve aunque el bloque 3 no exista.

- [x] **T003** `[RF-001]` Lista `RUTAS_PROHIBIDAS` y `rutaProhibida()`.
- [x] **T004** `[P]` `[RF-003]` Excepción `PLANTILLAS`, evaluada **antes** que la lista:
      `.env.example` coincide con el patrón de `.env` y debe leerse.
- [x] **T005** `[P]` `[RF-002]` `rutaProhibidaEnComando()`: parte el comando por palabras.
      No entiende sintaxis de shell a propósito (P9).
- [x] **T006** `[RF-001]` `mensajeDeRechazo()`: dice qué hacer, no solo que no se puede (P6).
- [x] **T007** Enganchar en `tool.execute.before`. Los argumentos llegan en el **segundo**
      parámetro, no en el primero.

## Bloque 3 — Redacción de patrones (RF-004 … RF-007)

- [x] **T008** `[RF-004]` Tabla `PATRONES`, con las claves privadas primero para que su
      bloque desaparezca entero antes de que otro patrón lo toque por dentro.
- [x] **T009** `[RF-006]` Patrón `ASIGNACION`, **solo** con valor entrecomillado.
- [x] **T010** `[P]` `[RF-007]` Lista `MARCADORES` de valores de relleno.
- [x] **T011** `[RF-005]` `redactar()` reemplaza en el lugar y devuelve los hallazgos sin
      los valores.
- [x] **T012** Enganchar en `tool.execute.after`, mutando `output.output` y `output.title`.

## Bloque 4 — Auditoría (RF-008)

- [x] **T013** `[RF-008]` Registrar `{herramienta, ruta, tipo, cantidad}` reutilizando
      `anotar()` de `auditoria-core.js`.

## Bloque 5 — Verificación

- [x] **T014** `[P]` Tests por patrón, con un caso que redacta y uno que no → **CA-005**.
- [x] **T015** `[P]` Test que lee este repositorio y exige cero hallazgos → **CA-003**.
- [x] **T016** `[P]` Extender `hooks.test.mjs` para que valide también este plugin (P4).
- [x] **T017** Ejercer los hooks con sus firmas reales y observar la salida → **CA-001**,
      **CA-002**, **CA-004**.

## Bloque 6 — Cierre

- [x] **T018** Sección del README diciendo qué cubre y, sobre todo, qué **no** (P7).
- [x] **T019** `[P]` Bug y causa raíz en el vault: el fixture con el PAT real (P8).
- [x] **T020** Completar [`trazabilidad.md`](trazabilidad.md) y dejar
      `tests/test_trazabilidad.py` en verde.

## Orden y paralelismo

```
Bloque 1  ──►  Bloque 2  ──┐
          └──►  Bloque 3  ──┼──►  Bloque 4  ──►  Bloque 5  ──►  Bloque 6
                            ┘
```

Los bloques 2 y 3 son independientes entre sí: cada uno cubre un modo de fallo distinto y
se puede entregar solo. El 4 necesita que exista algo que registrar.
