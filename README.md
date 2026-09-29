# cuy-cli

**Un asistente de programación en tu terminal que usa los modelos disponibles en tu workspace de Databricks.** Puedes pedirle que explique un proyecto, busque errores, revise código o implemente cambios, sin salir del repositorio en el que trabajas.

Cuy usa OpenCode como motor e incorpora configuración para Databricks, permisos de herramientas, seguimiento del gasto y auditoría local.

> **Estado:** prototipo. Los flujos tienen pruebas automatizadas y de integración con un proveedor simulado; sigue pendiente validar su calidad con modelos reales del workspace. Revisa sus respuestas y cambios antes de incorporarlos a tu proyecto.

## Para qué sirve

- **Entender código:** localizar dónde se implementa una función y explicar cómo funciona, con referencias a archivos.
- **Revisar un problema:** buscar posibles errores y recibir hallazgos con ubicación, severidad e impacto.
- **Hacer cambios:** pedir una implementación en una conversación o ejecutar una corrección aislada con pruebas y un diff para revisar.

Puedes usarlo de dos formas: una **conversación interactiva** para trabajar paso a paso, o una **tarea por comando** para obtener un informe concreto.

## Antes de empezar

Necesitas:

- **Python 3.10 o posterior** y **Git**.
- Un equipo con **Windows, macOS o Linux** (x64 o ARM64).
- La URL de tu workspace de **Databricks** y un token válido con acceso a los endpoints que vas a usar.
- Conexión a tu workspace y al servidor de distribución del ejecutable.

La instalación normal descarga un binario preparado para tu sistema y verifica su checksum. **No necesitas Node, npm ni Bun.** Las consultas a modelos consumen recursos de Databricks; la instalación también realiza consultas para descubrir y comprobar modelos.

## Instalación

Usa la URL de clonación que proporcione tu equipo en lugar de `URL_DEL_REPOSITORIO`.
Los ejemplos crean una carpeta local llamada `cuy-cli`, independientemente del nombre
del repositorio remoto. Las rutas de ejemplo se sustituyen por las de tu equipo.

### macOS y Linux

```bash
git clone "URL_DEL_REPOSITORIO" cuy-cli
cd cuy-cli
python3 instalar.py
./cuy
```

### Windows · PowerShell

```powershell
git clone "URL_DEL_REPOSITORIO" cuy-cli
cd cuy-cli
python instalar.py
.\cuy.cmd
```

El instalador solicita la URL del workspace y el token de forma oculta, descubre los modelos disponibles, genera la configuración y comprueba una respuesta. Guarda el token solicitado en `.env` (o reutiliza el del entorno) y la configuración en `opencode.json`, dentro de la carpeta de Cuy; ambos están excluidos de Git.

Si cambias de workspace, vuelve a ejecutar el instalador con la URL y la credencial correspondientes.

## Primera conversación en tu proyecto

Abre una terminal en el proyecto que quieres analizar y ejecuta Cuy por su ruta. Sustituye las rutas de ejemplo por las de tu equipo.

**macOS y Linux:**

```bash
cd /ruta/a/mi-proyecto
/ruta/a/cuy-cli/cuy
```

**Windows · PowerShell:**

```powershell
cd C:\ruta\a\mi-proyecto
& "C:\ruta\a\cuy-cli\cuy.cmd"
```

Cuy trabaja sobre la carpeta actual. Escribe directamente lo que necesitas: entender código,
revisar un problema o implementar un cambio. Por ejemplo:

```text
Explícame cómo se procesa un pedido y qué archivos intervienen. No modifiques nada.
```

```text
Revisa src/stock.py y busca errores en la validación de cantidades. Cita las líneas afectadas.
```

Usa **Planificar** para lectura y análisis, y **Editar** para implementar cambios con los permisos configurados. En la conversación interactiva, las ediciones se realizan sobre tu proyecto: revisa el diff antes de guardar un commit. Puedes elegir otro modelo disponible con `/models`.

Cuy carga sus [buenas prácticas](instrucciones/AGENTS.md) automáticamente. Para añadir
convenciones específicas, colócalas en `AGENTS.md` en la raíz de tu proyecto. Cuy usa su propia configuración; no carga los archivos `opencode.json` ni los plugins locales del proyecto.

## Tareas con un resultado para revisar

Los comandos `tarea` requieren un repositorio Git con al menos un commit. Estos ejemplos parten de la carpeta donde instalaste Cuy; `--proyecto` indica el repositorio de trabajo. En Windows, sustituye `./cuy` por `.\cuy.cmd`.

```bash
./cuy tarea entender "Explica el recorrido de un pedido" --proyecto /ruta/al/repo
./cuy tarea revisar "Busca regresiones en src/stock.py" --proyecto /ruta/al/repo
./cuy tarea corregir "Corrige el límite de reserva" --proyecto /ruta/al/repo --prueba "python -m unittest tests.test_stock"
```

Adapta la ruta, el objetivo y el comando de prueba a tu proyecto.

| Tarea | Qué recibes | Dónde trabaja |
|---|---|---|
| `entender` | Explicación con referencias a archivos y líneas | Proyecto actual, en lectura |
| `revisar` | Hallazgos con evidencia e impacto | Proyecto actual, en lectura |
| `corregir` | Informe, diff y resultados de pruebas | Copia de trabajo separada de Git (*worktree*) |

Para **corregir**, el repositorio debe estar limpio, sin cambios pendientes. Cuy crea el worktree desde el último commit y ejecuta las pruebas indicadas antes y después de la edición. Puedes repetir `--prueba` para ejecutar varios comandos. Estos se ejecutan con tus permisos, sin shell: no admiten `&&` ni pipes. Las dependencias y archivos ignorados no se copian al worktree; las pruebas deben poder funcionar allí.

