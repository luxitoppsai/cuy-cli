---
rfc: RFC-002
titulo: Redacción de secretos antes de que salgan hacia el modelo
estado: aceptado
fecha: 2026-09-24
proyecto: cuy-cli
---

# RFC-002 — Redacción de secretos antes de que salgan hacia el modelo

> **Estado: aceptado** el 2026-09-24, sin cambios de alcance respecto del borrador.

## 1. Problema

Los permisos de RFC-001 controlan **qué herramientas** corre el agente. No controlan
**qué contenido sale** hacia el endpoint.

Hoy, si alguien abre un repo que contiene un `.env`, un `terraform.tfvars`, un
`~/.aws/credentials` o un notebook con una credencial pegada, y el agente lo lee para
responder una pregunta, ese contenido viaja al endpoint de inferencia. Que el endpoint sea
el de la empresa lo hace menos grave —no sale del perímetro— pero no inofensivo: queda en
los logs de inferencia de Databricks, que tienen otra audiencia y otra retención que el
repositorio de donde salió.

El agente además no necesita hacer nada raro para provocarlo. `grep -r password .` es una
instrucción razonable, y `cat .env` es lo que cualquiera haría para depurar una config.

**Es el único riesgo del proyecto con consecuencia irreversible.** Un token filtrado no se
desfiltra: se rota, se investiga, y la herramienta que lo filtró se prohíbe. El resto de
los problemas abiertos —el tope de gasto local, la auditoría que no sale de la máquina— se
arreglan el día que molestan.

## 2. Qué no resuelve esto

Conviene decirlo antes que lo que sí, porque define el alcance.

- **No impide que una persona pegue un secreto en el prompt.** Si alguien escribe el token
  en el chat, sale. Eso ya pasó una vez en este proyecto, con un PAT real.
- **No es un control, es una barrera.** El plugin vive en la máquina del usuario, que
  puede editarlo. Igual que el tope de gasto: sirve contra el accidente, no contra la
  intención. El control de verdad —si hace falta— vive en el Gateway de Databricks.
- **No detecta un secreto que no parezca uno.** Una contraseña que sea `verano2026` es
  indistinguible de texto.

Lo que sí resuelve es **el accidente**, que es como ocurren casi todas las filtraciones.

## 3. Dónde intervenir

OpenCode expone `tool.execute.after`, que recibe el objeto de salida de la herramienta
**antes de que se le entregue al modelo**, y lo deja mutar:

```ts
const output = { ...result, /* … */ }
yield* plugin.trigger("tool.execute.after", { tool, sessionID, callID, args }, output)
return output   // ← lo que el modelo ve es lo que el hook dejó
```

Es el punto correcto: es el último lugar donde el contenido todavía es nuestro. Cubre
`read`, `grep`, `glob`, `list` y —lo más importante— `bash`, que es por donde entra
cualquier cosa que se nos escape (`cat`, `env`, `aws configure list`).

Y `tool.execute.before` ya se usa para el presupuesto: lanzar desde ahí aborta la llamada.
Sirve para el segundo mecanismo.

## 4. Decisiones propuestas

### D1 — Dos mecanismos, no uno

**Rechazar rutas conocidas** (`tool.execute.before`) y **redactar patrones**
(`tool.execute.after`). Son complementarios y fallan distinto:

| | Cubre | Falla cuando |
|---|---|---|
| Rutas | El archivo entero, sin leerlo | El secreto está en un archivo normal |
| Patrones | Cualquier origen, incluido `bash` | El secreto no tiene forma reconocible |

Una sola de las dos deja un agujero evidente.

### D2 — La lista de rutas se rechaza, no se redacta

`.env`, `.env.*`, `*.pem`, `*.key`, `id_rsa*`, `.credentials.json`, `terraform.tfvars`,
`.npmrc`, `.pypirc`, `.aws/credentials`, `.databrickscfg`, `.ssh/*`.

Rechazar y no redactar, porque el valor del archivo **es** el secreto: un `.env` redactado
no le sirve al modelo para nada y solo genera la ilusión de que lo leyó. El error le dice
al agente que ese archivo está fuera de alcance, que es información útil y verdadera.

