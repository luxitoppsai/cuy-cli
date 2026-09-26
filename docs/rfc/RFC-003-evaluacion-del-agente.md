---
rfc: RFC-003
titulo: Evaluación del agente — medir si la herramienta sirve
estado: aceptado
fecha: 2026-09-25
proyecto: cuy-cli
constitucion: 1.0.0
---

# RFC-003 — Evaluación del agente

> **Estado: aceptado por el dueño el 2026-09-25.** Implementación por hitos; las corridas reales se reportan separadas de los tests simulados.

## 1. Contexto y problema

El proyecto tiene 141 pruebas y ninguna mide el producto.

Todas validan la plomería: que la configuración se arme bien, que el presupuesto sume, que
los secretos se redacten, que los hooks existan. Ninguna responde la pregunta por la que se
construyó la herramienta: **¿resuelve las tareas que se le piden?**

Hoy no se puede contestar nada de esto:

- ¿Qué porcentaje de tareas termina en `verificada`?
- ¿Cuánto cuesta una tarea típica?
- ¿Haiku en `explore` pierde algo frente a Sonnet, o ahorra gratis?
- ¿El passthrough nativo de Anthropic rinde mejor que el contrato OpenAI, como sostiene
  RFC-001, o es solo más prolijo?
- Cuando falla, ¿por qué? ¿Se queda sin pasos, edita el archivo equivocado, se rinde?

Sin eso, cada mejora futura —mejor prompt, mejor contexto, otro modelo— es una opinión. Se
puede cambiar algo y *creer* que mejoró. **Es el hueco más grande que tiene el proyecto**, y
crece: cuanto más código haya encima, más caro es empezar a medir.

### La ventaja que ya existe

`cuy tarea corregir --prueba "..."` produce una señal **binaria y automática**: el informe
termina en `estado: "verificada"` solo si todas las pruebas declaradas pasaron. La mayoría
de las evaluaciones de agentes son un problema en sí mismas —hay que leer salidas, usar un
modelo juez, discutir criterios—. Esta **se califica sola**.

Este RFC existe para aprovechar eso antes de construir nada más.

## 2. Objetivo

Poder correr un comando y obtener tres números comparables entre corridas:

```
$ python evaluar.py --presupuesto-usd 1
10 casos · sonnet-4-5 · 2026-09-25T14:02

  resueltos      7/10  (70%)
  costo total    $0.84   (mediana por caso $0.07)
  duración       8m 12s  (mediana por caso 41s)

  fallidos:
    T004  sin_verificar   la prueba sigue en rojo
    T007  sin_pasos       agotó los 30 pasos
    T009  test_modificado el agente tocó el archivo de prueba
```

Está hecho cuando un cambio en el prompt, el modelo o el contexto se puede defender con la
diferencia entre dos corridas en vez de con una impresión.

## 3. Alcance

**Dentro**

- Un conjunto de casos versionado en el repo, reproducible sin red más allá del modelo.
- Un runner que corre los casos, recoge métricas y escribe un informe comparable.
- Clasificación del motivo de fallo.
- Poder correr el mismo conjunto con otra configuración de modelos, para comparar.
- Una guardia de gasto propia, porque evaluar consume tokens de verdad.

**Fuera (no-objetivos)**

- Integración con CI. Primero hay que saber cuánto cuesta y cuánto tarda una corrida.
- Panel web o cualquier visualización. La salida es texto y JSON.
- Modelo juez para calificar calidad. Se evalúa lo que se puede calificar solo; lo demás
  no se evalúa todavía.
- Estadística sobre repeticiones. Se registra la variación observada, no se modela.
- Evaluar los flujos `entender` y `revisar`. No tienen señal automática — se apoyan en
  juicio humano. Entran cuando haya con qué calificarlos.

## 4. Propuesta

### 4.1 Qué es un caso

