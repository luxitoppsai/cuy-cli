# cuy-cli

Asistente de programación en terminal sobre **OpenCode + Databricks Model Serving**.
Python resuelve instalación, descubrimiento y lanzamiento; OpenCode ejecuta el agente;
los plugins locales agregan presupuesto, auditoría y redacción de secretos.

**Estado:** prototipo con pruebas unitarias y una prueba de contrato del motor contra un
proveedor sintético. La calidad de tareas completas con los modelos del workspace debe
validarse con evaluaciones reales antes de desplegar al equipo.

## Instalar y usar

Requisitos: Python 3.10+ y Node/npm para el camino predeterminado.

```bash
git clone https://github.com/luxitoppsai/cuy-cli.git
cd cuy-cli
python3 instalar.py                 # en Windows: python
./cuy                              # en Windows: cuy.cmd
```

La instalación usa `npm ci` y la versión exacta de `package-lock.json`. Pide host HTTPS
y token, descubre modelos, escribe configuración y comprueba una respuesta con el
contrato del proveedor elegido. Esta prueba consume tokens y no acredita edición ni
calidad agéntica. `--sin-verificar` omite esa llamada final; el descubrimiento también
hace llamadas. `--rapido` omite solamente el sondeo de límites de salida.

La configuración queda en `opencode.json` y el token en `.env` (ignorados por git).
Las variables ya exportadas tienen precedencia. Cambiar de workspace requiere ejecutar
nuevamente el instalador y proporcionar la credencial correspondiente.

Para trabajar en otro proyecto, invocá el lanzador por su ruta:

```bash
cd /ruta/al/proyecto
/ruta/a/cuy-cli/cuy
/ruta/a/cuy-cli/cuy doctor
/ruta/a/cuy-cli/cuy doctor --json
/ruta/a/cuy-cli/cuy gasto
```

El proyecto sigue siendo el directorio actual. El lanzador carga la configuración y los
plugins fuente de Cuy por rutas absolutas, sin copiar plugins ni depender de la carpeta
`.opencode` del proyecto. También aplica las restricciones actualizadas a configuraciones
generadas por versiones anteriores. Los `opencode.json` y plugins locales del proyecto
no se cargan. Las instrucciones de trabajo deben vivir en `AGENTS.md`.

`doctor` comprueba archivos, configuración efectiva de Cuy, tarifas, credencial presente,
contabilidad y versión del ejecutable. No imprime el token. **No certifica** la carga
real de hooks, aislamiento de red ni políticas del servidor. `doctor --verificar` agrega
una llamada real y facturable al proveedor configurado.

## Entender, corregir y revisar

```bash
./cuy inicio                          # portada y estado local
./cuy tarea entender "Explicá el recorrido de un pedido"
./cuy tarea revisar "Buscá regresiones en src/stock.py"
./cuy tarea corregir "Corregí el límite de reserva" --prueba "python -m unittest tests.test_stock"
./cuy demo                            # resultado de ejemplo, sin inferencia
```

En Windows se usa `cuy.cmd`. Los tres flujos requieren un repositorio Git con un commit.
`--proyecto /ruta/al/repo` elige otro proyecto. `--json` devuelve el informe estructurado.
`--timeout 600` fija el tiempo máximo del motor y de **cada** prueba; no es un límite total
ni un presupuesto por tarea.

| Flujo | Entregable | Comprobación del lanzador |
|---|---|---|
| Entender | Resumen y referencias | Las rutas/líneas existen; sin cambios detectados |
| Revisar | Hallazgos con severidad, evidencia e impacto | Ubicaciones válidas; sin cambios detectados |
| Corregir | Worktree, diff exportado e informe | Pruebas explícitas antes/después; original sin cambios detectados |

Los agentes de tarea tienen permisos propios: lectura/búsqueda y, solo para corregir,
edición. No reciben shell, delegación ni acceso fuera del directorio. `revisar` analiza
el código actual indicado por el usuario; no reconstruye automáticamente un diff histórico.
La validez de una referencia no demuestra que la conclusión del modelo sea correcta.

**Corregir exige un árbol limpio** y crea un worktree separado desde HEAD. Si hay cambios
previos, los conserva y no inicia la corrección. Entender/revisar sí pueden analizar el
estado actual con cambios pendientes. No se copian archivos ignorados, credenciales ni
entornos de dependencias al worktree. Las pruebas deben poder ejecutarse en ese entorno.