### D3 — Patrones de alta precisión, no de alta cobertura

Arrancar con los que tienen forma inconfundible:

- Databricks PAT: `dapi[0-9a-f]{32}`
- AWS access key: `AKIA[0-9A-Z]{16}`, y `aws_secret_access_key` asignado
- Bloques de clave privada: `-----BEGIN * PRIVATE KEY-----`
- GitHub: `ghp_`, `gho_`, `ghs_`, `github_pat_`
- Slack: `xox[baprs]-`
- OpenAI / Anthropic: `sk-`, `sk-ant-`
- Asignaciones explícitas: `(password|secret|token|api_key)\s*[=:]\s*` seguido de algo que
  no sea un placeholder (`***`, `<...>`, `changeme`, `{env:...}`)

**Precisión sobre cobertura, a propósito.** Un falso positivo rompe el trabajo de forma
confusa —el modelo ve `[REDACTADO]` donde había código legítimo y razona sobre una
mentira—. Es preferible dejar pasar un caso raro que envenenar el contexto seguido. La
lista crece con casos reales, no con hipótesis.

### D4 — La redacción conserva la forma

Reemplazar por `[REDACTADO:tipo]`, no borrar la línea ni truncar el archivo. El modelo
tiene que poder seguir razonando sobre la estructura del archivo; lo único que no puede
ver es el valor.

**Efecto secundario que resulta deseable:** si el agente intenta reescribir esa línea, su
`oldString` no va a coincidir con el archivo real y la edición falla. Es decir que la
redacción **no puede pisar un secreto con `[REDACTADO]` en disco**. Falla cerrado sin que
haya que programarlo.

### D5 — Cada redacción queda en la auditoría

Registrar `{herramienta, ruta, tipo, cantidad}` — nunca el valor. Dos motivos: saber si
está funcionando, y detectar el falso positivo sistemático que hay que sacar de la lista.

### D6 — No hay variable de entorno para apagarlo

El tope de gasto tiene `CUY_LIMITE_USD=0` porque es una herramienta de presupuesto
personal. Esto no: una barrera con interruptor se apaga el día que molesta, que es
exactamente el día que hace falta. Quien quiera sacarlo edita el plugin, y eso deja rastro
en git.

## 5. Alcance

**Entra:** `plugin/secretos.js` + `plugin/lib/secretos-core.js`, la lista de rutas, los
patrones, el registro en auditoría, y tests sobre cada patrón con casos positivos y
negativos.

**No entra:** escaneo del prompt del usuario, escaneo de lo que el agente escribe a disco,
integración con un escáner externo (`gitleaks`, `trufflehog`). Todo eso es razonable y
ninguno es necesario para cerrar el riesgo principal.

## 6. Criterios de aceptación

1. `cat .env` por `bash` devuelve un error de permiso, no el contenido.
2. Un archivo normal que contiene `dapi` + 32 hex se lee con el valor reemplazado, y el
   resto del archivo intacto.
3. Un repo sin secretos se lee **idéntico** a como se lee hoy —sin falsos positivos sobre
   el propio código de este proyecto, que menciona `dapi` y `token` en varios lados—.
4. La redacción queda anotada en `auditoria.jsonl` sin el valor.
5. Los tests cubren cada patrón con un caso que debe redactarse y uno que no.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| Falso positivo que rompe el trabajo | Patrones de alta precisión; criterio 3; la lista crece con casos reales |
| Falsa sensación de seguridad | §2 dice explícitamente qué no cubre; el README lo repite |
| El costo de escanear cada salida | Regex sobre texto ya en memoria; medir si aparece como problema |
| Alguien lo desactiva | Asumido: es una barrera, no un control (D6) |

## 8. Preguntas abiertas

1. ¿Se redacta también lo que el agente manda a un MCP externo? Hoy no hay ninguno
   configurado, así que se deja fuera hasta que lo haya.
2. ¿La lista de rutas debe ser configurable por repo (un `.cuyignore`)? Suena útil y suena
   a YAGNI: esperar a que alguien lo pida.
