---
rfc: RFC-001
titulo: CLI de codificación agéntica multi-proveedor con Databricks para el equipo
estado: aceptado
fecha: 2026-09-23
proyecto: cuy-cli
---

# RFC-001 — CLI de codificación agéntica multi-proveedor con Databricks

> **Estado: aceptado** el 2026-09-23, con la decisión de arrancar por la Fase 0 sin
> divergir de OpenCode (el fork se decide después, con datos). El nombre `cuy-cli` sigue
> siendo provisional (ver Preguntas abiertas).

## 1. Problema

El equipo no tiene un asistente de codificación en terminal que pueda usar con los
modelos servidos por **Databricks Model Serving** de la empresa. Las herramientas
existentes asumen las APIs públicas de Anthropic u OpenAI, lo que obliga a elegir entre
no usarlas o mandar código de trabajo fuera del perímetro de la empresa.

El desarrollo ocurre en un **Databricks Community** con modelos de pesos abiertos, y el
destino es el **Databricks del trabajo**, que sí sirve Claude (§2.5). Esa separación no es
un obstáculo sino una restricción de diseño: obliga a que nada dependa en el código de qué
modelos existen.

Hace falta además poder elegir el modelo según la tarea y que el equipo pueda instalarlo
y configurarlo sin que cada persona reinvente su setup.

Secundariamente, y sin que condicione el diseño, poder apuntar a proveedores públicos
(OpenAI, DeepSeek, Qwen) para no quedar atado a una sola vía.

## 2. Estado del arte (investigación, 2026-09-23)

Esta sección existe porque cambió el diseño. Sin ella, el RFC habría propuesto algo
que la evidencia desaconseja.

### 2.1 El espacio está resuelto y saturado

