# Instrucciones para trabajar en cuy-cli

Lee y aplica las [buenas prácticas compartidas](instrucciones/AGENTS.md). Son las mismas
que Cuy incorpora al contexto al trabajar con OpenCode. Las instrucciones de este archivo
añaden el contexto propio del desarrollo de la herramienta y sirven también para Codex.

## Producto

El uso principal es la conversación libre: el usuario escribe, el agente investiga,
edita y verifica con los permisos configurados. No introduzcas un asistente de inicio
ni obligues a usar comandos de tarea para obtener ese comportamiento.

Python instala, configura y lanza el motor de OpenCode en `vendor/opencode`.
Los plugins locales añaden presupuesto, auditoría y redacción limitada de secretos.
Mantén las instrucciones, rutas y documentación portables entre equipos y repositorios.

## Cambios y comprobaciones

- Para decisiones de diseño consulta `docs/CONSTITUCION.md` y `docs/SDD.md`. Los RFC viven en `docs/rfc/`; los planes y la evidencia, en `docs/specs/`.
- Python: `python3 -m unittest discover tests` (en Windows, `python`). JavaScript de plugins: `npm test`.
- Dentro de `vendor/opencode`, lee las instrucciones de la carpeta afectada. Ejecuta las pruebas y `bun typecheck` desde el paquete correspondiente, no desde la raíz del vendor.
- Prueba el motor real con `CUY_TEST_BINARIO` cuando cambies su integración. Las pruebas simuladas no demuestran calidad de modelos de Databricks; las llamadas reales requieren configuración y presupuesto autorizado.
- Los cambios en el fuente del motor no actualizan los binarios publicados. Distingue fuente verificado, binario local compilado y release distribuida.
- No copies contenido de `.env` ni configuraciones privadas a documentación o salidas de diagnóstico.

## Documentación

El README explica el uso. `docs/README.md` organiza las guías; `docs/REFERENCIA.md`
describe límites técnicos. Conserva la diferencia entre comportamiento implementado,
propuestas futuras y evidencia de pruebas. Registra las decisiones en el repositorio,
sin depender de archivos personales ni plugins específicos del editor.
