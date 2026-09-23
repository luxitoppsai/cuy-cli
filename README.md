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

## Poner en marcha

```bash
git clone https://github.com/luxitoppsai/cuy-cli.git && cd cuy-cli
python3 instalar.py
```

Eso es todo. El instalador verifica que tengas Node, pide el token sin mostrarlo en
pantalla ni dejarlo en el historial, descubre qué modelos sirve tu workspace, genera la
configuración, instala OpenCode local al proyecto y **hace una llamada real para
confirmar que responde** antes de decir que terminó.

Después:

```bash
./node_modules/.bin/opencode
```

También reparte los roles entre los modelos que encontró (D3 del RFC): el capaz ejecuta
y edita, el barato planifica y explora. OpenCode liga un modelo a cada agente de forma
nativa, así que esto es configuración — no hay ninguna modificación al harness.

**Al cambiar de workspace** —de tu entorno de pruebas al del trabajo— volvés a correr
`python3 instalar.py` y se reconfigura solo. En el Databricks del trabajo detecta los
Claude que tengas y los ordena por nivel (haiku < sonnet < opus) sin que averigües nada.

### Opciones

```bash
python3 instalar.py --host https://...     # sin preguntar el workspace
python3 instalar.py --rapido               # no sondear límites de tokens (más veloz)
python3 instalar.py --sin-verificar        # omitir la llamada de prueba final
```

### Otras herramientas

```bash
python3 generar_config.py --host https://...   # solo regenerar la configuración
bash spike/01-conexion.sh                      # probar la API cruda, sin capas
python3 -m unittest discover tests             # pruebas
```


## Gotchas encontrados

- **El límite de tokens es por modelo**, no global (`gpt-oss-120b`: 25000,
  `llama-4-maverick`: 8192). El error no dice cuál ni de dónde sale el número.
- **`small_model` hay que declararlo**: OpenCode apunta por defecto a un modelo que no
  existe en el workspace y da 404 en cada sesión, solo visible en el log.
- **Un agente "lento" puede ser backoff de reintentos.** Mirar
  `~/.local/share/opencode/log/opencode.log` antes de sospechar de la red o del modelo.