[OpenCode](https://opencode.ai/docs/providers/) (~202k estrellas, MIT) soporta 75+
proveedores vía Vercel AI SDK y el registro Models.dev, con plugins, LSP y hooks.
Agregar un proveedor OpenAI-compatible —como Databricks— es un bloque de configuración
con `@ai-sdk/openai-compatible`, `baseURL` y headers propios; no requiere tocar código.
También compiten Goose (Block, donado a la Agentic AI Foundation de la Linux Foundation
en abril de 2026 — la única historia de gobierno neutral del espacio), Crush, Cline,
Continue y Aider (este último con la velocidad frenada, sin release etiquetado desde 2025).

**DeepSeek Harness** merece mención aparte porque es tentador: es de `deepseek-ai`, MIT,
y su arquitectura "todo es un plugin" sobre el kernel Cordis es conceptualmente buena.
Pero está en **v0.1, developer preview** (lanzado 2026-08-13), su propio README avisa en
mayúsculas que *habrá cambios que rompen compatibilidad*, es un framework más que un
agente terminado y no publica benchmarks. Para una herramienta que va a usar el equipo en
el trabajo hoy es la base equivocada; vale seguirlo, no construir encima todavía.

### 2.2 El harness pesa más que el modelo (*model-harness fit*)

Es el hallazgo que más condiciona este proyecto. Los modelos frontera se post-entrenan
contra una superficie de herramientas concreta, y las instintos no viajan con los pesos:

- El mismo modelo cambia **hasta 16 puntos porcentuales** según el harness (77% → 93%).
- Las colisiones son concretas: Codex espera `apply_patch` con gramática Lark; Claude
  Code espera `Edit` con `old_string`/`new_string`; Copilot CLI usa tres verbos de bash.
  Un modelo entrenado en parches gasta razonamiento extra —y falla más— si se lo fuerza
  a reemplazo de strings.
- Los **routers de terceros rinden por debajo** de los pares modelo-harness nativos en
  Terminal-Bench.

La conclusión de la fuente es explícita: soportar rendimiento multimodelo real cuesta un
esfuerzo de ingeniería equivalente al post-entrenamiento original, por modelo. **No hay
almuerzo gratis.** Ver [Model-Harness Fit](https://nicolasbustamante.com/blog/model-harness-fit).

La salida que sí escala es la de GitHub Copilot CLI: no fingir neutralidad y dar a cada
familia su vocabulario nativo — Claude recibe `Edit`/`Write`, OpenAI recibe `apply_patch`.

### 2.2.1 Cuánto se puede recuperar: el techo no es tan bajo

El párrafo anterior suena a que un harness de terceros está condenado. La evidencia dice
otra cosa: **la casi-paridad es alcanzable si se replican las superficies correctas.**
Warp midió una mejora de **3-5%** sobre los equivalentes GPT estándar tras hacerlo. Lo
que se desploma —"a veces en dos dígitos"— es meter esos modelos en un *wrapper genérico
de Chat Completions*. La diferencia entre ambos resultados es trabajo concreto, no magia:

1. **`apply_patch` con diffs V4A.** Los modelos Codex están post-entrenados en ese
   formato; Warp reportó ediciones más fiables al migrar desde reemplazo de strings.
2. **Nombres de herramienta semánticamente correctos** (`ripgrep`, no `grep`). Parece
   cosmético y dio mejoras medibles en Warp y en OpenCode.
3. **Prefijo de prompt estable** (instrucciones, definiciones de herramientas, contexto
   del proyecto en posición fija). Habilita cache hits en 60-80% de las requests, lo que
   además baja el costo.

Referencia de magnitud: Codex CLI con GPT-5.5 marca **83,4%** en Terminal-Bench 2.1 —el
mejor CLI con nombre—, y el tope absoluto lo tiene un harness de investigación (`vix`)
con Opus 4.7 en 90,2%
([leaderboard](https://ssojet.com/blog/best-cli-coding-agents-ranked)).

**Lo que más importa para este RFC:** OpenCode **ya implementa esta estrategia** — agregó
`apply_patch` para modelos GPT/Codex y mantiene las herramientas de edición estándar para
Claude y el resto. La decisión D2 no hay que construirla desde cero
([detalle](https://codex.danielvaughan.com/2026/04/28/codex-models-third-party-harnesses-apply-patch-v4a-portable-agent/)).

Lo que sí queda fuera del alcance de un harness de terceros, y conviene no prometer:
sandbox propio, compactación del lado del servidor y *review gates* automáticos del CLI
oficial.

### 2.3 Rutear por complejidad no conviene a esta escala

[RouteLLM](https://klymentiev.com/blog/llm-router) (LMSYS/Berkeley, ICLR 2025) reporta
ahorros de 40-85% enrutando con clasificadores entrenados, pero el punto de equilibrio
costo-beneficio está alrededor de **100.000 usuarios/día**: por debajo, la complejidad de
ingeniería no se paga. Suma además 40-120 ms de latencia por clasificación.

Lo que sí aplica a un equipo es el **ruteo por rol**: un modelo barato para planificar,
uno capaz para ejecutar, otro para criticar. OpenDev lo implementa como *binding por
workflow* con jerarquía sesión → agente → workflow → LLM
([arXiv:2603.05344](https://arxiv.org/html/2603.05344v1)). La decisión queda explícita y
auditable en vez de depender de un clasificador que adivina.

### 2.4 Los fallos del harness ya están catalogados

De la misma investigación, los problemas que aparecen sí o sí y su cura conocida:

| Problema | Cura documentada |
|---|---|
| *Context rot* por buffering infinito | Capa de contexto desde el día 1, compactación adaptativa progresiva |
| *Instruction fade-out* a los 20-30 turnos | Recordatorios inyectados en el punto de decisión, no solo en el prompt inicial |
| Fatiga de aprobaciones | Permisos persistentes por prefijo de comando o nivel de riesgo |
| Modo plan frágil como máquina de estados | Planner como subagente con schema de **solo lectura** — separación en el schema, no chequeos en runtime |
| Loops repetitivos de herramientas | Es un síntoma típico de modelos no entrenados para agentic coding |

### 2.5 Dos entornos, no uno (corregido con Fase 0)

> **Corrección (2026-09-23).** Una versión anterior de este RFC asumía un solo entorno
> Databricks con Claude servido. Son **dos**, y confundirlos llevó a decisiones mal
> fundadas. Se deja la corrección a la vista porque el error —tomar el catálogo por lo
> desplegado, y un workspace por otro— es fácil de repetir.

| | Desarrollo | Destino |
|---|---|---|
| Workspace | Databricks **Community** (`dbc-xxxxxxxx-xxxx`) | Databricks del **trabajo** |
| Modelos | Pesos abiertos básicos | **Claude** (Haiku, Sonnet, Opus) |
| API nativa de Anthropic | No existe | Disponible |
| Prompt caching | No observable | Disponible (documentado para Claude) |
| Cuotas | Limitadas | Por confirmar |

**Lo verificado en el entorno de desarrollo** (`spike/RESULTADOS.md`):

- El token autentica (los fallos fueron 404, no 401).
- La superficie **OpenAI-compatible funciona**: `base_url=<host>/serving-endpoints`,
  `model=<nombre del endpoint>`, `Authorization: Bearer`.
- **Tool calling funciona** en `gpt-oss-120b`, `qwen35-122b-a10b` y `llama-4-maverick`:
  los tres eligieron la herramienta correcta al primer intento, con `finish_reason:
  tool_calls`. Los dos primeros devuelven además bloques de razonamiento.
- 11 endpoints `READY`, todos de pesos abiertos: `gpt-oss-120b/20b`,
  `qwen35-122b-a10b`, `qwen3-next-80b`, `llama-4-maverick`, `llama-3-3-70b`,
  `llama-3-1-8b`, `gemma-3-12b`, más tres de embeddings.

**Qué se puede inferir del entorno de desarrollo, y qué no.** Es la distinción que evita
sorpresas al migrar:

*Transfiere tal cual*, porque la superficie de Model Serving es la misma tenga Gemma o
Claude detrás: configuración del proveedor, autenticación, ruteo por nombre de endpoint,
formato de tool calling, y todo lo que no depende del modelo — permisos, auditoría,
sesiones, instalación y distribución. **Es la mayor parte del trabajo.**

*No transfiere, y hay que validarlo en el trabajo*: la calidad agéntica (un modelo de
pesos abiertos en 30 turnos no predice a Claude), la API nativa de Anthropic, el prompt
caching, el costo y las cuotas.

**Riesgo propio de Community:** las cuotas son mucho más ajustadas. Una sesión agéntica
larga consume bastante más que una consulta suelta, así que se puede chocar con límites
probando algo que en el workspace del trabajo funcionaría.


## 3. Decisiones

- **D1. Construir sobre OpenCode, no desde cero.** El harness es un commodity que se
  mueve a diario; la ventaja del equipo está en Databricks con gobierno, que nadie más va
  a construir. Un harness casero puesto frente al equipo hereda derivas de instrucción y
  loops documentados. El aprendizaje se obtiene construyendo proveedor, router y capa de
  permisos, y leyendo el código de OpenCode.
  *Alternativa descartada:* desde cero (meses, compitiendo contra equipos que iteran a
  diario). *Salida de emergencia:* forkear si Fase 0 muestra que no se pueden definir
  superficies de herramienta por modelo.

- **D2. Superficies de herramienta por familia de modelo, no denominador común.** Cada
  familia recibe su vocabulario nativo: `apply_patch` con diffs V4A para GPT/Codex,
  `Edit`/`Write` para Claude, nombres semánticamente correctos (`ripgrep`, no `grep`) y
  prefijo de prompt estable para aprovechar el cache. Degradar a un denominador común
  cuesta rendimiento en todos los modelos a la vez; hacerlo bien recupera la casi-paridad
  (§2.2.1). OpenCode ya trae esta estrategia implementada, así que se hereda en vez de
  construirse.

- **D3. Ruteo por rol explícito, no clasificador de complejidad.** Con Claude servido en
  Databricks (§2.5), el ruteo es por **nivel dentro de una misma familia**: el modelo más
  barato disponible para planificar y tareas mecánicas, y Opus reservado para lo difícil
  o para criticar. Mismo vocabulario de herramientas en todos los niveles, decisión
  explícita y visible en la traza. A escala de equipo un clasificador entrenado no se
  paga y vuelve la decisión opaca (§2.3).
  Con el inventario real (§2.5) los niveles son otros: modelos chicos (`gpt-oss-20b`,
  `gemma-3-12b`, `llama-3-1-8b`) para tareas mecánicas, y grandes (`gpt-oss-120b`,
  `qwen35-122b-a10b`, `llama-4-maverick`) para ejecutar. *Pendiente de medición:* costo
  por token de cada uno y si los chicos aguantan una tarea real sin derivar.

- **D4. No reimplementar contexto, sesiones ni compactación.** Se usan las de OpenCode.
  Si resultan insuficientes, se mide antes de tocar.

- **D5. Credenciales por persona, nunca en el repo.** Cada quien usa su token de
  Databricks; el repo versiona configuración, no secretos — mismo criterio que
  `claude-config`.

- **D7. El entorno es configuración, nunca código.** Lista de endpoints, elección de
  superficie de herramientas, credenciales y ruteo viven en configuración por entorno. El
  desarrollo pasa por Community y el uso real por el workspace del trabajo (§2.5): mudarse
  de uno al otro debe ser cambiar un archivo, no tocar el harness. Es la misma disciplina
  que en `claude-config`.

- **D6. Sin telemetría hacia afuera.** El código del trabajo no sale del perímetro
  Databricks salvo que la persona elija explícitamente un proveedor público.

## 4. Alcance

**Entra:** los modelos servidos del workspace funcionando de punta a punta en un harness
serio; ruteo por nivel entre los endpoints disponibles; permisos y auditoría adecuados a
uso de equipo; instalación y configuración reproducible; documentación para que el equipo
lo adopte sin ayuda.

**Secundario, no condiciona el diseño:** proveedores públicos (OpenAI, DeepSeek, Qwen)
como alternativa para no depender de una sola vía.

**No entra (por ahora):** escribir el loop de agente, el sistema de contexto o el de
sesiones; clasificador de complejidad entrenado; interfaz gráfica; proveedores más allá
de los nombrados; fine-tuning de modelos.

## 5. Fases

### Fase 0 — Spike

**Ejecutado el 2026-09-23** en el entorno de desarrollo (`spike/01-conexion.sh`,
detalle en `spike/RESULTADOS.md`):

| # | Pregunta | Resultado |
|---|---|---|
| 1 | ¿Autentica el token? | **Sí** (los fallos fueron 404, no 401) |
| 2 | ¿Superficie OpenAI-compatible? | **Sí** |
| 3 | ¿Tool calling real? | **Sí**, en los tres modelos grandes probados |
| 4 | ¿API nativa de Anthropic / caching? | **No aplica** en Community: no hay Claude |

Con eso, la plomería está validada: se puede construir contra Databricks con confianza.

**Pendiente, separado por entorno** (§2.5):

*En desarrollo (Community) — se puede hacer ya:*

5. **OpenCode apuntado a estos endpoints**, con una tarea de codificación real de punta a
   punta. Valida la integración, no la calidad.
6. **Qwen Code como base alternativa**: sus modelos están post-entrenados para ese harness
   y Community sirve dos Qwen grandes. Es el único lugar donde se puede comparar bases con
   un par casi nativo. Merece medirse antes de fijar la base.
7. Cuidado con las **cuotas** de Community: si algo falla en una sesión larga, descartar
   primero el límite del tier antes de culpar al diseño.

*En el trabajo — requiere acceso al workspace de la empresa:*

8. **Sesión agéntica larga (>30 turnos) con Claude**: ¿deriva o entra en loops? Es la
   pregunta que decide la calidad del producto y **no se puede responder en Community**.
9. **API nativa de Anthropic y prompt caching** contra los endpoints Claude reales.
10. **Costo y cuotas** del workspace del trabajo.

**Criterio de muerte:** ya no hay uno técnico en desarrollo — la integración funciona. El
riesgo se corrió al punto (8), que solo se resuelve en el trabajo.

### Fase 1 — Databricks utilizable

Proveedor configurado y credenciales por persona, con una tarea de codificación real
completada de punta a punta. Se construye y se prueba contra Community; la validación
final es contra el workspace del trabajo (D7: cambiar de entorno es cambiar un archivo).

### Fase 2 — Ruteo por rol

Planner / ejecutor / crítico configurables por proyecto, con el modelo elegido visible en
la traza. Medición de costo y calidad contra usar un solo modelo.

### Fase 3 — Gobierno para equipo

Niveles de permiso, persistencia de aprobaciones por prefijo, trazas por usuario y
auditoría. Sandboxing del SO si el uso lo justifica.

### Fase 4 — Distribución

Instalación y configuración reproducible para el equipo (mismo patrón que
`claude-config`), documentación y guía de adopción.

## 6. Criterios de aceptación

- [ ] Una persona del equipo instala, configura y completa una tarea real contra
      Databricks siguiendo solo la documentación, sin ayuda.
- [ ] El código de trabajo no sale del perímetro Databricks salvo elección explícita.
- [ ] El ruteo por nivel funciona entre los endpoints disponibles y su decisión es
      visible en la traza.
- [ ] Se conoce si el prompt caching existe sobre estos endpoints. *No exigible*: está
      documentado para Claude y no se observaron contadores sobre pesos abiertos (§2.5).
- [ ] Cada familia de modelo recibe su superficie de herramientas nativa, con prefijo de
      prompt estable (medible por tasa de cache hits).
- [ ] Las credenciales viven fuera del repo; versionamos configuración.
- [ ] Existe traza por usuario suficiente para auditar qué hizo el agente.
- [ ] Una sesión larga (>30 turnos) no deriva ni entra en loops de herramientas.

## 7. Riesgos

- **La calidad agéntica no se puede validar en el entorno de desarrollo.** Los pesos
  abiertos de Community sirven para probar la plomería, no para predecir a Claude. El
  riesgo real —deriva de instrucciones y loops a los 20-30 turnos (§2.4)— solo se mide en
  el workspace del trabajo. Mitigación: no tomar resultados de Community como evidencia
  de calidad, solo de integración.
- **Cuotas de Community.** Sesiones agénticas largas pueden chocar con límites del tier
  gratuito y confundirse con fallos del diseño.
- **El prompt caching puede no sobrevivir la capa intermedia.** Databricks lo soporta,
  pero hay bugs documentados en abstracciones con este combo exacto. Sin caching el costo
  por sesión sube fuerte y se pierde un criterio de aceptación. Se mide en Fase 0.
- **Cuotas y costo de Model Serving.** Habrá que confirmar la modalidad contratada
  (pay-per-token vs provisioned throughput) y sus límites: un agente en sesión larga
  consume mucho más que una consulta suelta, y puede chocar con cuotas pensadas para
  otro patrón de uso.
- **Dependencia de OpenCode.** Si cambia de rumbo, de licencia o se frena, heredamos el
  problema. Mitigación: es MIT y forkeable; mantener la capa propia desacoplada.
- **El rendimiento multimodelo tiene techo, pero es más alto de lo que parece.** Ningún
  harness de terceros iguala al par nativo (§2.2); replicando las superficies correctas
  se llega a casi-paridad (§2.2.1). Lo que hay que comunicar al equipo es eso —
  casi-paridad con trabajo—, no "igual que Claude Code" ni "no sirve".
- **Gobierno corporativo.** Usar Model Serving desde una herramienta nueva puede requerir
  aprobación de seguridad o plataforma. Conviene confirmarlo antes de Fase 1.
- **Costos sin control.** Un agente en loop puede gastar mucho rápido. Hace falta límite
  de gasto por sesión antes de abrirlo al equipo.

## 8. Preguntas abiertas

1. **Nombre y ubicación.** `cuy-cli` es provisional. ¿Es un proyecto propio o un
   componente de **cuykit**, dado que ambos son del COE y del mismo entorno Databricks?
2. ~~¿Qué modelos hay disponibles?~~ **Respondida por la Fase 0**: pesos abiertos
   (GPT-OSS, Qwen, Llama, Gemma), **ningún Claude servido** (§2.5).
   **Pregunta nueva y la más importante del proyecto: ¿puede el admin de Databricks
   habilitar Claude** en este workspace, pay-per-token o provisioned throughput? Si la
   respuesta es sí, gran parte del §2.5 original vuelve a aplicar y el proyecto mejora
   mucho. Si es no, el diseño se queda con pesos abiertos y hay que medir si aguantan.
3. **¿Cuántas personas** del equipo y con qué sistemas operativos? Define cuánto pesa el
   soporte multiplataforma.
4. **¿Hay política de la empresa** sobre asistentes de IA con código propietario? Puede
   restringir los proveedores públicos a cero.
5. **¿Repo privado en `luxitoppsai` o en la organización de la empresa?** Si lo usa el
   equipo, la propiedad y el mantenimiento a largo plazo cambian.