Una carpeta con el estado **anterior** a un arreglo, la prueba que lo detecta, y el
objetivo en lenguaje natural.

```
evaluacion/casos/004-limite-por-modelo/
  caso.json          objetivo, comando de prueba, archivos intocables
  proyecto/          los archivos tal como estaban antes del arreglo
```

`caso.json`:

```json
{
  "objetivo": "El tope de salida se lee del primer endpoint y se aplica a todos. Cada modelo tiene el suyo.",
  "prueba": ["python", "-m", "unittest", "test_limite.py"],
  "intocables": ["test_limite.py"],
  "referencia": "commit a1b2c3d de cuy-cli"
}
```

### 4.2 Cómo se construye un caso — y por qué así

Se parte de un arreglo real que vino con su prueba: se toma el estado previo, se conserva
la prueba, y el agente tiene que volver a ponerla en verde.

**Cada caso se materializa como un repositorio git nuevo con un único commit.** Esto no es
un detalle de implementación: si se usara el repositorio original en un commit anterior, el
arreglo seguiría estando en el almacén de objetos y el agente —que tiene `bash`— podría
encontrarlo con `git log --all -p`. Un caso así no mide nada. El repo de un solo commit
elimina la fuga por construcción (**P6**, fallar cerrado).

### 4.3 Cómo se califica

| Resultado | Cuándo |
|---|---|
| `resuelto` | `estado: "verificada"` **y** ningún archivo intocable modificado |
| `sin_verificar` | El agente terminó pero la prueba sigue en rojo |
| `test_modificado` | La prueba pasa porque el agente la cambió |
| `sin_pasos` | Reservado para una señal explícita del motor de detención por límite; contar pasos no basta |
| `sin_cambios` | Terminó sin tocar ningún archivo |
| `error` | Fallo de preparación, motor o inspección; fase y código distinguen la causa sin atribuir infraestructura al modelo |
| `no_ejecutado` | Caso previsto que no se inició; excluido del denominador de resolución |

**`test_modificado` es la categoría que más importa.** Un agente al que se le pide poner
una prueba en verde tiene un atajo evidente: borrarla, vaciarla, o hacer que la aserción sea
trivial. Si el arnés no lo detecta, la tasa de resolución mide la capacidad de hacer trampa,
no la de arreglar. Se comprueba comparando el hash de cada archivo intocable antes y
después; `foto()` en `tareas.py` ya calcula exactamente eso.

### 4.4 Métricas

Por corrida: **tasa de resolución**, **costo total y mediana por caso**, **duración total y
mediana**. Por caso: resultado, costo, duración, pasos, archivos tocados.

Se usa mediana y no promedio: un caso que se va de tiempo distorsiona el promedio y esconde
el comportamiento típico.

Cada informe registra la configuración que lo produjo —modelos por rol, versión del
binario, fecha— porque un número sin su configuración no se puede comparar con nada.

### 4.5 Presupuesto y costos parciales

Decisiones acordadas con el dueño el 2026-09-25:

- La corrida real exige un presupuesto máximo explícito en USD; no se intenta adivinar
  su costo previo. Se mantiene USD 0,07/DBU como conversión de referencia, no contractual.
- El presupuesto de evaluación se aplica además del mensual, sin desactivarlo. Se
  comprueba entre llamadas al modelo: no es un techo duro, porque la llamada en curso
  puede excederlo. Al alcanzar cualquiera de los dos se conserva el informe parcial.
- Si falta el costo de algún paso, el importe conocido se presenta como **total parcial**,
  con cantidad de pasos contabilizados y sin costo. Si ninguno tiene costo válido,
  el importe es `null`, no cero. No se publica una mediana completa con datos incompletos.
- Ante contabilidad incompleta se conserva el resultado y se detienen nuevas inferencias
  de evaluación: un subtotal conocido no permite garantizar el presupuesto restante.

### 4.6 Señal del límite de pasos

