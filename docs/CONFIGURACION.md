# Configuración

Cuy separa la carpeta de instalación del proyecto donde trabaja. Los archivos de configuración
se buscan junto a `cuy.py`, independientemente de la carpeta desde la que lo ejecutes.
Los ejemplos usan nombres genéricos y funcionan con cualquier remoto del repositorio.

## Archivos y precedencia

- `.env`: credencial local y opciones del lanzador. Excluido de Git.
- `opencode.json`: modelos, proveedores y tarifas generados por el instalador. No se versiona.
- `bin/seleccion.json`: ejecutable seleccionado; contiene una ruta local absoluta. Si mueves la instalación, ejecuta `python3 instalar.py --reparar-motor` desde su nueva ubicación.
- `AGENTS.md` del proyecto de trabajo: instrucciones para el agente. Cuy no carga la configuración `opencode.json` ni los plugins locales de ese proyecto.

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
| `CUY_LIMITE_USD` | `10` | Tope mensual local estimado; `0` lo desactiva |
| `CUY_AVISO_PORCENTAJE` | `80` | Umbral porcentual de aviso del presupuesto |
| `CUY_USD_POR_DBU` | `0.07` | Conversión de referencia al generar o actualizar tarifas; no modifica gastos históricos |
| `CUY_TARIFAS` | Sin archivo personalizado | Ruta de JSON con tarifas contractuales por endpoint |
| `CUY_GASTO` | `~/.local/share/cuy-cli/gasto.json` | Archivo de contabilidad local |
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
CUY_LIMITE_USD=5
CUY_AVISO_PORCENTAJE=80
CUY_RETENCION_DIAS=90
```

No copies credenciales en comandos ni ejemplos. El instalador solicita el token de forma oculta.

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
