# Auditoría de red: ¿se fuga algo por el lado de la librería?

Fecha: 2026-09-23. Versión auditada: `opencode-ai@1.18.32` (binario `darwin-x64`).

La pregunta importa porque el sentido del proyecto es **no sacar el código del perímetro
de la empresa**. Si el harness contacta servidores propios, esa promesa no se sostiene.

## Qué es realmente el paquete

`opencode-ai` **no contiene código fuente**: es un envoltorio de cuatro archivos
(`bin/`, `LICENSE`, `package.json`, `postinstall.mjs`) que instala un **binario compilado
de ~143 MB** desde una dependencia opcional por plataforma (`opencode-darwin-x64`,
`opencode-linux-x64`, `opencode-windows-x64`, etc.).

**Consecuencia para esta auditoría:** no se puede auditar leyendo el código. Lo que sigue
es análisis estático de cadenas del binario más **observación de las conexiones reales**,
que es la evidencia más fuerte disponible sin recompilar desde fuente.

## Hallazgo: contacta `api.opencode.ai` por defecto

Ejecutando una sesión normal, con un proveedor propio de Databricks configurado y ningún
servicio de OpenCode en uso, el proceso abre una conexión a:

```
104.20.32.17:443   →  api.opencode.ai / app.opencode.ai
```

No se determinó qué envía —el tráfico es TLS y no se interceptó—, pero las variables de
entorno del binario sugieren que corresponde a la verificación de actualizaciones. **No
se encontró ningún SDK de telemetría conocido** (Posthog, Sentry, Segment, Amplitude,
Mixpanel, Datadog, Rollbar): las coincidencias con "rollbar" resultaron ser propiedades
de tema `scrollbar`.

## Solución verificada

El binario expone variables para desactivar cada salida de red. Con estas activas:

| Variable | Qué evita |
|---|---|
| `OPENCODE_DISABLE_AUTOUPDATE` | La llamada a `api.opencode.ai` |
| `OPENCODE_DISABLE_MODELS_FETCH` | Descargar el catálogo de models.dev |
| `OPENCODE_DISABLE_SHARE` + `OPENCODE_AUTO_SHARE=0` | Subir la sesión —con el código— a un servidor de terceros |
| `OPENCODE_DISABLE_LSP_DOWNLOAD` | Descargar servidores de lenguaje en ejecución |
| `OPENCODE_DISABLE_EXTERNAL_SKILLS` | Cargar skills remotas |

**Resultado medido**, observando las conexiones establecidas del proceso y sus hijos
durante una sesión completa:

| | Destinos contactados |
|---|---|
| Sin blindaje | `104.20.32.17` (api.opencode.ai) **+** Databricks |
| Con blindaje | **Solo Databricks** (`3.128.237.222`) |

La sesión funciona igual en ambos casos.

Por eso el lanzador `./cuy` aplica el blindaje siempre: depender de que cada persona
recuerde exportar seis variables es depender de que nadie se olvide nunca.

## Lo que esta auditoría **no** prueba

Conviene ser explícito, porque una auditoría que se presenta como más concluyente de lo
que es resulta peor que ninguna:

- **No se inspeccionó el tráfico TLS.** Se sabe *a quién* contacta, no *qué* envía. Para
  saberlo haría falta un proxy con intercepción (mitmproxy) y confiar en el certificado.
- **Es un binario compilado.** El análisis de cadenas encuentra lo que está en texto
  plano; no descarta comportamiento ofuscado o condicional.
- **Vale para esta versión.** `1.18.32`, que es la que el repo fija exactamente. Una
  versión nueva puede cambiar el comportamiento: **volver a correr esta auditoría al
  subir de versión** es parte del procedimiento de actualización.
- **No cubre los plugins ni los MCP** que se agreguen después, que corren con los mismos
  permisos.

## Reproducir

```bash
# Destinos contactados durante una sesión
./cuy run "decí hola" & PID=$!
for i in $(seq 1 40); do
  for P in $PID $(pgrep -P $PID); do lsof -nP -i -a -p $P | grep ESTABLISHED; done
  sleep 0.5
done
```

## Si hace falta más garantía

El siguiente escalón, si seguridad de la empresa lo exige, es **bloquear por red** en vez
de confiar en variables de entorno: una regla de firewall que solo permita salida al host
de Databricks. Eso no depende de la configuración de la herramienta ni de que el binario
la respete.