Revisión del motor integrado: `session/prompt.ts` calcula `isLastStep = step >= maxSteps`
y agrega `MAX_STEPS_PROMPT` al mensaje. Ese punto no publica un motivo estructurado de
agotamiento ni impone por sí mismo un corte del bucle. El evento `step_finish` expone el
motivo de finalización del modelo; no acredita que el motor haya detenido la tarea por
su límite de pasos. Un motivo `length` tampoco significa agotamiento de pasos.

Por ahora, registrar pasos observados y límite configurado; no inferir `sin_pasos` de
alcanzar 30 ni de que el modelo diga que agotó sus pasos. Una tarea inconclusa conserva
la categoría observable (`sin_verificar` o `error`, según corresponda). La categoría
`sin_pasos` queda reservada hasta disponer de un corte efectivo con motivo estructurado
comprobado mediante un test de integración. No se amplía este RFC con un cambio del motor.

### 4.7 Estructura

```
evaluacion/
  casos/NNN-slug/{caso.json,proyecto/}
evaluar.py
# Fuera del repositorio:
~/.local/share/cuy-cli/evaluaciones/ID.json
```

`evaluar.py` reutiliza `tareas.correr_tarea`: evaluar es correr el producto, no una versión
paralela de él. Si el runner se desviara del camino real, mediría otra cosa.

## 5. Alternativas consideradas

**No hacer nada.** Seguir mejorando a ojo. Descartada: es la situación actual y el motivo
del RFC.

**Usar SWE-bench u otro conjunto público.** Da comparabilidad con la industria, pero mide
repositorios Python de gran escala que no se parecen al trabajo real del equipo, cuesta
mucho más por corrida, y buena parte está en el entrenamiento de los modelos. Se descarta
por ahora; nada impide agregarlo después.

**Modelo juez para calificar la calidad del arreglo.** Es la forma de evaluar `entender` y
`revisar`. Se descarta en esta etapa porque agrega una fuente de error —hay que evaluar al
juez— antes de tener funcionando lo que se califica solo.

**Casos sintéticos escritos a mano.** Más rápido de producir, pero se termina midiendo
contra bugs que uno inventó pensando en cómo fallan los agentes. Los casos salen de
arreglos reales.

## 6. ¿Agente LLM? (LangChain/LangGraph)

**No.** El runner es un bucle sobre una lista de casos que invoca un subproceso y compara
hashes. No hay orquestación, ni estado, ni ramas. Python pelado con la biblioteca estándar,
como el resto del repo (**P9**).

## 7. Requisitos funcionales

| ID | Requisito |
|---|---|
| RF-001 | El runner **debe** materializar cada caso como un repositorio git nuevo con un único commit, sin historia previa. |
| RF-002 | El runner **debe** ejecutar cada caso a través de `tareas.correr_tarea`, el mismo camino que usa una persona. |
| RF-003 | El runner **debe** marcar `test_modificado` cuando un archivo declarado intocable cambió, aunque las pruebas pasen. |
| RF-004 | El runner **debe** clasificar cada caso en exactamente una de las categorías de §4.3. |
| RF-005 | El informe **debe** registrar la configuración que lo produjo: modelo por rol, versión del binario y fecha. |
| RF-006 | El informe **debe** reportar tasa de resolución, costo total, costo mediano, duración total y duración mediana. |
| RF-007 | El runner **debe** aceptar una configuración de modelos alternativa para comparar sin tocar la del usuario. |
| RF-008 | Una corrida real **debe** exigir un presupuesto máximo explícito, adicional al mensual, y comprobarlo entre inferencias; debe advertir que una llamada en curso puede excederlo. |
| RF-009 | El runner **debe** detenerse si el presupuesto mensual se agota a mitad de la corrida, dejando el informe parcial escrito. |
| RF-010 | Un fallo de caso con contabilidad completa, o local de preparación demostrado antes de intentar el motor, **no debe** interrumpir los demás casos. Fallos globales o de causa no clasificable detienen la corrida; no se atribuyen al modelo. |
| RF-011 | El runner **no debe** dejar residuos en el repositorio del usuario ni en su `opencode.json`. |
| RF-012 | El informe **debe** conservar costos conocidos aun si falla la inspección. Sin costos acreditados usa `null`; antes de intentar el motor puede acreditar cero. Un intento iniciado o incierto con contabilidad incompleta detiene nuevas inferencias y muestra total parcial, también por grupo. |
| RF-013 | El runner **no debe** clasificar `sin_pasos` sin una señal estructurada de corte efectivo del motor; debe registrar pasos observados y límite configurado. |
| RF-014 | Cada caso **debe** declarar grupo. El informe **debe** incluir las cinco métricas por grupo y total; grupos con costos desconocidos muestran total parcial. |
| RF-015 | Los casos no iniciados **deben** figurar como `no_ejecutado`, fuera del denominador de resolución; errores de preparación se identifican y no cuentan como fallos del modelo. |
| RF-016 | `tareas.py` **debe** informar fase, código de motivo y límite efectivo. La clasificación no depende del texto humano; comparación de integridad imposible produce error, modificación comprobada prevalece aun ante error del motor. |