`--prueba` es una autorización explícita para ejecutar ese comando **antes y después** de
la edición; se puede repetir. Se ejecuta como lista de argumentos, sin shell ni operadores
como `&&` o pipes. Para rutas con espacios o separadores Windows, entrecomillá el ejecutable
dentro del argumento. Las pruebas ejecutan código con los permisos del usuario; no son un
sandbox. Se retiran las credenciales conocidas del proveedor y su configuración del entorno
del proceso de prueba. No se transmite la salida cruda de las pruebas al modelo.

Un cambio solo aparece **VERIFICADA** si se entregó el informe requerido, hubo cambios y
todas las pruebas elegidas terminaron con código 0 sin timeout. No significa ausencia de
bugs: solo acredita esas comprobaciones. Sin pruebas o con pruebas fallidas queda
**SIN VERIFICAR** (exit code 2). Errores del motor, formato inválido, referencias inventadas,
cambios inesperados o cancelación no se presentan como éxito (exit code 1).
Entender/revisar válidos se marcan **ENTREGADA · por revisar** (exit code 0).

El informe conserva base Git, cambios detectados, sesiones, duración, costo reportado por
los pasos y códigos de prueba antes/después. La detección compara archivos versionados y
no ignorados; no inspecciona todo el sistema, archivos ignorados ni el interior de submódulos.
Si las pruebas modifican archivos no ignorados se pide inspección, no se acepta el cambio
como verificado. El costo de pasos no incluye necesariamente llamadas auxiliares del motor.

Resultados en `~/.local/share/cuy-cli/tareas/<id>/` (`CUY_TAREAS` permite otra carpeta **fuera**
del proyecto): `base.json`, `resultado.json`, `cambios.patch` y el worktree cuando corresponda.
El patch incluye archivos nuevos sin staging ni commits automáticos. El informe y el diff
pueden contener información del proyecto: se guardan localmente, con permisos restrictivos
cuando el sistema los soporta. No se exportan a otro servicio.

Inspeccioná el resultado con `git -C <worktree> status --short`, `git -C <worktree> diff` y
el patch exportado. La aplicación al repositorio original y la limpieza del worktree son
manuales. No hay auto-commit, auto-publicación ni reanudación automática tras interrupción.

### Vista visual

[Demo interactiva local](docs/demo.html) · [captura renderizada](docs/demo.png).
Los ejemplos son simulados y usan el mismo renderizador de resultados que las tareas reales.

```bash
./cuy demo --flujo entender
./cuy demo --flujo revisar
./cuy demo --flujo pendiente
./cuy demo --html /tmp/cuy-demo.html
```

La demo no llama al modelo. La terminal adapta el ancho y desactiva colores al redirigir
salida o definir `NO_COLOR`. La página tiene pestañas navegables por teclado y permite
inspeccionar los estados sin ejecutar tareas.

## Origen y actualización del motor

- **Predeterminado:** paquete oficial fijado a `opencode-ai@1.18.32`, con marca OpenCode.
- `python3 instalar.py --compilar`: compila el subtree `vendor/opencode` con Bun y lockfile
  congelado. Requiere descargar las dependencias del build; no hace falta para usar Cuy.
- `python3 instalar.py --binario-manifiesto release.json`: descarga una release propia
  fijada por un manifiesto local revisado. Exige `version` y un mapa `sha256` por nombre
  de artefacto (`cuy-darwin-arm64`, `cuy-windows-x64.exe`, etc.). No acepta `latest`.

Las descargas se validan antes de reemplazar el ejecutable. No se publica un manifiesto
con hashes inventados: quien construye la release debe producirlo y revisarlo. Un hash
comprueba integridad respecto del manifiesto; no sustituye su procedencia confiable.

La selección instalada queda en `bin/seleccion.json`, evitando que una descarga antigua
oculte una compilación o instalación posterior. Las instalaciones anteriores mantienen
su selección por compatibilidad hasta reinstalar.

El fuente vendorizado y un binario pueden diferir. Ejecutá las pruebas del motor real
antes de aprobar una actualización. Cambiar el lockfile es deliberado; repetí también
la auditoría de red. La observación histórica en [spike/RED.md](spike/RED.md) solo describe
la versión y los escenarios allí medidos.

En redes corporativas con certificados propios, configurá `NODE_EXTRA_CA_CERTS`. El
build intenta exportar raíces del sistema en Windows. No desactives la validación TLS.

