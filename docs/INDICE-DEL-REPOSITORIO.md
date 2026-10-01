# Índice del repositorio

Cuy usa CodeGraph para ayudar al agente a encontrar símbolos, llamadas y dependencias
durante la conversación libre. Se prepara automáticamente al abrir Cuy o ejecutar
`cuy run` local; no requiere `/graphify` ni un asistente de inicio.

## Para qué sirve

El índice guarda un mapa de funciones, clases, archivos y sus relaciones. Así el agente
puede localizar la implementación de una función, consultar quién la llama o identificar
dependencias antes de proponer un cambio. Es especialmente útil cuando una pregunta
abarca varios archivos y necesitas entender cómo se conectan.

Las consultas devuelven la información relacionada con la pregunta; no añaden todo el
repositorio al mensaje del modelo. El índice complementa la lectura de archivos y las
pruebas del proyecto. No modifica tus fuentes ni ejecuta sus pruebas por su cuenta.

## Qué ocurre al abrir Cuy

1. Determina la raíz del repositorio Git o del worktree. Fuera de Git usa la carpeta
   de la conversación. También admite la ruta del arranque interactivo y `run --dir`.
2. Si falta CodeGraph, descarga su ejecutable de la release fijada en el repositorio y
   comprueba SHA-256. La primera descarga necesita acceso a GitHub; las consultas son locales.
3. Prepara una copia de los archivos incluidos y comprueba sus hashes. Actualiza altas
   y cambios; reconstruye la caché si se borraron archivos para eliminar símbolos antiguos.
4. Abre Cuy con doce herramientas de consulta de lectura. Repite la comprobación de
   archivos antes de cada consulta para incorporar cambios durante la conversación.

Por ejemplo, puedes escribir:

```text
Explícame qué llama a la función reservar_stock y qué podría verse afectado si la modificamos.
```

El agente dispone del índice y de las herramientas habituales. Su elección depende de
la tarea y del modelo; disponer del índice no garantiza que lo consulte en cada respuesta.
Las rutas de los resultados apuntan a los archivos originales. El agente debe leerlos
antes de editar y verificar el resultado.

## Archivos y almacenamiento

El estado está en `.cuy/codegraph/` dentro del proyecto: copia local de fuentes,
manifiesto de hashes, esquemas de herramientas y caché nativa. Cada repositorio/worktree
tiene su propio estado; mover el repositorio obliga a regenerar la caché.

Cuy añade `/.cuy/codegraph/` y `/.codegraph-state/` a `.gitignore`, sin reemplazar las
reglas anteriores ni repetirlas. En un repositorio nuevo, esta modificación de
`.gitignore` aparece como un cambio que puedes revisar y guardar.

Dentro de Git se incluyen archivos versionados y archivos nuevos no ignorados, con
sus cambios actuales; no necesitas hacer commit para actualizar el índice. Se excluyen:

- Archivos y carpetas ocultos, enlaces simbólicos y nombres convencionales de
  credenciales como `credentials.json`, `secrets.json`, `*.token`, `*.pem` y `*.key`.
- Dependencias y salidas como `node_modules`, `vendor`, `bin`, `dist`, `build`, `target`
  y entornos virtuales. CodeGraph excluye también `fixtures`, `examples`, `cases` y `benches`.
- Archivos con bytes nulos o mayores de 1 MiB. El límite de la copia es de 5000 archivos
  y 64 MiB de texto: si se supera, Cuy avisa y continúa sin índice, evitando cobertura parcial.

CodeGraph analiza los lenguajes que soporta; copiar un archivo no significa que su
contenido haya generado símbolos. Fuera de Git se aplican las exclusiones convencionales;
las reglas personalizadas de `.gitignore` requieren un repositorio Git.

Las exclusiones son barreras locales. Un archivo de código permitido puede contener un
secreto que no se reconozca. Los resultados usados como contexto se envían al modelo
configurado, igual que las lecturas habituales de Cuy.

## Límites y recuperación

Se usa CodeGraph 0.20.1 en modo estructural, sin embeddings ni API de inferencia para
indexar. La búsqueda es por nombres/texto, no búsqueda semántica con vectores. No incluye
historial Git, memoria del agente ni relaciones con otros repositorios. El proceso
nativo recibe un entorno mínimo sin las credenciales del proveedor.

El análisis estático puede omitir relaciones dinámicas. Un resultado vacío no demuestra
que no haya dependencias. En esta versión, las consultas por línea pueden resolver el
nodo del archivo completo al consultar su primera línea; consultar dentro del cuerpo
del símbolo evita esa ambigüedad. Las líneas expuestas en Cuy se cuentan desde 1.

Si no puede descargar, actualizar o consultar el índice, Cuy conserva sus herramientas
de lectura y búsqueda. Reintenta al volver a abrirlo. Para regenerar un estado dañado,
cierra las sesiones del proyecto y mueve su carpeta `.cuy/codegraph/` a otra ubicación;
la próxima apertura la crea de nuevo. Las sesiones simultáneas serializan las consultas:
si otra está actualizando, se informa que debes reintentar.

Esta release ofrece binarios para macOS y Linux x64/ARM64 y Windows x64. Windows ARM64
continúa sin índice. Los comandos informativos, conexiones remotas y `cuy tarea` no
preparan el índice en este alcance.

Las consultas de una sola ejecución revisan archivos y abren la caché antes de responder.
Se eligieron para respetar las exclusiones y detectar borrados; añaden trabajo frente a
un servidor residente. Todavía no se ha medido ahorro de tokens, tiempo o calidad con
modelos reales de Databricks.

Contrato externo: [CodeGraph v0.20.1](https://github.com/codegraph-ai/CodeGraph/releases/tag/v0.20.1).
Decisión: [RFC-004](rfc/RFC-004-indice-del-repositorio.md).
