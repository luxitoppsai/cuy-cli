# Evolución: utilidad, eficiencia y gobierno

Fecha: 2026-09-24. Estado: los tres flujos del punto 1 están implementados y probados
contra un proveedor sintético. El piloto real y las etapas posteriores siguen propuestos.

## Qué se busca

Un desarrollador debe poder resolver una tarea verificable en su repositorio con pocas
interrupciones, un costo comprensible y permisos que el equipo pueda explicar. La métrica
principal será **costo por tarea correctamente resuelta**, acompañada de tiempo e
intervenciones humanas. Tokens baratos o más agentes no equivalen a productividad.

## Base implementada en esta revisión

- Configuración del producto independiente del proyecto actual, con plugins fuente y
  política de Cuy aplicada al iniciar.
- `plan`/`explore` de lectura, shell sujeto a autorización, pasos acotados y retiro de
  `scout`; planificación con el modelo capaz.
- Sondeos fallidos excluidos; descubrimiento compartido; verificación del contrato
  seleccionado, incluido Anthropic nativo.
- Presupuesto antes de inferencia, contabilidad atómica concurrente y eventos deduplicados;
  costo desconocido bloqueado con tope activo.
- Auditoría de intentos/resultados y permisos con IDs reales; redacción antes de persistir.
- Instalación predeterminada por lockfile, release opcional con versión/hash y diagnóstico.
- Pruebas del motor con proveedor sintético; CI declarada para tres sistemas.

No se implementó un límite financiero distribuido, sandbox, control inmutable de políticas,
OAuth, trazabilidad central ni evaluación de calidad con los modelos reales.

## 1. Hacerlo útil: completar tareas y facilitar su revisión

**Primero un piloto pequeño:** dos desarrolladores, un repositorio representativo y tareas
que hoy hagan manualmente. No empezar extendiendo compatibilidad a todas las familias.

Implementados tres flujos explícitos mediante `cuy tarea`, con criterios de cierre:

| Flujo | Entregable | Cierre verificable |
|---|---|---|
| Entender | Mapa del módulo y referencias a archivos | Respuestas correctas a preguntas previamente conocidas; cero cambios |
| Corregir | Diff pequeño, pruebas relevantes y explicación | Test que fallaba pasa, regresiones pasan, sin archivos ajenos a la tarea |
| Revisar | Hallazgos con ubicación y reproducción | Hallazgos reproducibles; no modificar el trabajo del autor |

`cuy tarea corregir` ya crea un worktree desde HEAD y requiere un árbol limpio para no
excluir silenciosamente trabajo pendiente. Conserva la base, exporta un patch sin staging,
y ejecuta pruebas elegidas antes y después. Entender/revisar trabajan en lectura sobre el
estado actual y validan referencias. No auto-commitea, publica ni reanuda.

La interfaz incluye `cuy inicio`, resultados con estados explícitos y `cuy demo`. La vista
HTML en `docs/demo.html` muestra datos simulados usando el mismo renderizador de terminal.

Pendiente en este punto: piloto real, soporte de proyectos sin Git y recuperación explícita
de tareas interrumpidas. El aislamiento del worktree no es un sandbox del sistema.

**Aceptación:** una persona nueva puede instalar, diagnosticar y completar una corrección
sin editar JSON ni interpretar logs internos. No basta con un saludo exitoso al modelo.

## 2. Medir antes de optimizar

Crear un benchmark versionado de 12 casos con repositorios mínimos y tests privados al
agente cuando se mida generalización:

1. Corregir límites inclusivos/exclusivos de rangos.
2. Reparar manejo de `None` sin cambiar el contrato público.
3. Actualizar firma y llamadas en varios archivos.
4. Resolver una regresión de serialización Unicode.
5. Corregir lectura de fechas y zonas horarias.
6. Agregar validación con compatibilidad hacia atrás.
7. Diagnosticar un test fallido antes de cambiar código.
8. Recuperarse de una herramienta que devuelve error.
9. Respetar archivos fuera de alcance y cambios previos del usuario.
10. Redactar secretos sintéticos sin romper el código de contexto.
11. Detenerse ante un error de autenticación o presupuesto agotado.
12. Sesión larga con corrección de un supuesto y recuperación de contexto.

