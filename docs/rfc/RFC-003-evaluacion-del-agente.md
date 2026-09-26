---
rfc: RFC-003
titulo: Evaluación del agente — medir si la herramienta sirve
estado: borrador
fecha: 2026-09-25
proyecto: cuy-cli
constitucion: 1.0.0
---

# RFC-003 — Evaluación del agente

> **Estado: borrador.** No se programa hasta que esté `aceptado`.

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
$ python evaluar.py
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
| `sin_pasos` | Agotó el límite de pasos |
| `sin_cambios` | Terminó sin tocar ningún archivo |
| `error` | El motor falló, o se agotó el tiempo |

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

### 4.5 Estructura

```
evaluacion/
  casos/NNN-slug/{caso.json,proyecto/}
  resultados/AAAA-MM-DDTHH-MM.json
evaluar.py
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
| RF-008 | El runner **debe** estimar el costo antes de empezar y pedir confirmación si supera un umbral. |
| RF-009 | El runner **debe** detenerse si el presupuesto mensual se agota a mitad de la corrida, dejando el informe parcial escrito. |
| RF-010 | Un caso que falla **no debe** interrumpir la corrida. |
| RF-011 | El runner **no debe** dejar residuos en el repositorio del usuario ni en su `opencode.json`. |

## 8. Criterios de aceptación

| ID | Criterio |
|---|---|
| CA-001 | Con diez casos versionados, `python evaluar.py` produce un informe con las seis métricas de RF-006. |
| CA-002 | Un caso cuyo proyecto ya viene arreglado se clasifica `resuelto`; uno imposible, `sin_verificar`. |
| CA-003 | Un agente simulado que borra el archivo de prueba se clasifica `test_modificado`, no `resuelto`. |
| CA-004 | El repositorio de un caso materializado no contiene el arreglo en ninguna parte de su historia. |
| CA-005 | Dos corridas con configuraciones distintas producen informes comparables campo a campo. |
| CA-006 | Una corrida interrumpida deja un informe parcial válido con los casos ya completados. |
| CA-007 | Después de una corrida, `git status` del repositorio del usuario no muestra cambios. |

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| **El agente hace trampa con la prueba** | RF-003 y CA-003. Es el riesgo principal: sin esto la métrica mide lo contrario de lo que dice. |
| **Contaminación**: los casos salen de un repo público que el modelo pudo ver | Se documenta como límite. El repo de un solo commit evita la fuga por `git`, no la memorización. Los casos de repos privados del trabajo son más confiables y no se versionan acá. |
| **Muestra chica**: diez casos dan mucho ruido | Se reporta el número absoluto además del porcentaje —"7/10", no "70%"— para no sugerir precisión que no hay. El conjunto crece con casos reales. |
| **Evaluar cuesta plata** | RF-008 y RF-009. Una corrida estimada en $0.50–$2 consume un quinto del tope mensual: no puede correrse a ciegas. |
| **No determinismo del modelo** | Se registra la variación entre corridas de la misma configuración. No se promete reproducibilidad exacta. |
| **El conjunto se vuelve el objetivo** | Diez casos no son el producto. Se revisa el conjunto cuando la tasa supere el 80%: a esa altura mide poco. |

## 10. Plan de entrega

| Hito | Contenido | Demostrable |
|---|---|---|
| **H1** | Materialización de casos y clasificación, con tres casos | `evaluar.py --seco` clasifica sin gastar un token |
| **H2** | Corrida real y informe | El comando de §2 sobre tres casos |
| **H3** | Diez casos derivados de arreglos reales | Primera cifra de referencia del proyecto |
| **H4** | Comparación entre configuraciones | Responder si Haiku en `explore` pierde algo |

H1 es MVP: clasificar bien sin gastar es lo que hace confiable todo lo demás.

## 11. Preguntas abiertas

1. **¿De dónde salen los diez casos?** La historia de cuy-cli tiene arreglos reales con
   prueba —el `NameError` del instalador, los hooks que no existían, el sondeo que aprobaba
   de más— pero el repo es público. Los repos del trabajo son mejores casos y no se pueden
   versionar acá. Posible respuesta: los públicos como conjunto base versionado, y un
   `CUY_CASOS` que apunte a un conjunto privado.
2. **¿Cuántos pasos se le dan a un caso?** Hoy `corregir` usa 30. Si el límite es el que
   determina la tasa, se está midiendo el límite y no el agente.
3. **¿Se evalúa con el presupuesto activo o desactivado?** Con tope activo la corrida puede
   cortarse a la mitad; sin tope puede gastar sin techo. Inclinación: tope propio de la
   corrida, separado del mensual.
