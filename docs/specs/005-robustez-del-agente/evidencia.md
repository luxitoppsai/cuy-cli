# Evidencia — RFC-005, primera etapa

2026-10-08. Fuente y binario local; no se ha publicado una release.

- Desde el paquete del motor: `bun test test/tool/write.test.ts
  test/tool/edit.test.ts test/tool/apply_patch.test.ts --only-failures`: 80 pruebas,
  0 fallos. Ocho casos nuevos comprueban conflictos durante aprobación, conservación
  del conjunto del parche y destinos existentes. Dos regresiones anteriores que
  admitían sobrescribir mediante Add/Move ahora comprueban el rechazo definido en
  RF-002; conservan las verificaciones de contenido.
- `bun typecheck`: correcto. La comprobación detectó inicialmente que un fixture
  introducía dependencias en el callback de permisos; se corrigió el fixture.
- Motor local compilado con Bun, versión `0.4.3-rfc005-local`, sin interfaz web
  embebida ni publicación. Smoke test `--version`: correcto.
- Contrato `tests/test_motor.py` con `CUY_TEST_BINARIO` apuntando al binario local:
  6 pruebas, 5 correctas y 1 omitida por no configurar CodeGraph real. Presupuesto,
  permisos de plan, instrucciones, edición/auditoría y corrección verificada pasan
  contra un proveedor SSE ficticio. El entorno restringido impidió abrir el puerto;
  se repitió con permiso para localhost. No se llamó a Databricks.
- Trazabilidad: 5 comprobaciones correctas; cobertura parcial explícita en la tabla.

## Límites y pendientes

La comprobación actual vincula el diff preparado a los bytes del archivo, no a la
lectura previa del modelo. No ofrece recuperación segura, bloqueo de editores
externos, atomicidad de parches ni protección de escrituras por shell/MCP/formateadores.
RF-003 a RF-007 continúan pendientes. El binario distribuido 0.4.3 y la selección
local del usuario no se han reemplazado. Las pruebas sintéticas no miden calidad
de modelos ni equivalencia con proveedores directos.