Guardar por intento: versión de Cuy/motor, modelo y endpoint, política, resultado de tests,
archivos modificados, número de turnos, tokens, costo estimado/servidor, latencia y permisos
consultados. Los prompts y contenidos no se exportan por defecto. Separar fallos de modelo,
contrato, herramientas, política y entorno; no atribuir un cuelgue a entrenamiento sin aislarlo.

Ejecutar al menos tres repeticiones por caso y configuración. Comparar baseline con una sola
variable a la vez. El proveedor sintético verifica integración; este benchmark mide calidad.

## 3. Ganar eficiencia sin perder calidad

| Cambio candidato | Evidencia requerida antes de activarlo |
|---|---|
| Modelo económico para explorar | Mismo éxito en localización y comprensión, menor costo total |
| Cambio a modelo capaz tras fallo | Más tareas resueltas que reintentar indefinidamente; máximo de intentos explícito |
| Caché de descubrimiento por host/modelo/versión | Menos llamadas al instalar, invalidación visible al cambiar endpoint |
| Contexto selectivo y resúmenes de exploración | Menos tokens sin perder restricciones, rutas o decisiones importantes |
| Caché de prompts del proveedor | Hits medidos con métricas reales, ahorro conciliado con facturación |
| Límite por tarea además del mensual | Detención reproducible, presupuesto visible y recuperación de trabajo |

No rutear únicamente por parámetros ni lexicografía del nombre. Una tabla declarativa y
versionada debe separar capacidades verificadas, contexto, tarifas, preferencias y su fecha
fuente. Una tarifa ausente debe mostrarse como desconocida. Los errores 401/403 y contrato
inválido no merecen la misma política de reintentos que 429 o fallos transitorios.

## 4. Gobierno: distinguir ayuda local de control corporativo

| Capa | Responsabilidad | Garantía |
|---|---|---|
| Cuy local | UX de permisos, redacción, estimación y diagnóstico | Protege contra accidentes; el usuario puede modificarla |
| Política distribuida por la empresa | Versiones aprobadas, modelos, herramientas, conectores y perfiles | Requiere distribución confiable y verificación; no basta un archivo en el repo |
| Identidad y Gateway | Identidad autenticada, cuotas, presupuestos y registro central | Aplicación independiente del proceso local, según capacidades del workspace |
| Entorno de ejecución | Red permitida, aislamiento del sistema y acceso a credenciales | Sandbox/firewall administrados; patrones de shell no los sustituyen |

Siguientes decisiones con el administrador del entorno:

- Sustituir PAT manual cuando sea viable por autenticación corporativa de corta duración.
- Elegir los servicios/modelos aprobados; definir cuotas y corte del lado del servidor.
- Conciliar estimación local con consumo del servidor y su retraso de actualización.
- Identificar cada tarea con usuario, proyecto y sesión sin adjuntar código a los tags.
- Definir acceso, retención y contenido de auditoría central; no enviar prompts íntegros
  por comodidad. Los comandos también pueden contener información confidencial.
- Distribuir una política con versión/hash y perfiles `interactivo`, `lectura` y `CI`.
  En CI, permisos deterministas allow/deny y comandos de prueba explícitamente aprobados.
- Aprobar plugins/MCP por versión y procedencia; controlar también los globales de OpenCode.
- Mantener releases revisables, checksums confiables, rollback y prueba del binario exacto.

Databricks documenta presupuestos y seguimiento del Gateway, pero su disponibilidad y
cobertura deben verificarse para el servicio, región y contrato concretos:
[budgets](https://docs.databricks.com/aws/en/admin/account-settings/budgets),
[governance de endpoints](https://docs.databricks.com/aws/en/ai-gateway/overview-serving-endpoints).
No se asume que una función del Gateway ya esté activada en este workspace.

## Orden recomendado y puerta de salida

1. **Validar esta base** con el motor exacto y un piloto real de leer–editar–probar.
2. **Instrumentar el benchmark** y fijar el baseline de éxito/costo/tiempo.
3. **Resolver identidad, políticas y gasto en servidor** antes de ampliar el equipo.
4. **Empaquetar mejor la distribución** (comando instalable, actualización/rollback) y mejorar
   los tres flujos según los resultados del piloto.
5. **Optimizar routing y contexto** contra el benchmark, manteniendo regresiones visibles.

Posponer memoria persistente, RAG, más subagentes y un fork más profundo. Se incorporan
solo cuando un fallo medido justifique su costo operativo.