## 8. Criterios de aceptación

| ID | Criterio |
|---|---|
| CA-001 | Con diez casos versionados, `python evaluar.py --presupuesto-usd 1` produce un informe con las cinco métricas de RF-006. |
| CA-002 | Un caso cuyo proyecto ya viene arreglado se clasifica `resuelto`; uno imposible, `sin_verificar`. |
| CA-003 | Un agente simulado que borra el archivo de prueba se clasifica `test_modificado`, no `resuelto`. |
| CA-004 | El repositorio de un caso materializado no contiene el arreglo en ninguna parte de su historia. |
| CA-005 | Dos corridas con configuraciones distintas producen informes comparables campo a campo. |
| CA-006 | Una corrida interrumpida deja un informe parcial válido con los casos ya completados. |
| CA-007 | Después de una corrida, `git status` del repositorio del usuario no muestra cambios. |
| CA-008 | Sin presupuesto explícito, una corrida real no inicia inferencias; al alcanzar el presupuesto de corrida o mensual no inicia la siguiente y conserva un informe parcial. |
| CA-009 | Con un paso de costo válido y otro ausente, el informe muestra total parcial y ambos conteos; con todos ausentes muestra importe `null`; no inicia nuevas inferencias. |
| CA-010 | Alcanzar 30 pasos, recibir `length` o leer una afirmación del modelo no produce por sí solo `sin_pasos`. |
| CA-011 | Fallo local de manifiesto/copia previo al motor continúa con cero acreditado; lanzamiento incierto sin contabilidad corta; presupuesto/configuración global bloquean nuevos casos. |
| CA-012 | Un fallo de infraestructura o causa no clasificable detiene la corrida; los restantes figuran no ejecutados y no se atribuyen al modelo. Si falla persistencia solo se garantiza el último informe guardado. |
| CA-013 | Grupos explícitos reportan agregados correctos: costos ausentes → `null`, ceros acreditados → cero, mezcla → total parcial sin mediana completa. |
| CA-014 | Raíz inválida no se clasifica como modificación; borrar un intocable dentro de raíz válida sí, incluso seguido de error. |
| CA-015 | Cambiar el mensaje humano no altera `sin_cambios`; código de motivo y límite provienen del flujo real de tareas. |
| CA-016 | Presupuesto de evaluación inválido permite construir el plugin pero bloquea en el hook antes de invocar al proveedor. |

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| **El agente hace trampa con la prueba** | RF-003 y CA-003. Es el riesgo principal: sin esto la métrica mide lo contrario de lo que dice. |
| **Contaminación**: los casos salen de un repo público que el modelo pudo ver | Se documenta como límite. El repo de un solo commit evita la fuga por `git`, no la memorización. Los casos de repos privados del trabajo son más confiables y no se versionan acá. |
| **Muestra chica**: diez casos dan mucho ruido | Se reporta el número absoluto además del porcentaje —"7/10", no "70%"— para no sugerir precisión que no hay. El conjunto crece con casos reales. |
| **Evaluar cuesta plata** | RF-008 y RF-009. Se exige máximo explícito por corrida además del mensual; no se presume un costo previo. |
| **No determinismo del modelo** | Se registra la variación entre corridas de la misma configuración. No se promete reproducibilidad exacta. |
| **El conjunto se vuelve el objetivo** | Diez casos no son el producto. Se revisa el conjunto cuando la tasa supere el 80%: a esa altura mide poco. |

