# Referencia técnica de cuy-cli

Detalles de los flujos, permisos, registros y comprobaciones para quienes necesitan
configurar o mantener la herramienta. Para instalarla y empezar, consulta el
[README](../README.md). Los comandos de esta página parten de la raíz de cuy-cli,
salvo que se indique otra carpeta. Las rutas de ejemplo son sustituibles; `~` significa
la carpeta personal del usuario en cada sistema. Consulta [configuración](CONFIGURACION.md)
para cambiar las ubicaciones de datos.

Las conversaciones locales incorporan también un [índice de CodeGraph](INDICE-DEL-REPOSITORIO.md)
con consultas de lectura. El lanzador comprueba sus fuentes al arrancar y antes de cada
consulta; las tareas explícitas descritas abajo conservan su ejecución sin ese índice.

## Entender, corregir y revisar

```bash
./cuy inicio                          # portada y estado local
./cuy tarea entender "Explicá el recorrido de un pedido"
./cuy tarea revisar "Buscá regresiones en src/stock.py"
./cuy tarea corregir "Corregí el límite de reserva" --prueba "python -m unittest tests.test_stock"
./cuy demo                            # resultado de ejemplo, sin inferencia
```

En Windows se usa `cuy.exe` en el paquete compilado. Los tres flujos requieren un repositorio Git con un commit.
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

Un cambio solo aparece **VERIFICADA** si se entregó el informe requerido y
todas las pruebas elegidas terminaron con código 0 sin timeout, sin cambios inesperados.
También puede verificarse una base sin cambios si sus pruebas ya pasaban antes de la tarea. No significa ausencia de
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
manuales; la [guía de correcciones](CORRECCIONES.md) explica esos pasos. No hay auto-commit, auto-publicación ni reanudación automática tras interrupción.

### Vista visual

[Demo interactiva local](demo.html) · [captura renderizada](demo.png).
Los ejemplos son simulados y usan el mismo renderizador de resultados que las tareas reales.

```bash
./cuy demo --flujo entender
./cuy demo --flujo revisar
./cuy demo --flujo pendiente
./cuy demo --html cuy-demo.html
```

La demo no llama al modelo. La terminal adapta el ancho y desactiva colores al redirigir
salida o definir `NO_COLOR`. La página tiene pestañas navegables por teclado y permite
inspeccionar los estados sin ejecutar tareas.

## Origen y actualización del motor

El paquete completo incorpora el motor y su runtime. Se instala con el instalador
Windows o con `cuy instalar` desde el paquete portable; se actualiza descargando la
nueva distribución del equipo. No requiere clonar fuentes ni instalar Python.
Las opciones siguientes corresponden al instalador anterior usado desde fuentes.

- **Predeterminado:** descarga el binario de **cuycli** publicado para tu sistema,
  fijado por `release.json`, y verifica su SHA-256 antes de instalarlo.
