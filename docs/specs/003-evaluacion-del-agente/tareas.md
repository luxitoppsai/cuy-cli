# Tareas — RFC-003

- [x] T001 Materializar y validar casos en `evaluar.py` (RF-001, RF-011).
- [x] T002 Contabilizar pasos incompletos en `tareas.py` (RF-012).
- [x] T003 Guardia adicional de corrida en `plugin/presupuesto.js` (RF-008, RF-009).
- [x] T004 Runner, clasificación e informes en `evaluar.py` (RF-002 a RF-007, RF-010, RF-013).
- [x] T005 Casos de regresiones históricas en `evaluacion/casos/` y pruebas del evaluador.
- [x] T006 Documentación y trazabilidad de cada RF/CA, con límites explícitos.
- [ ] T007 Baseline con modelos reales y comparación entre configuraciones (H3/H4).

Orden: T001/T002/T003 antes de T004; T005 y T006 antes del baseline.

## Enmienda 1

- [x] T008 Fases, códigos y límite efectivo desde tareas; integridad explícita.
- [x] T009 Errores locales/globales, manifiestos inválidos, costos preservados y no ejecutados.
- [x] T010 Grupos explícitos, dos objetivos por síntoma y agregados parciales.
- [x] T011 Validación diferida del plugin y tests de rechazo sin inferencia.
- [x] T012 Main, aritmética, regresiones, trazabilidad y documentación verificadas.

## Verificación de estado — 2026-09-28

Se reconciliaron T008–T012 con la implementación, la tabla de trazabilidad y las
pruebas actuales. `python3 -m unittest discover tests` terminó sin fallos: 129 pruebas,
con cuatro omisiones del contrato del motor por no configurar `CUY_TEST_BINARIO`.
`npm test` terminó sin fallos, incluidos los hooks de presupuesto de evaluación.
La suite Python incluye las 25 pruebas del evaluador y las cinco de trazabilidad.
Esta evidencia cierra la implementación local de la enmienda; no acredita una corrida
con Databricks. T007 permanece pendiente.
