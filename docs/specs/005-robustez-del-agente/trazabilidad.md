# Trazabilidad — RFC-005

| Identificador | Test | Archivo |
|---|---|---|
| RF-001 | `preserves concurrent` | `vendor/opencode/packages/opencode/test/tool/write.test.ts` |
| RF-002 | `rejects move over existing destination and preserves both files` | `vendor/opencode/packages/opencode/test/tool/apply_patch.test.ts` |
| RF-003 | Pendiente; ver notas. | — |
| RF-004 | Pendiente; ver notas. | — |
| RF-005 | Pendiente; ver notas. | — |
| RF-006 | Pendiente; ver notas. | — |
| RF-007 | Pendiente; ver notas. | — |
| CA-001 | `edit preserves concurrent` | `vendor/opencode/packages/opencode/test/tool/edit.test.ts` |
| CA-002 | `preserves all files when one patch target changes during approval` | `vendor/opencode/packages/opencode/test/tool/apply_patch.test.ts` |
| CA-003 | Pendiente; ver notas. | — |
| CA-004 | Pendiente; ver notas. | — |
| CA-005 | Pendiente; ver notas. | — |
| CA-006 | Pendiente; ver notas. | — |

## Notas

RF-002 también se verifica con destinos creados durante aprobación, altas existentes
y la inclusión de ambas rutas en la autorización de movimiento.
RF-003 y CA-003: versiones de lectura y recuperación aún no implementadas.
RF-004 y CA-004: permisos comunes y auditoría de decisiones aún pendientes.
RF-005 y CA-005: ejecución local acotada aún pendiente; no hay sandbox disponible.
RF-006 y CA-006: mejora incremental y contexto versionado aún pendientes.
RF-007: límites de operaciones y ampliación de auditoría aún pendientes.
Esta tabla registra cobertura parcial; no acredita cierre del RFC.