El resultado indica:

- **ENTREGADA · por revisar:** terminó el análisis de `entender` o `revisar`.
- **VERIFICADA:** todas las pruebas indicadas pasaron y el informe superó las comprobaciones del flujo. También puede ocurrir sin cambios si la base ya pasaba las pruebas.
- **SIN VERIFICAR:** faltan pruebas o no pasaron. Requiere revisión antes de usar el cambio.

«Verificada» acredita esas pruebas, no la ausencia de errores. Los fallos de ejecución o informes inválidos se muestran como errores.

Los resultados quedan en `~/.local/share/cuy-cli/tareas/<id>/` (`~` representa la carpeta personal del usuario, también en Windows), con el informe `resultado.json`, el patch `cambios.patch` y el worktree cuando corresponde. Revisa el informe y el patch; **aplicar la corrección al proyecto original y eliminar el worktree son pasos manuales**. Sigue la [guía para revisar, aplicar y limpiar una corrección](docs/CORRECCIONES.md). Cuy no crea commits ni publica cambios automáticamente en este flujo.

Consulta las [opciones y comprobaciones de las tareas](docs/REFERENCIA.md#entender-corregir-y-revisar) para salida JSON, tiempos máximos y detalles de verificación.

## Comandos útiles

Desde la carpeta de instalación (o usando la ruta completa al lanzador):

| Comando | Para qué sirve |
|---|---|
| `./cuy` | Abrir la conversación interactiva |
| `./cuy inicio` | Consultar la portada y el estado local |
| `./cuy doctor` | Diagnosticar la instalación sin llamar al modelo |
| `./cuy doctor --verificar` | Añadir una prueba real de conexión, con consumo |
| `./cuy gasto` | Consultar el gasto estimado registrado localmente |
| `./cuy costos` | Revisar las tarifas configuradas |
| `./cuy demo` | Ver un resultado simulado sin llamar al modelo |

En Windows usa `.\cuy.cmd` en lugar de `./cuy`. También puedes ver la [captura de la demo](docs/demo.png) o abrir [la demo HTML](docs/demo.html) localmente.

## Gasto y datos del proyecto

El límite local predeterminado es **USD 10 al mes**. Puedes cambiarlo para la terminal actual:

```bash
# macOS y Linux
CUY_LIMITE_USD=3 ./cuy
```

```powershell
# Windows · PowerShell
$env:CUY_LIMITE_USD="3"
.\cuy.cmd
```

El gasto es una estimación basada en los tokens y las tarifas configuradas. El límite se comprueba entre llamadas: una solicitud en curso puede superarlo y las consultas del instalador no se incluyen. **No sustituye un límite de facturación en Databricks.** Con el tope activo, un modelo sin tarifas conocidas se bloquea. Más información en [costos y contexto](docs/COSTOS-Y-CONTEXTO.md).

Los mensajes y el código que el agente utiliza como contexto se envían al proveedor configurado en Databricks. Cuy incorpora filtros para algunos secretos y un registro local de actividad, pero no detecta todos los datos sensibles ni filtra los secretos que pegues directamente en un mensaje. Los permisos locales tampoco son un sandbox. Consulta el [alcance de la protección y auditoría](docs/REFERENCIA.md#secretos-y-auditoría) si vas a trabajar con información sensible.

## Si algo falla

**Empieza por el diagnóstico:** ejecuta `./cuy doctor` (Windows: `.\cuy.cmd doctor`). Añade `--verificar` si necesitas comprobar una llamada real al modelo.

### Databricks devuelve 401

Comprueba que la URL corresponde al workspace correcto y que el token sigue vigente. Desde la carpeta de Cuy, puedes renovarlo sin escribirlo en el historial:

```bash
python3 instalar.py --renovar-token --host https://TU-WORKSPACE
```

En Windows usa `python`. Si ya tienes `DATABRICKS_TOKEN` exportado en la terminal, tiene prioridad sobre `.env`: actualízalo o elimínalo con `unset DATABRICKS_TOKEN` (macOS/Linux) o `Remove-Item Env:DATABRICKS_TOKEN` (PowerShell) antes de usar la credencial del archivo.

### El ejecutable no arranca o quieres actualizarlo

Para actualizar, primero actualiza tu copia del repositorio. Después, desde la carpeta de Cuy, reinstala el motor correspondiente a tu sistema:

```bash
python3 instalar.py --reparar-motor
```

En Windows usa `python` y abre Cuy con `.\cuy.cmd`. La reparación descarga el ejecutable sin consultar Databricks ni modificar el token o los modelos configurados. Si `python --version` también falla, corrige primero la instalación de Python.

En VS Code Web de Azure Machine Learning, ejecuta la instalación desde la terminal de la instancia Linux. Se descarga el binario de esa instancia, no el de tu computadora.

## Más documentación

El [índice de documentación](docs/README.md) distingue las guías vigentes de las especificaciones y el historial.

- [Configuración](docs/CONFIGURACION.md): variables, precedencia y ubicación de datos.
- [Desarrollo y distribución](docs/DESARROLLO.md): pruebas, releases y traslado al repositorio del equipo.
- [Referencia técnica](docs/REFERENCIA.md): tareas, instalación avanzada, permisos, presupuesto, auditoría y pruebas.
- [Costos y contexto](docs/COSTOS-Y-CONTEXTO.md): tarifas, comparación con consumo real y manejo del historial.
- [Evaluación del agente](evaluacion/README.md): cómo medir correcciones y costos.
- [Plan de evolución](docs/EVOLUCION.md): próximos pasos y propuestas; incluye decisiones históricas.
- [Proceso de especificaciones](docs/SDD.md) y [principios del proyecto](docs/CONSTITUCION.md): proceso para contribuir.
