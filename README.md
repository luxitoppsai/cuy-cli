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

- **Git**, para las operaciones sobre repositorios.
- Un equipo con **Windows, macOS o Linux** (x64 o ARM64).
- La URL de tu workspace de **Databricks** y un token válido con acceso a los endpoints que vas a usar.
- Conexión a tu workspace y al servidor de distribución del ejecutable.

El paquete incluye el lanzador, su runtime y el motor. **No necesitas clonar el repositorio ni instalar Python, Node, npm o Bun.** Las consultas a modelos consumen recursos de Databricks; la configuración también realiza consultas para descubrir y comprobar modelos.

La distribución compilada está preparada para validación local; solicita a tu equipo el paquete aprobado para tu sistema. No confundas la release anterior del motor con el paquete completo.

## Instalación

Descarga el paquete para tu sistema desde el servidor que indique tu equipo y
comprueba su SHA-256 contra el manifiesto proporcionado. En Windows x64, abre el
instalador `.exe` y sigue sus pasos; el acceso «Configurar Cuy» prepara Databricks.
Para macOS/Linux, o si tu equipo entrega el ZIP portable, extrae la carpeta completa
y conserva el ejecutable y `_internal` juntos. Los siguientes comandos corresponden
al paquete portable.

### macOS y Linux

```bash
cd /ruta/al/paquete-extraido
./cuy instalar
```

### Windows · PowerShell

```powershell
cd C:\ruta\al\paquete-extraido
.\cuy.exe instalar
```

El comando muestra la ruta instalada. Usa ese ejecutable para configurar la conexión:

```text
cuy configurar --host https://TU-WORKSPACE
```

Usa su ruta completa, o añade la carpeta del ejecutable al PATH. En PowerShell,
antepone `&` a una ruta entre comillas. La configuración solicita el token de forma
oculta, descubre modelos y comprueba una respuesta. Guarda `.env` y `opencode.json`
en `~/.local/share/cuy-cli`, separados de la aplicación y del proyecto.

Si cambias de workspace, vuelve a ejecutar `cuy configurar` con la URL y credencial correspondientes.

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
& "C:\ruta\a\cuy-cli\cuy.exe"
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

Al abrir una conversación, Cuy prepara automáticamente un **índice local con CodeGraph**.
La primera vez descarga su ejecutable verificado y crea el índice; después comprueba
los cambios y reutiliza los archivos intactos. El agente puede consultar símbolos,
dependencias y llamadas mientras conversas. No necesitas ejecutar un comando especial.
Esto le permite orientarse entre archivos y explorar qué partes podrían verse afectadas
antes de proponer un cambio.

El estado queda en `.cuy/codegraph/` del proyecto y Cuy añade sus exclusiones a
`.gitignore`. Si el índice falla, avisa y continúa con lectura y búsqueda normales.
La primera preparación puede tardar más. Consulta [el índice del repositorio](docs/INDICE-DEL-REPOSITORIO.md)
para conocer qué incluye y sus límites.

## Tareas con un resultado para revisar

Los comandos `tarea` requieren un repositorio Git con al menos un commit. Estos ejemplos parten de la carpeta donde instalaste Cuy; `--proyecto` indica el repositorio de trabajo. En Windows, sustituye `./cuy` por `.\cuy.exe`.

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

En Windows usa `.\cuy.exe` en lugar de `./cuy`. También puedes ver la [captura de la demo](docs/demo.png) o abrir [la demo HTML](docs/demo.html) localmente.

## Gasto y datos del proyecto

El presupuesto mensual local lo define tu equipo en la distribución. Puedes consultar
el consumo y el límite vigente con `cuy gasto`; no se ajusta desde las opciones de uso.

El gasto es una estimación basada en los tokens y las tarifas configuradas. El límite se comprueba entre llamadas: una solicitud en curso puede superarlo y las consultas del instalador no se incluyen. **No sustituye un límite de facturación en Databricks.** Con el tope activo, un modelo sin tarifas conocidas se bloquea. Más información en [costos y contexto](docs/COSTOS-Y-CONTEXTO.md).

Los mensajes y el código que el agente utiliza como contexto se envían al proveedor configurado en Databricks. Cuy incorpora filtros para algunos secretos y un registro local de actividad, pero no detecta todos los datos sensibles ni filtra los secretos que pegues directamente en un mensaje. Los permisos locales tampoco son un sandbox. Consulta el [alcance de la protección y auditoría](docs/REFERENCIA.md#secretos-y-auditoría) si vas a trabajar con información sensible.

## Si algo falla

**Empieza por el diagnóstico:** ejecuta `./cuy doctor` (Windows: `.\cuy.exe doctor`). Añade `--verificar` si necesitas comprobar una llamada real al modelo.

### Databricks devuelve 401

Comprueba que la URL corresponde al workspace correcto y que el token sigue vigente. Desde la carpeta de Cuy, puedes renovarlo sin escribirlo en el historial:

```bash
cuy configurar --renovar-token --host https://TU-WORKSPACE
```

Si ya tienes `DATABRICKS_TOKEN` exportado en la terminal, tiene prioridad sobre `.env`: actualízalo o elimínalo con `unset DATABRICKS_TOKEN` (macOS/Linux) o `Remove-Item Env:DATABRICKS_TOKEN` (PowerShell) antes de usar la credencial del archivo.

### El ejecutable no arranca o quieres actualizarlo

Descarga y extrae el nuevo paquete completo para tu sistema. Desde esa carpeta, ejecuta:

```bash
cuy instalar
```

Usa `./cuy instalar` en macOS/Linux o `.\cuy.exe instalar` en Windows. La reinstalación conserva el token, los modelos configurados y la contabilidad. Si falta `_internal`, vuelve a extraer el paquete completo.

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
