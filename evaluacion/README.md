# Evaluación del agente

El runner usa `tareas.correr_tarea`, verifica pruebas y detecta cambios en archivos
intocables. Cada caso nace en un repositorio Git temporal de un solo commit. Los casos
son código de confianza: las pruebas ejecutan Python localmente, sin sandbox de sistema.

Desde la raíz, validar las bases **sin modelos, tokens ni credenciales**:

```powershell
python evaluar.py --seco
```

La salida esperada del conjunto inicial es `base_roja` en los diez casos. Eso demuestra
que los casos reproducen fallos, no que un agente pueda resolverlos. Un timeout es `error`.

Para una corrida real, con cuycli ya instalado y configurado:

```powershell
python evaluar.py --presupuesto-usd 0.50
```

El presupuesto de evaluación se suma al mensual, sin desactivarlo. Ambos son barreras
locales entre inferencias; la última llamada puede exceder el máximo. No se promete un
corte duro de tokens ni de los 30 pasos configurados. `--limite-segundos 120` limita cada
proceso del motor y cada ejecución de pruebas por separado.

Los informes JSON quedan en `~/.local/share/cuy-cli/evaluaciones/`, fuera del repositorio.
`--salida` admite un archivo nuevo en otra ubicación externa. Se guardan tras cada caso
completado y al interrumpir; no hay reanudación automática. El trabajo temporal se elimina.
Los errores se clasifican sin copiar respuestas del modelo ni credenciales al informe.

Un costo ausente no suma cero: se muestra **total parcial**, con pasos contabilizados y
sin costo; si ninguno tiene costo, el importe es `null`. Una contabilidad incompleta
detiene las siguientes inferencias. Los importes siguen siendo estimaciones locales,
con USD 0,07/DBU de referencia; no constituyen conciliación con la factura.

## Comparar configuraciones

`--config alternativas.json` aplica solo selecciones de modelos, en memoria:

```json
{"model":"cuy/endpoint-descubierto","agent":{"explore":{"model":"cuy/otro-endpoint-descubierto"}}}
```

Los endpoints deben existir en la configuración instalada. El informe registra modelos,
versión del motor y hash del conjunto para comparar JSON de dos corridas. No cambia
`opencode.json`, proveedores, plugins ni permisos. El flujo actual `corregir` no habilita
subagentes: cambiar únicamente `explore` no es un experimento de routing válido todavía.

## Procedencia y límites del conjunto

Cada `caso.json` referencia código histórico del repo. Las funciones y constantes se
extrajeron a módulos mínimos; los tests de contrato se adaptaron a esas extracciones.
Los comentarios y errores de los módulos son deliberadamente históricos. No son código
recomendado para producción. No se incluye la solución ni la historia Git en los casos.

Los diez casos cubren **familias relacionadas**, no diez problemas independientes:
versiones de tarifas, caché, lectura tardía del factor, precios de contexto largo,
identidad exacta del endpoint, ventanas configuradas y copia de permisos. Las tarifas
son las del contrato de la prueba, no una nueva consulta de precios del proveedor.

El conjunto sirve para iniciar una medición de regresiones. No mide generalización ni
sustituye casos representativos del equipo; al ser público puede estar memorizado.
`--casos` acepta una carpeta privada con la misma estructura, sin publicarla.

Validación entregada: bases rojas, motor simulado, Git/worktree y pruebas reales locales.
**Pendiente:** baseline con Databricks y comparación real entre configuraciones.

## Enmienda de revisión cruzada

Los manifiestos requieren `grupo` explícito (`tarifas`, `contexto` y `permisos` en el
conjunto incluido). Dos objetivos describen síntomas; siguen siendo diez casos.
Cada informe contiene todos los casos previstos, incluidos `no_ejecutado`, y las cinco
métricas por grupo. No ejecutados y fallos de preparación no integran el denominador de
resolución. Se muestran sus conteos aparte. Las duraciones agregan los casos iniciados.

Una preparación fallida antes de intentar el motor acredita cero costo de modelo y puede
continuar si la causa es local. Disco lleno, configuración global inválida y causas no
clasificables detienen la corrida. Un intento de motor sin contabilidad completa corta
con total parcial. Cero acreditado y costo desconocido (`null`) son estados diferentes.
El importe conocido se conserva aunque falle la inspección del worktree.

El informe incluye fase, código de motivo y límite de pasos efectivo informado por tareas.
Modificar el texto humano no cambia la clasificación. Raíz imposible de inspeccionar es
error; un intocable comprobablemente borrado es modificación, aun si el motor luego falla.

La primera comparación se limita al modelo principal. Es exploratoria, no una demostración
de superioridad. No comparar agregados de conjuntos distintos como si solo cambiara el
modelo. Un hash null indica que no se inspeccionó el conjunto completo. El baseline real
con Databricks sigue pendiente; ningún test simulado lo sustituye.

Si falla el almacenamiento del informe, solo se conserva la última escritura exitosa.
Los errores de infraestructura no se presentan como una colección de fallos del agente.
