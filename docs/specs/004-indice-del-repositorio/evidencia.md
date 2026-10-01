# Evidencia — RFC-004

Verificación local el 2026-09-30, en macOS.

| Comprobación ejecutada | Resultado |
|---|---|
| `python3 -m unittest discover tests` | 149 pruebas: sin fallos, 8 omitidas por ejecutables opcionales no definidos. |
| `test_codegraph.py` con `CUY_TEST_CODEGRAPH` apuntando al asset darwin-x64 de 0.20.1 | 18 pruebas, sin fallos ni omisiones. |
| `test_motor.py` con CodeGraph real y el motor Cuy 0.4.3 compilado para darwin-arm64 | 6 pruebas, sin fallos. Proveedor SSE sintético en localhost. |
| `npm test` | Sin fallos. |
| `test_trazabilidad.py` | 5 pruebas, sin fallos. |
| `git diff --check` | Sin errores. |
| `git check-ignore` para estado local y binario | Las rutas generadas quedan excluidas. |

El contrato nativo ejerció búsquedas por símbolo y por URI, cambios de contenido,
altas, borrados y traducción a las rutas originales. El contrato del motor comprobó
que el agente `plan` recibe las herramientas de consulta, ejecuta una consulta MCP y
recibe su resultado sin habilitar escritura ni shell.

Se descargaron los assets macOS ARM64 y x64 y se comprobaron contra los SHA-256 fijados
en `codegraph-release.json`. La descarga x64 también recorrió el instalador Python real.
Las pruebas de checksum incorrecto, sidecar de Windows y plataformas son simuladas.
No se ejecutaron binarios de Windows ni Linux.

Sobre este repositorio, una preparación con cambios tardó 0.466 s, la preparación
sin cambios siguiente 0.373 s y una consulta por `entorno_agente` 0.386 s. Son mediciones
locales de una caché ya creada, no un benchmark de arranque frío ni del comportamiento
del modelo. No acreditan reducción de tokens o tiempo de resolución de tareas.

La prueba nativa mostró una ambigüedad del resolvedor de CodeGraph: consultar la
primera línea puede devolver el nodo `CodeFile` en vez de la función. Sus propiedades
de ubicación usan líneas desde 1 aunque algunos esquemas nativos dicen desde 0.
El adaptador aclara la numeración observada en los esquemas y la guía explica el límite;
la búsqueda por nombres y las consultas dentro del cuerpo sí se verificaron.

No se hicieron llamadas a Databricks ni se evaluó calidad con modelos reales.
No cambió el fuente ni el binario del motor; el cambio vive en el lanzador Python y
el adaptador local. La suite completa con ambas variables de motores reales juntas
no se repitió: se ejecutaron sus contratos por separado.
