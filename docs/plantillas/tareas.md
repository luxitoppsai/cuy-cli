---
tipo: tareas
spec: RFC-NNN
proyecto: cuy-cli
fecha: AAAA-MM-DD
---

# Tareas — RFC-NNN, {{título}}

> Plan: [`plan.md`](plan.md) · Spec: [`../../rfc/RFC-NNN-slug.md`](../../rfc/RFC-NNN-slug.md)

Formato: `TNNN [P] [RF-NNN] descripción`. `[P]` marca las que pueden ir en paralelo dentro
de su bloque — archivos distintos, sin dependencia entre ellas. Cada descripción nombra el
archivo concreto que toca.

## Bloque 1 — Base

Lo que bloquea a todo lo demás. Cuanto más chico, mejor.

- [ ] **T001** …

## Bloque 2 — {{primer entregable}}

Cada bloque a partir de acá debe poder entregarse **solo** y aportar algo por sí mismo. Si
dos bloques no sirven por separado, son un solo bloque.

- [ ] **T002** `[RF-001]` …

## Bloque N — Verificación

Una tarea por criterio de aceptación, nombrando el criterio que cierra.

- [ ] **T00N** … → **CA-001**

## Bloque final — Cierre

- [ ] Documentar en el README qué cubre y qué **no**.
- [ ] Completar `trazabilidad.md` y dejar `tests/test_trazabilidad.py` en verde.
- [ ] Registrar en el vault los bugs con causa raíz y las decisiones como ADR.

## Orden y paralelismo

Un diagrama de qué depende de qué, aunque sea en texto.