- En la computadora de trabajo solo hace falta Python: **no Bun, npm ni compilación**.
- `--reparar-motor` vuelve a descargar el binario sin consultar Databricks.
- `--compilar` es una opción explícita para desarrollo, en el equipo que tiene Bun.
- `python3 instalar.py --binario-manifiesto release.json`: selecciona versión y hashes
  desde un manifiesto local revisado. El manifiesto no cambia el servidor de descarga:
  este se define en `RELEASE` dentro de `instalar.py`. Consulta [distribución](DESARROLLO.md#distribuir-desde-el-repositorio-del-equipo). Exige `version` y un mapa `sha256` por nombre
  de artefacto (`cuy-darwin-arm64`, `cuy-windows-x64.exe`, etc.). No acepta `latest`.

### VS Code Web en Azure Machine Learning

Las instancias de cómputo Linux x86-64 usan el artefacto `cuy-linux-x64` de la versión
fijada en `release.json` al usar el instalador anterior desde fuentes. Para el paquete
compilado, instala la distribución Linux desde la terminal de la instancia. Su
arquitectura corresponde a la instancia, no a tu computadora. El procedimiento
anterior desde fuentes es:

```sh
python3 instalar.py --reparar-motor
./cuy
```

El instalador descarga el binario, verifica su SHA-256 y no necesita Bun ni npm. Si solo
querés comprobar el artefacto sin volver a configurar el workspace:

```sh
python3 instalar.py --reparar-motor --sin-compilar
```

La arquitectura esperada es `x86_64`; en una instancia ARM corresponde `cuy-linux-arm64`.
El binario es nativo de Linux y no se puede ejecutar desde macOS para probarlo localmente.

Las descargas se validan antes de reemplazar el ejecutable. No se publica un manifiesto
con hashes inventados: quien construye la release debe producirlo y revisarlo. Un hash
comprueba integridad respecto del manifiesto; no sustituye su procedencia confiable.

La selección instalada queda en `bin/seleccion.json`, evitando que una descarga antigua
oculte una compilación o instalación posterior. Las instalaciones anteriores mantienen
su selección por compatibilidad hasta reinstalar.

El fuente vendorizado y un binario pueden diferir. Ejecutá las pruebas del motor real
antes de aprobar una actualización. Al actualizar el motor, repetí también la auditoría de red. La observación histórica en [spike/RED.md](../spike/RED.md) solo describe
la versión y los escenarios allí medidos.

En redes corporativas con certificados propios, configurá `NODE_EXTRA_CA_CERTS`. El
build intenta exportar raíces del sistema en Windows. No desactives la validación TLS.

## Agentes y permisos

| Rol | Modelo inicial | Herramientas |
|---|---|---|
| `build` | Preferencia Sonnet; respaldo por nombre/tamaño estimado | Edición habilitada, shell sujeto a política; 30 pasos configurados |
| `plan` | El mismo modelo capaz que `build` | Lectura y búsqueda; sin shell, edición ni delegación; 15 pasos configurados |
| `explore` | Preferencia Haiku; respaldo económico estimado | Subagente de lectura y búsqueda; 15 pasos configurados |

El número de pasos configurado orienta al motor, pero no garantiza un corte estricto.
No debe usarse como límite de gasto ni de duración; véase [RFC-003, señal del límite](rfc/RFC-003-evaluacion-del-agente.md#46-señal-del-límite-de-pasos).

`scout` se retiró porque duplicaba `explore` y no tenía restricciones propias.
La selección por nombre es una heurística: no constituye una evaluación de capacidad.
Los límites de contexto son valores operativos configurados y las tarifas tienen un alcance declarado; no son
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
cuy gasto
```

El plugin comprueba el gasto mensual en `chat.params`, **antes de cada inferencia que
pasa por ese hook**, además de impedir nuevas herramientas al alcanzar el límite. Relee
el archivo en cada comprobación, por lo que detecta cambios de mes y gasto de otras
sesiones. Cuenta eventos `step-finish` una sola vez por identificador.

La persistencia usa lock entre procesos y reemplazo atómico. Un archivo corrupto o un
fallo contable bloquea la siguiente inferencia; no se interpreta como cero. Un lock
huérfano tras un cierre abrupto requiere revisar procesos activos antes de retirarlo.
El archivo está en `~/.local/share/cuy-cli/gasto.json`. El paquete fija la ruta;
la opción de ruta alternativa se conserva para desarrollo desde fuentes.

Con tope activo, un modelo sin tarifas positivas `cost.input`/`cost.output` se rechaza.
**Costo desconocido no significa gratis.** Se pueden declarar tarifas del contrato en
el modelo de `opencode.json`; `CUY_USD_POR_DBU` ajusta la conversión al regenerar.
El importe mensual se incorpora a la distribución; no se modifica ni desactiva
con variables de ejecución. Los plugins de Cuy van incorporados al nuevo motor y
se cargan aunque se deshabiliten los plugins opcionales. No dependen de JavaScript
editable en el paquete. Véase [RFC-006](rfc/RFC-006-distribucion-compilada.md).

Es una **estimación local**, no un límite de facturación estricto: una petición iniciada
antes del corte puede exceder el saldo y varias peticiones simultáneas pueden estar en
vuelo. No reserva costo por anticipado, no cancela otras sesiones ni incluye llamadas
hechas fuera del motor, como sondeos de instalación. Los precios, descuentos y tokens de
caché deben contrastarse con el contrato y consumo del servidor. El límite corporativo
pertenece al Gateway, fuera del control del usuario local.

## Secretos y auditoría

### Protección de ediciones en desarrollo

La primera etapa del [RFC-005](rfc/RFC-005-robustez-del-agente.md) añade al fuente
del motor una comparación SHA-256 de los bytes usados para preparar `write`, `edit`
y `apply_patch`, después de la aprobación y antes de escribir. Si cambian, la
herramienta falla y pide releer. Un parche comprueba todos los archivos antes de la
primera modificación; los movimientos requieren permiso para origen y destino.
Las altas y destinos de movimientos no pueden sobrescribir archivos existentes.
Para modificar un archivo existente se utiliza una actualización o reemplazo explícito.

Esto todavía no compara con una lectura anterior de la conversación ni protege el
undo existente. Tampoco cubre escrituras hechas por shell, MCP o formateadores.
La comprobación deja una ventana antes de escribir y no convierte un parche en una
transacción atómica. Estas mejoras requieren un motor compilado con el cambio;
no se incorporan a la release 0.4.3 mediante una actualización de Python.

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
[docs/EVOLUCION.md](EVOLUCION.md).

## Pruebas

Requisitos de desarrollo y preparación del entorno en [DESARROLLO.md](DESARROLLO.md).

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

Los RFC y spikes conservan decisiones e hipótesis históricas.
