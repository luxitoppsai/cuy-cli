# Plan — RFC-005

1. Comprobar versiones después de permisos en write, edit y apply_patch; probar
   modificaciones concurrentes, altas, borrados y movimientos.
2. Registrar versiones de lectura y recuperación; integrar undo sin sobrescribir
   cambios ajenos. No habilitar una garantía de recuperación antes de verificarla.
3. Unificar permisos, acotar ejecución local, mejorar índice y contexto, aplicar
   límites de operaciones y ampliar auditoría. Documentar cada entrega y su evidencia.

## Compuerta constitucional (1.0.1)

| Principio | Aplicación |
|---|---|
| P1 | Pruebas del motor y diferencia explícita entre fuente, binario y release. |
| P2 | Inspeccionar herramientas existentes y resolver rutas del proyecto. |
| P3 | Casos deterministas con modificación durante aprobación; contratos reales posteriores. |
| P4 | Integrar Effect y FSUtil existentes; verificar tipos del paquete. |
| P5 | Rechazar conflictos conservando ediciones normales, BOM y finales de línea. |
| P6 | Conflicto aborta antes de mutar y pide releer; errores de E/S no son archivo ausente. |
| P7 | Comparación optimista y ejecución acotada no constituyen aislamiento. |
| P8 | No registrar contenidos ni credenciales; recuperación local restringida pendiente. |
| P9 | Reutilizar herramientas y librería estándar; no introducir un framework. |
| P10 | RFC, tareas, evidencia y limitaciones en el repositorio. |
