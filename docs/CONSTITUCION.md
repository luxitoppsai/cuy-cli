---
tipo: constitucion
proyecto: cuy-cli
version: 1.0.0
fecha: 2026-09-25
---

# Constitución de cuy-cli

Los principios que **toda spec de este repo debe respetar**. No son buenas intenciones: el
plan de cada feature pasa por una compuerta que los verifica uno por uno, y violarlos exige
justificarlo por escrito en la sección de complejidad del plan.

Cada principio salió de un error concreto de este proyecto, no de un libro. La referencia
está al final de cada uno.

## P1 — Verificar, no deducir

Una afirmación sobre el comportamiento del sistema vale si se observó. No cuenta como
evidencia: que el código *parezca* hacerlo, que el log no muestre errores, que un proceso
*debería* estar corriendo.

**Cómo se aplica.** Toda tarea que cambie comportamiento se cierra ejecutando lo que cambió
y mostrando la salida. Las especificaciones se cierran corriendo sus criterios de
aceptación, no leyéndolos.

> Un agente "lento" resultó ser backoff de reintentos sobre un `Bad Request`. El síntoma no
> se parecía a la causa, y el log lo decía desde el principio.

## P2 — Descubrir el entorno, no asumirlo

Nada que dependa del workspace se escribe a mano: ni los modelos, ni sus topes de tokens, ni
la forma de autenticación, ni el nombre con que un endpoint responde. Se pregunta.

**Cómo se aplica.** Si una spec introduce un valor que varía entre entornos, el plan tiene
que decir cómo se descubre, o justificar por qué se fija.

> El tope de salida es distinto en cada modelo y no está documentado; el passthrough de
> Anthropic acepta `claude-sonnet-4-5` pero no `databricks-claude-sonnet-4-5`.

## P3 — Un camino que solo corre en producción es un camino sin cubrir

Que exista un test suite no significa que el código esté probado. El código que solo se
ejecuta contra un servicio vivo, o solo en otra plataforma, no lo recorre nadie.

**Cómo se aplica.** Todo camino de red, de sistema de archivos o específico de un sistema
operativo tiene un test que lo recorre con las dependencias externas fingidas.

> Un `NameError` de una línea en `instalar.py` sobrevivió a toda la suite y reventó en la
> máquina del trabajo, a mitad de la instalación.

## P4 — Una API que ignora en silencio convierte un typo en código muerto

Cuando se integra contra algo que descarta lo que no reconoce —nombres de hooks, claves de
configuración, tipos de evento— hay que verificar contra su definición, no contra la
memoria.

**Cómo se aplica.** Los nombres que cruzan una frontera se validan en un test contra la
fuente real, no contra una lista copiada.

> El presupuesto declaraba `"message.updated"` como hook. No existe. Nunca contó un
> centavo, sin error ni aviso, durante toda la vida del proyecto.

## P5 — Precisión sobre cobertura en todo lo que filtra

Un falso positivo en un filtro que toca el contexto del modelo es peor que un falso
negativo: el modelo razona sobre una mentira, y nadie se entera.

**Cómo se aplica.** Toda heurística que descarte, redacte o transforme contenido lleva
casos negativos explícitos en sus tests, incluido el propio repositorio.

> La redacción de secretos solo actúa sobre valores entrecomillados, para que
> `token = response.token` —código normal— quede intacto.

## P6 — Fallar cerrado, y que el error diga qué hacer

Ante la duda, no se procede. Y el mensaje explica el siguiente paso, no solo la prohibición.

**Cómo se aplica.** Todo rechazo lleva en el mismo mensaje la acción concreta que
desbloquea. Todo valor desconocido que afecte dinero o seguridad detiene la operación en
vez de asumir un valor por defecto.

> Un modelo sin tarifa conocida no se elige por defecto: el tope de gasto lo sumaría en
> cero y el presupuesto dejaría de existir sin avisar.

## P7 — Distinguir barrera de control

Lo que corre en la máquina del usuario y el usuario puede editar es una **barrera**: sirve
contra el accidente. Un **control** es lo que el usuario no puede desactivar, y vive del
lado del servidor.

**Cómo se aplica.** Toda spec que prometa una garantía de seguridad dice explícitamente
cuál de las dos es y qué **no** cubre. Prometer control donde hay barrera es peor que no
tener nada, porque se deja de mirar.

> El tope de gasto y la redacción de secretos son barreras. El control duro vive en el
> Gateway de Databricks.

## P8 — El secreto nunca toca el disco ni el historial

No se commitean credenciales, ni siquiera revocadas, ni siquiera como fixture de test. Los
registros guardan qué se hizo, nunca el contenido.

**Cómo se aplica.** Los fixtures con forma de credencial se **construyen** en tiempo de
ejecución, no se pegan literales. La auditoría registra rutas y tipos, nunca valores.

> El push de la feature que impide filtrar secretos fue rechazado por GitHub: traía un PAT
> real usado como fixture.

## P9 — KISS y YAGNI, con la simplicidad justificada

La solución más chica que funcione. Nada de flags, capas ni abstracciones para requisitos
hipotéticos.

**Cómo se aplica.** La compuerta del plan pregunta por cada componente nuevo: ¿qué se rompe
si no existe? Si la respuesta es "nada todavía", no entra. Borrar código en favor de algo
que la plataforma ya resuelve es una mejora, no una pérdida.

> Declarar el precio en la config hizo que OpenCode calculara el costo, y permitió borrar
> del plugin la tabla de tarifas entera y su aritmética.

## P10 — El porqué se escribe donde vive el código

Un docstring dice qué hace una función; el conocimiento caro es por qué está hecha así.
Perderlo hace que el error se repita.

**Cómo se aplica.** Docstrings en formato Sphinx (reST) en módulos, clases y funciones
públicas. Las decisiones no obvias quedan como ADR en el vault y los bugs con causa raíz en
`Bugs-and-Learnings/`.

> Las tarifas de Databricks no coinciden con la lista de Anthropic. Costó dos correcciones
> descubrirlo y una refactorización casi lo borra del repo.

---

## Cómo se modifica esta constitución

Agregar, cambiar o quitar un principio requiere su propio RFC, y sube la versión:

- **Mayor** — se quita un principio o se cambia su significado.
- **Menor** — se agrega un principio.
- **Parche** — se aclara la redacción sin cambiar qué exige.

Un principio se quita cuando dejó de ser cierto, no cuando molesta.