## 10. Plan de entrega

| Hito | Contenido | Demostrable |
|---|---|---|
| **H1** | Materialización de casos y clasificación, con tres casos | `evaluar.py --seco` valida bases sin inferencia; clasificación probada con motor simulado |
| **H2** | Corrida real y informe | El comando de §2 sobre tres casos |
| **H3** | Diez casos derivados de arreglos reales | Primera cifra de referencia del proyecto |
| **H4** | Comparación entre configuraciones | Comparar el modelo principal con idéntico conjunto y parámetros efectivos |

H1 es MVP: clasificar bien sin gastar es lo que hace confiable todo lo demás.

## 11. Decisiones y preguntas pendientes

1. **Procedencia decidida:** diez extracciones históricas versionadas y `--casos` para un
   conjunto privado. **Pendiente:** representatividad y contaminación por disponibilidad
   pública; el primer baseline real aún no existe.
2. **Pasos:** se registra el límite efectivo que informa `tareas.py`. Hoy configura 30,
   sin prometer un corte duro. **Pendiente:** medir el efecto del límite en resultados.
3. **Presupuesto decidido:** máximo de corrida además del mensual, ambos activos.
4. **Comparación inicial decidida:** modelo principal, mismo conjunto y parámetros efectivos.
   **Pendiente:** evaluar subagentes requiere un flujo que delegue y queda fuera de esta enmienda.

## Revisiones

### Enmienda 1 — 2026-09-25

Procedimiento acordado: `en-revision` si la enmienda espera aceptación. En este caso,
**el dueño autorizó aplicar el alcance acordado («hazlo») tras el cierre bilateral en
REVISION.md, antes de editar esta enmienda**. Se mantiene `aceptado` con este registro
explícito; la aceptación original por sí sola no autorizaba el texto nuevo.
Base histórica: HEAD `aec0ffc` (RFC original) y primera implementación aún no commiteada.

Se aclaran fases y contabilidad (RF-010/RF-012), integridad, motivos estructurados y
límites efectivos; se corrige cinco/seis. Se agregan explícitamente desglose por grupo y
casos no ejecutados como comportamiento observable con RF/CA propios. H4 compara modelo
principal: el flujo actual no delega a explore. No se habilita delegación en esta enmienda.

El conjunto mantiene diez casos, reformulando dos objetivos por síntomas autosuficientes.
Es un baseline de mecánica de edición y contratos, con grupos relacionados; no mide
capacidad general de depuración. Su hash incluye contenido, objetivos y grupos.
La primera comparación es exploratoria: sus diferencias son observaciones, no demuestran
superioridad ni bastan por sí solas para adoptar una configuración. No comparar agregados
de conjuntos distintos como si solo hubiera cambiado el modelo.

§11: procedencia resuelta con extracciones históricas y opción --casos; siguen pendientes
representatividad, contaminación pública y baseline real. El límite se registra desde
la configuración efectiva y no se promete corte duro. Evaluar subagentes requiere otro
flujo y queda pendiente. Si falla la escritura, se conserva solo la última versión
persistida; no se garantiza actualización cuando el almacenamiento no funciona.
