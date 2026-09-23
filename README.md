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
# 1. La credencial nunca se versiona. Una de las dos:
read -s "?Token Databricks: " T && echo "DATABRICKS_TOKEN=$T" > .env && chmod 600 .env && unset T
# o bien:  databricks auth login --host <host>

# 2. Descubrir el workspace y generar la configuración
python3 generar_config.py --host https://<tu-workspace>.cloud.databricks.com

# 3. Instalar y usar
npm install
./node_modules/.bin/opencode
```

El paso 2 es lo que hace portable el proyecto: consulta los endpoints servidos, sondea
el tope de tokens de cada uno, descarta los que no respetan el contrato OpenAI, y elige
modelo principal y auxiliar. **En el workspace del trabajo genera la configuración de los
Claude que tengas sin que averigües nada a mano.**

```bash
python3 generar_config.py --rapido           # sin sondear límites (más veloz)
bash spike/01-conexion.sh                    # prueba la API cruda, sin capas
python3 -m unittest discover tests           # pruebas
```

## Gotchas encontrados

- **El límite de tokens es por modelo**, no global (`gpt-oss-120b`: 25000,
  `llama-4-maverick`: 8192). El error no dice cuál ni de dónde sale el número.
- **`small_model` hay que declararlo**: OpenCode apunta por defecto a un modelo que no
  existe en el workspace y da 404 en cada sesión, solo visible en el log.
- **Un agente "lento" puede ser backoff de reintentos.** Mirar
  `~/.local/share/opencode/log/opencode.log` antes de sospechar de la red o del modelo.
