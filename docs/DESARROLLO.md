# Desarrollo y distribución

Esta guía se ejecuta desde la raíz de cualquier copia del repositorio. No requiere rutas
personales, un remoto concreto ni acceso a notas externas. Para el uso diario basta la
[instalación del README](../README.md); las herramientas adicionales son para desarrollo.

## Preparar y probar

Usa Python 3.12 y Node 22 para reproducir las versiones declaradas en la CI, además de Git.
Las utilidades Python usan la biblioteca estándar. Las pruebas locales básicas son:

```sh
python3 -m unittest discover tests
npm test
```

En Windows sustituye `python3` por `python`. `npm test` ejecuta las pruebas JavaScript
con Node. Las pruebas que requieren herramientas o un motor opcional pueden omitirse:
revisa las omisiones, además del resultado final.

Para verificar los contratos con el paquete fijado en `package-lock.json`, instala primero
las dependencias de desarrollo:

```sh
npm ci --no-fund --no-audit
```

Para probar un ejecutable concreto, define `CUY_TEST_BINARIO` con su ruta absoluta:

```bash
# macOS/Linux: binario instalado por Cuy
export CUY_TEST_BINARIO="$PWD/bin/cuy"
python3 -m unittest discover -s tests -p test_motor.py
```

```powershell
# Windows: binario instalado por Cuy
$env:CUY_TEST_BINARIO = (Resolve-Path .\bin\cuy.exe).Path
python -m unittest discover -s tests -p test_motor.py
```

También puedes apuntar al motor instalado por npm; la CI usa
`node_modules/opencode-ai/bin/opencode.exe`. El motor de npm y el binario publicado
pueden diferir: para aprobar una release, comprueba sus artefactos concretos.
Estas pruebas usan un proveedor sintético en localhost, no Databricks.

Comprobaciones específicas de documentación y evaluación:

```sh
python3 -m unittest discover -s tests -p test_trazabilidad.py
python3 evaluar.py --seco
```

El modo seco debe detectar las bases defectuosas de los casos; no mide la capacidad del modelo.
Una evaluación real requiere instalación configurada, presupuesto explícito y acceso a
Databricks; consulta [evaluación](../evaluacion/README.md).

## Compilar una release

Requiere Python 3.11 o posterior (el script usa `hashlib.file_digest`) y la versión de Bun
indicada en `packageManager` de `vendor/opencode/package.json`. Mantén ese árbol de fuentes
al copiar el proyecto. El script instala sus dependencias con el lockfile de Bun.

Ejemplo con una versión nueva elegida por el mantenedor; sustituye `X.Y.Z` por números:

```sh
python3 scripts/preparar_release.py X.Y.Z --targets windows-x64-baseline darwin-arm64 linux-x64-baseline
```

`--help` muestra todos los targets. Sin `--targets` solo prepara Windows x64 y macOS ARM64.
Los artefactos y sus hashes reales se escriben en `dist-release/vX.Y.Z/`, junto con
`release.json`. Este paso no publica archivos ni actualiza el manifiesto de la raíz.

Prueba los artefactos en sus sistemas de destino, publícalos en el servidor elegido bajo
la versión fija y copia el manifiesto generado a la raíz del repositorio. El manifiesto
debe incluir todas las plataformas que se ofrezcan a los usuarios.

## Distribuir desde el repositorio del equipo

Puedes clonar el repositorio de origen y copiar sus fuentes al repositorio del trabajo.
Los enlaces de las guías son relativos y los ejemplos no dependen del nombre del remoto.

La documentación usa `URL_DEL_REPOSITORIO` como marcador para que cada equipo utilice su
remoto. Sin embargo, **copiar las fuentes no cambia automáticamente el origen del motor**:

| Elemento actual | Qué debe revisar el mantenedor |
|---|---|
| `RELEASE` en `instalar.py` | URL base de descarga. El instalador añade versión y nombre de artefacto |
| `FORK` y `RAMA` en `instalar.py` | Repositorio y rama usados si debe obtener las fuentes para compilar |
| `release.json` | Versión publicada y SHA-256 de cada artefacto |

Si el equipo sigue usando los binarios de origen, la descarga seguirá dependiendo de ese
servidor. Si publica sus propios binarios, debe adaptar `RELEASE` y comprobar la descarga.
`--binario-manifiesto` solo cambia versión y hashes; no permite cambiar el servidor.
El instalador actual tampoco implementa una autenticación específica para descargas de
releases privadas: ese acceso requiere una adaptación al mecanismo del servidor del equipo.

## Mantener la documentación

Las guías de uso describen lo implementado. El [proceso SDD](SDD.md) define dónde registrar
propuestas, decisiones, criterios y evidencia. Conserva el contexto histórico de los RFC
mediante aclaraciones fechadas cuando una afirmación necesite corregirse.
No marques una validación con modelos reales como terminada por pasar pruebas simuladas.
