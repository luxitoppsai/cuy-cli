# cuy-cli

CLI de codificación agéntica que habla con **Databricks Model Serving**, para poder usar
un asistente en terminal sin sacar el código del perímetro de la empresa.

Construido **sobre OpenCode** (MIT), no desde cero: el harness es un commodity que itera
a diario; la ventaja está en la integración con Databricks y el gobierno para el equipo.
El razonamiento completo, con la investigación que lo sustenta, está en [RFC.md](./RFC.md).

## Estado

Fase 0 (spike). **La integración con Databricks funciona** — autenticación, streaming,
tool calling, todo verificado. Falta completar una tarea de punta a punta con el agente.
Hallazgos y comandos para reproducir: [spike/RESULTADOS.md](./spike/RESULTADOS.md).

## Dos entornos

| | Desarrollo | Destino |
|---|---|---|
| Workspace | Databricks Community | Databricks del trabajo |
| Modelos | Pesos abiertos (Llama, Qwen, GPT-OSS, Gemma) | Claude |

La superficie de Model Serving es idéntica en los dos, así que la integración se
construye acá y se valida allá. Nada debe asumir en el código qué modelos existen
(decisión D7 del RFC).

## Instalación

```
git clone https://github.com/luxitoppsai/cuy-cli.git
cd cuy-cli
python instalar.py          # en macOS/Linux: python3
```

Eso es todo. El instalador compila el binario desde el fuente que viene en el repo
—por eso arranca con el logo de cuy-cli—, descubre qué modelos sirve tu workspace,
genera la configuración, instala los plugins y **hace una llamada real para confirmar
que responde** antes de decir que terminó.