## Agentes y permisos

| Rol | Modelo inicial | Herramientas |
|---|---|---|
| `build` | Preferencia Sonnet; respaldo por nombre/tamaño estimado | Edición habilitada, shell sujeto a política; hasta 30 pasos |
| `plan` | El mismo modelo capaz que `build` | Lectura y búsqueda; sin shell, edición ni delegación; hasta 15 pasos |
| `explore` | Preferencia Haiku; respaldo económico estimado | Subagente de lectura y búsqueda; hasta 15 pasos |

`scout` se retiró porque duplicaba `explore` y no tenía restricciones propias.
La selección por nombre es una heurística: no constituye una evaluación de capacidad.
Los límites de contexto y tarifas por familia también son valores configurados, no
capacidades descubiertas del servidor.

La política global no incluye `*: allow`: preserva restricciones nativas. Los roles de
lectura tienen una lista explícita de herramientas permitidas. Tests, `npm run` y `make`
piden permiso: ejecutan código del repositorio. Los patrones destructivos conocidos se
rechazan. La política está en `construir_permisos()` y el lanzador la aplica al arrancar;
modificar `permission` en el JSON generado no altera esa política.

**Los patrones de shell no son un sandbox.** Un comando permitido puede ejecutar código,
escribir o usar la red. En ejecución headless, una acción que pide permiso puede ser
rechazada por el motor; no asumas que una prueba pendiente fue ejecutada.

## Presupuesto y eficiencia

```bash
python3 gasto.py
CUY_LIMITE_USD=3 ./cuy              # macOS/Linux
# PowerShell: $env:CUY_LIMITE_USD="3"; .\cuy.cmd
```

El plugin comprueba el gasto mensual en `chat.params`, **antes de cada inferencia que
pasa por ese hook**, además de impedir nuevas herramientas al alcanzar el límite. Relee
el archivo en cada comprobación, por lo que detecta cambios de mes y gasto de otras
sesiones. Cuenta eventos `step-finish` una sola vez por identificador.

La persistencia usa lock entre procesos y reemplazo atómico. Un archivo corrupto o un
fallo contable bloquea la siguiente inferencia; no se interpreta como cero. Un lock
huérfano tras un cierre abrupto requiere revisar procesos activos antes de retirarlo.
El archivo está en `~/.local/share/cuy-cli/gasto.json` (`CUY_GASTO` cambia la ruta).

Con tope activo, un modelo sin tarifas positivas `cost.input`/`cost.output` se rechaza.
**Costo desconocido no significa gratis.** Se pueden declarar tarifas del contrato en
el modelo de `opencode.json`; `CUY_USD_POR_DBU` ajusta la conversión al regenerar.
`CUY_LIMITE_USD=0` desactiva explícitamente el tope local.

Es una **estimación local**, no un límite de facturación estricto: una petición iniciada
antes del corte puede exceder el saldo y varias peticiones simultáneas pueden estar en
vuelo. No reserva costo por anticipado, no cancela otras sesiones ni incluye llamadas
hechas fuera del motor, como sondeos de instalación. Los precios, descuentos y tokens de
caché deben contrastarse con el contrato y consumo del servidor. El límite corporativo
pertenece al Gateway, fuera del control del usuario local.

## Secretos y auditoría

El plugin rechaza rutas sensibles conocidas y redacta patrones en salidas de herramientas,
títulos y metadatos. Incluye PATs, claves privadas, asignaciones entre comillas en código
y JSON, y cabeceras Bearer/Basic. La auditoría aplica saneamiento antes de persistir,
incluyendo argumentos y parámetros de URL reconocibles.

La cobertura es deliberadamente limitada: regex no reconoce todos los secretos, alias,
enlaces simbólicos, archivos adjuntos ni valores transformados. No redacta el prompt que
una persona pega directamente. Un archivo `.env.example` puede leerse; su nombre no
prueba que sus valores sean inocuos. La redacción tampoco garantiza que una reescritura
completa de archivo preserve un valor que el modelo no vio.

```bash
python3 auditar.py
python3 auditar.py --comandos
python3 auditar.py --archivos --dias 30
```

