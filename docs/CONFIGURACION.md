# Configuración

Cuy separa la carpeta de instalación del proyecto donde trabaja. Los archivos de configuración
se buscan en `~/.local/share/cuy-cli` en el paquete compilado, independientemente
de la carpeta desde la que lo ejecutes. En desarrollo desde fuentes se conservan
junto al lanzador.
Los ejemplos usan nombres genéricos y funcionan con cualquier remoto del repositorio.

## Archivos y precedencia

- `.env`: credencial local y opciones del lanzador. Excluido de Git.
- `opencode.json`: modelos, proveedores y tarifas generados por el instalador. No se versiona.
- El paquete contiene el motor en `_internal/motor`; no usa una selección de ejecutable editable. En instalaciones desde fuentes, `bin/seleccion.json` conserva la selección del instalador anterior.
- `AGENTS.md` del proyecto de trabajo: instrucciones para el agente. Cuy no carga la configuración `opencode.json` ni los plugins locales de ese proyecto.
- `codegraph-release.json`: versión y hashes del indexador, versionados junto al código.
  Su binario verificado se guarda en `bin/codegraph/<version>/` de los datos locales
  en el paquete, o de la instalación al usar fuentes.
- `.cuy/codegraph/` del proyecto de trabajo: copia e índice local, preparados al abrir
  una conversación. El lanzador añade MCP y permisos de consulta solo a la configuración
  de esa ejecución. Consulta [el índice del repositorio](INDICE-DEL-REPOSITORIO.md).

El lanzador carga `.env` sin reemplazar variables ya exportadas. El lector acepta comillas y
el prefijo `export`, pero **no expande** variables ni ejecuta comandos: usa valores y rutas
completos, no expresiones como `$HOME/datos` dentro de `.env`.

Durante la instalación, el host se toma en este orden: `--host`, `DATABRICKS_HOST` del entorno,
`.env`, o la selección interactiva (que puede ofrecer el workspace de la configuración previa).
El token se toma del entorno, de `.env` o de la entrada oculta. `--renovar-token` sustituye
el guardado; si hay uno exportado, primero debes actualizarlo o quitarlo del entorno.

Después de instalar, el endpoint de las conversaciones procede de `opencode.json`.
Cambiar solamente `DATABRICKS_HOST` no regenera los proveedores: vuelve a ejecutar el instalador
para cambiar de workspace. El lanzador reaplica su política de permisos al iniciar;
editar `permission` en el JSON no sustituye esa política.

## Variables de uso habitual

Estas opciones se pueden exportar antes de abrir Cuy. El lanzador también las lee de `.env`.
Para ejecutar utilidades directamente, exporta las opciones en la terminal; no asumas que
todos los scripts cargan `.env` por sí solos.

| Variable | Valor predeterminado | Uso |
|---|---|---|
| `DATABRICKS_HOST` | Sin valor fijo | URL HTTPS raíz del workspace para el instalador |
| `DATABRICKS_TOKEN` | Sin valor fijo | PAT o access token OAuth suministrado por el usuario; no hay renovación OAuth automática |
| `CUY_USD_POR_DBU` | `0.07` | Conversión de referencia al generar o actualizar tarifas; no modifica gastos históricos |
| `CUY_TARIFAS` | Sin archivo personalizado | Ruta de JSON con tarifas contractuales por endpoint |
| `CUY_GASTO` | `~/.local/share/cuy-cli/gasto.json` | Ruta alternativa solo para desarrollo desde fuentes; el paquete conserva su ruta fija |
| `CUY_TAREAS` | `~/.local/share/cuy-cli/tareas` | Resultados; debe estar fuera del proyecto analizado |
| `CUY_AUDITORIA` | `~/.local/share/cuy-cli/auditoria.jsonl` | Registro local de actividad |
| `CUY_RETENCION_DIAS` | `90` | Retención de auditoría; `0` desactiva la limpieza por antigüedad |
| `CUY_AUDITORIA_OFF` | Desactivada | `1` apaga el registro local |
| `NO_COLOR` | Sin definir | Desactiva los colores de la presentación de Cuy |
| `NODE_EXTRA_CA_CERTS` | Sin archivo adicional | Certificados PEM adicionales para el motor; no configura por sí solo el cliente HTTPS de Python |

Los valores monetarios deben ser finitos y no negativos. Con tope activo, tarifas desconocidas
o contabilidad inválida bloquean nuevas inferencias. Consulta [costos y contexto](COSTOS-Y-CONTEXTO.md)
para el formato de tarifas y [referencia técnica](REFERENCIA.md) para el alcance de los controles.

Ejemplo de opciones no secretas en `.env`:

```dotenv
CUY_RETENCION_DIAS=90
```

No copies credenciales en comandos ni ejemplos. El instalador solicita el token de forma oculta.

El presupuesto y el umbral de aviso proceden de la distribución; `.env` y las
variables de la terminal no los cambian ni desactivan. `cuy gasto` muestra el importe.

## Datos locales

La carpeta predeterminada `.local/share/cuy-cli` cuelga de la carpeta personal del usuario
en todos los sistemas, incluido Windows; no se cambia automáticamente a AppData.
Las evaluaciones se guardan en su subcarpeta `evaluaciones`; `evaluar.py --salida` permite
seleccionar otro archivo fuera del repositorio.

Gasto y auditoría usan archivos separados de los informes de tareas. Los informes y patches
pueden contener información del proyecto. No borres la contabilidad para resolver un bloqueo:
revisa `cuy doctor` y la causa. Los worktrees necesitan además su limpieza mediante Git,
explicada en [correcciones](CORRECCIONES.md).

El motor puede mantener sus propios datos de sesión: esta lista describe los archivos de Cuy,
no un inventario completo de todos los archivos creados por OpenCode.

## Buenas prácticas e instrucciones del proyecto

Cuy añade `instrucciones/AGENTS.md`, desde su propia instalación, al contexto de cada
conversación. Contiene las prácticas generales de diseño, revisión y verificación.
Se carga por ruta absoluta calculada al arrancar, así que funciona al abrir otro proyecto
sin copiar archivos ni depender de la configuración personal de Claude o Codex.
Cuy desactiva la carga de `CLAUDE.md`; usa `AGENTS.md` para las reglas del proyecto.

El motor de Cuy también lee `AGENTS.md` del proyecto de trabajo aunque su configuración
local de OpenCode esté desactivada. Esto no habilita `opencode.json` ni plugins del
proyecto. Las instrucciones de subcarpetas se incorporan cuando el motor lee archivos
allí. El Markdown orienta al modelo: no modifica permisos ni garantiza cumplimiento.

En este repositorio, `AGENTS.md` añade las reglas para desarrollar Cuy. En otro proyecto,
usa su propio `AGENTS.md` para comandos de prueba, arquitectura y convenciones del equipo.
Las buenas prácticas generales indican que se respeten esas convenciones específicas.

La carga de `AGENTS.md` del proyecto con configuración local desactivada está disponible
desde el motor 0.4.3. Actualiza mediante el paquete aprobado por tu equipo.
Los binarios anteriores pueden seguir omitiendo esas instrucciones.