Requiere [bun](https://bun.sh). La primera vez tarda varios minutos porque descarga
~2 GB de dependencias; las siguientes son rápidas.

Después:

```
cuy.cmd          # Windows
./cuy            # macOS y Linux
```

**Usá siempre el lanzador**, no `opencode` a secas: aplica el blindaje de red. Sin él,
el agente contacta `api.opencode.ai` durante una sesión normal aunque tu proveedor sea
propio ([spike/RED.md](./spike/RED.md)).

**Al cambiar de workspace** volvés a correr el instalador y se reconfigura solo. En el
Databricks del trabajo detecta los Claude y los ordena por nivel sin que averigües nada.

### Si no podés compilar

```
python instalar.py --sin-compilar
```

Usa el binario oficial de OpenCode en vez de compilar: arranca en un minuto y no
necesita bun, pero **vas a ver el logo de OpenCode**. Todo lo demás es idéntico.

Dos fallas conocidas al compilar:

- **Falta bun** — `powershell -c "irm bun.sh/install.ps1 | iex"` en Windows. El
  instalador lo busca también en `~/.bun/bin`, así que **no hace falta reiniciar la
  terminal** después de instalarlo.
- **`tree-sitter-powershell` falla** (necesita Visual Studio Build Tools en Windows). Es
  una gramática de resaltado y **no es fatal**: si `node_modules` quedó completo, volvé
  a correr el instalador y el build sigue.


### Opciones

```bash
python3 instalar.py --host https://...     # sin preguntar el workspace
python3 instalar.py --rapido               # no sondear límites de tokens (más veloz)
python3 instalar.py --sin-verificar        # omitir la llamada de prueba final
```

### Otras herramientas

```bash
python3 generar_config.py --host https://...   # solo regenerar la configuración
python3 -m unittest discover tests             # pruebas
node tests/presupuesto.test.mjs                # pruebas de los plugins
bash spike/01-conexion.sh                      # probar la API cruda (solo Unix)
```

> En Windows usá `python` en vez de `python3`. El único archivo que no corre ahí es
> `spike/01-conexion.sh`, que es una herramienta de diagnóstico, no parte del producto.


## El fuente vive en este repo

`vendor/opencode` trae el fork con `git subtree`, así que un `git clone` se lo lleva todo
y compilar no requiere bajar nada más. Clonar pesa ~78 MB.

Los cambios de marca son tres archivos, en la rama `cuy` del
[fork](https://github.com/luxitoppsai/opencode). Para traer una versión nueva de upstream:

```bash
git subtree pull --prefix=vendor/opencode https://github.com/luxitoppsai/opencode.git cuy --squash
```

Al subir de versión conviene **repetir la auditoría de red** ([spike/RED.md](./spike/RED.md)):
sus conclusiones valen para la versión auditada, no para cualquiera.


## Aspecto

El instalador deja un tema propio (`tema/cuy.json`) — paleta cálida de tierra, pensada
para sesiones largas: los colores de identidad se reservan para lo que hay que mirar y el
resto queda neutro para no competir con el código. **Se elige una vez**, dentro del
agente:

```
/theme      →  elegí "cuy"
```

La elección queda persistida. No se puede fijar desde `opencode.json`: `theme` no es una
clave válida de configuración en esta versión.

El nombre que aparece en las conversaciones sí es configurable y ya viene puesto
(`username: cuy-cli`).

**Lo que no se puede cambiar sin recompilar** es el logo ASCII y el nombre "opencode" del
arranque: están en el binario (`packages/opencode/src/cli/ui.ts` del fuente). Hacerlo
implica mantener un binario propio — ver `ADR-001` en el vault.

## Límites y permisos

Dos controles distintos, que se configuran por separado.

**Qué puede hacer.** La instalación deja una política pensada para equipo: leer, buscar
y navegar no piden permiso; correr pruebas y git de solo lectura tampoco; lo irreversible
—`rm -rf`, `sudo`, `git push --force`, `git reset --hard`, ejecutar lo que se descarga de
internet— está **bloqueado**, no preguntado; y lo demás pregunta.

El criterio es que si el agente pregunta por todo, la gente aprueba sin leer y el control
deja de servir. Se ajusta en el bloque `permission` de `opencode.json`, con patrones por
comando y override por agente.

> En modo headless (`opencode run`) una acción `ask` no tiene quién la responda y la
> sesión queda esperando. Para uso automatizado conviene dejar solo `allow` y `deny`.

**Cuánto puede gastar.** OpenCode cuenta tokens pero no permite ponerles tope: un agente
en loop gasta hasta que alguien mire. El plugin `plugin/presupuesto.js` agrega ese límite
y corta la sesión al alcanzarlo, avisando antes al 80%.

```bash
CUY_LIMITE_TOKENS=300000 ./node_modules/.bin/opencode    # default
CUY_LIMITE_TOKENS=0 ./node_modules/.bin/opencode         # sin tope
```

Se cuenta en tokens y no en dólares porque el precio de un endpoint de Databricks depende
de la modalidad contratada y no viaja en la respuesta; los tokens sí son exactos.

## Auditoría

Cada sesión deja registro de qué tocó el agente y quién lo pidió, en
`~/.local/share/cuy-cli/auditoria.jsonl`.

```bash
python3 auditar.py                 # resumen de los últimos 7 días
python3 auditar.py --comandos      # todos los comandos ejecutados
python3 auditar.py --archivos      # todos los archivos modificados
python3 auditar.py --usuario ana --dias 30
```

Se registra **qué** se hizo, no el contenido: rutas de archivo pero no su texto,
comandos pero no su salida. Un registro de auditoría con el código adentro es una
filtración esperando ocurrir, y crece sin control. También quedan los permisos que la
política consultó o bloqueó, que es la mitad que no aparece en ningún otro lado.

Retención de 90 días por defecto (`CUY_RETENCION_DIAS`), y se apaga con
`CUY_AUDITORIA_OFF=1`.

> **Es atribución, no prueba.** El archivo lo escribe el mismo usuario cuya actividad
> registra, así que puede editarlo. Sirve para saber qué hizo el agente y repartir
> consumo, no para sostener una acusación. Para eso habría que centralizarlo fuera del
> alcance del usuario — hoy fuera de alcance a propósito.

## Aislamiento de red

`./cuy` desactiva todas las salidas de red que no sean tu proveedor: verificación de
actualizaciones, descarga del catálogo de modelos, **compartir sesiones** —que subiría la
conversación con el código adentro a un servidor de terceros—, descarga de servidores de
lenguaje y skills remotas.

| | Destinos contactados |
|---|---|
| `opencode` directo | `api.opencode.ai` + tu proveedor |
| `./cuy` | **solo tu proveedor** |

Si seguridad de tu empresa pide más garantía que unas variables de entorno, el siguiente
escalón es una regla de firewall que solo permita salida al host de Databricks: eso no
depende de que el binario respete su propia configuración.

## Qué vive dónde

El repo tiene **solo código propio**: el instalador, el generador de configuración, los
plugins, las pruebas y la documentación. **OpenCode no está en el repo** — se baja de npm
al instalar (`node_modules`, unos 286 MB, ignorados por git).

La versión está **fijada exacta** (`opencode-ai: 1.18.32`, sin `^`) y el
`package-lock.json` está versionado. Para una herramienta de equipo importa más que todos
tengan exactamente lo mismo que recibir mejoras automáticas: OpenCode itera a diario, y
el generador escribe configuración para un esquema concreto (`small_model`, `limit`,
agentes). Si cambia entre versiones, a uno le funciona y a otro no.

**Para subir de versión**, que es un acto deliberado:

```bash
npm install opencode-ai@<nueva-version> --save-exact
python3 instalar.py --sin-verificar   # regenerar config por si cambió el esquema
./node_modules/.bin/opencode          # probar antes de commitear el lock
```

## Gotchas encontrados

- **El límite de tokens es por modelo**, no global (`gpt-oss-120b`: 25000,
  `llama-4-maverick`: 8192). El error no dice cuál ni de dónde sale el número.
- **`small_model` hay que declararlo**: OpenCode apunta por defecto a un modelo que no
  existe en el workspace y da 404 en cada sesión, solo visible en el log.
- **Un agente "lento" puede ser backoff de reintentos.** Mirar
  `~/.local/share/opencode/log/opencode.log` antes de sospechar de la red o del modelo.