El registro usa `sessionID` y `callID` reales. Distingue `herramienta.intento` de
`herramienta.resultado` (`completed` o `error`); una sesión `idle` queda como estado, no
como cierre definitivo. Captura eventos `permission.asked` y `permission.replied`.
No todas las denegaciones automáticas emiten una consulta: el resultado de herramienta
puede mostrar el fallo sin atribuir su causa. No se guardan salida, contenido editado ni
texto de errores.

Los informes muestran resultados completados. Registros antiguos sin resultado no se
consideran éxito. Ubicación: `~/.local/share/cuy-cli/auditoria.jsonl`, configurable con
`CUY_AUDITORIA`. Retención de 90 días (`CUY_RETENCION_DIAS`); la limpieza y los append
comparten lock. `CUY_AUDITORIA_OFF=1` desactiva el registro local.

**No es evidencia inmutable:** el usuario puede modificar plugins, políticas y registros.
La atribución local tampoco sustituye la identidad autenticada de Databricks.

## Red y gobierno

El lanzador desactiva actualización automática, descarga de catálogo, compartir sesiones,
descarga de LSP y skills externas. Esto reduce conexiones automáticas conocidas; **no es
un firewall ni garantiza que solo se contacte Databricks**. Dependencias, configuraciones
globales de OpenCode, plugins, MCP y herramientas pueden introducir otras conexiones.
Los controles locales no aíslan código malicioso ni administradores del equipo.

Para gobierno corporativo hacen falta controles independientes: autenticación central,
allowlist de modelos, restricciones de salida, presupuesto y auditoría del servidor.
El plan de evolución con criterios verificables está en
[docs/EVOLUCION.md](docs/EVOLUCION.md).

## Pruebas

```bash
python3 -m unittest discover tests
node --test tests/*.test.mjs

# Contrato con el ejecutable real, proveedor local sintético y carpetas temporales:
CUY_TEST_BINARIO="$PWD/bin/cuy" python3 -m unittest discover -s tests -p test_motor.py
# También se puede apuntar a node_modules/opencode-ai/bin/opencode.exe.
```

La prueba del motor comprueba edición y auditoría, ausencia de herramientas de escritura
en `plan`, bloqueo antes de llegar al proveedor cuando se agotó el presupuesto y el flujo
completo de corrección aislada con prueba antes/después y patch exportado. Usa
localhost y credenciales ficticias: no llama a Databricks ni mide calidad del modelo.
Sin `CUY_TEST_BINARIO`, esas pruebas se omiten explícitamente. CI ejecuta pruebas unitarias
y de contrato con el paquete fijado en Windows, macOS y Linux.

Los RFC y spikes conservan decisiones e hipótesis históricas; este README describe el
comportamiento actual.

### Si Databricks devuelve HTTP 401 al listar endpoints

El descubrimiento consulta `GET /api/2.0/serving-endpoints` del workspace de
Databricks. Un 401 indica que se rechazó la autenticación, antes de probar los
modelos. Revisá que `DATABRICKS_HOST` sea la URL raíz del workspace correcto y
que su PAT o access token OAuth siga vigente.

La variable `DATABRICKS_TOKEN` del entorno tiene prioridad sobre `.env`.
Actualizala si está definida. Si preferís usar el archivo, eliminá la variable
de la terminal (`Remove-Item Env:DATABRICKS_TOKEN` en PowerShell o
`unset DATABRICKS_TOKEN` en macOS/Linux) y ejecutá:

```sh
python instalar.py --renovar-token --host https://TU-WORKSPACE
```

El token se pide de forma oculta y se reemplaza sin borrar las otras opciones de
`.env`. En macOS/Linux podés necesitar `python3`. Las comillas y `export` en
`.env` están admitidos. No pegues credenciales en comandos, capturas ni reportes.

### Windows: «Esta aplicación no se puede ejecutar en el equipo»

En PowerShell usá `.\cuy.cmd`. Primero comprobá `python --version`: si también
falla, hay que reparar la instalación de Python para ese equipo. Si Python funciona,
reinstalá el motor desde la carpeta del proyecto:

```powershell
python instalar.py --reparar-motor
.\cuy.cmd
```

La reparación requiere npm y acceso a su registro, pero no consulta Databricks ni
modifica el token o la configuración de modelos. Instala el paquete fijado en el
proyecto y actualiza el ejecutable seleccionado. No copies `node_modules` ni los
binarios compilados de macOS/Linux a Windows. El lanzador valida el formato Windows
antes de intentar ejecutar el agente; esa validación no sustituye una prueba en la
versión y arquitectura de Windows de destino.
