# Evidencia — RFC-006

2026-10-08 a 2026-10-12. Implementación y validación de la distribución 0.4.4.

## Observado

- Suite Python completa: 161 pruebas, 0 fallos y 14 omisiones optativas en la corrida
  general. Después se añadió la regresión de discrepancia de política: pasó dentro
  de las 7 pruebas locales de distribución (4 contratos del paquete se omiten si no
  se configura el ejecutable).
- JavaScript: `npm test`, 15 casos del runner correctos, además de los grupos internos.
  La nueva regresión prueba que `0`, importes mayores, negativos y NaN del entorno
  no modifican el límite ni el umbral de aviso.
- Motor: `bun typecheck` correcto; 80 pruebas de write/edit/apply_patch correctas.
- Compilado de mantenimiento con presupuesto USD 14: 8 contratos del motor,
  7 correctos y 1 omitido por no configurar CodeGraph. La política declara 14 y el
  agotamiento bloquea inferencia incluso sin plugins externos, con plugins opcionales
  deshabilitados y un intento de desactivar el presupuesto por entorno.
- Paquete final de validación `0.4.4-preview`, darwin-x64, presupuesto USD 10:
  generado con PyInstaller 6.22.3 y Python 3.12.8, motor Bun x64 incluido. No requiere
  intérpretes externos. Es x64; su ejecución en la Mac ARM del mantenedor usa Rosetta.
- Los 11 casos de distribución pasan con el paquete real y CodeGraph real: 7 locales
  y 4 contratos. PATH apunta a una carpeta sin intérpretes. Se verifican instalación,
  reinstalación, ayuda, versión, diagnóstico, gasto y MCP con búsqueda de `alpha`.
- Los 8 contratos del motor incluido en `_internal/motor` pasan: 7 correctos y
  1 omisión del contrato MCP integrado del motor. MCP del ejecutable empaquetado sí
  se verificó en el punto anterior. No se llamó a Databricks.
- Inspección del paquete: sin fuentes `.py`, `.js`, `.ts`, `.env` ni configuración
  privada; incluye recursos de uso, runtime y licencias. Manifiesto SHA-256 generado.
- Trazabilidad: 5 comprobaciones correctas; revisión del diff sin errores de espacios.

## Validación nativa de 0.4.4

El [workflow de paquetes](https://github.com/luxitoppsai/cuy-cli/actions/runs/37886765941)
pasó en Windows x64, macOS ARM64 y Linux x64, con el commit
`ff23a8a3b6eef7d81d7f7bfe44fa8b2acd9d16d8`. Ejecutó los contratos del motor y
del paquete en cada runner. Windows produjo el instalador Inno Setup, lo instaló
en una carpeta temporal y ejecutó la aplicación instalada. Las pruebas generales
del mismo commit también pasaron en los tres sistemas.

La primera ejecución detectó salida ANSI del Python congelado en Windows:
`PYTHONUTF8` no configura ese runtime. Se fijó UTF-8 en la entrada compilada y se
añadió una regresión. La segunda detectó una constante de carpeta inválida en los
accesos de Inno Setup; se sustituyó por el directorio de instalación.

Los cuatro manifiestos descargados coinciden con sus archivos por SHA-256. Los ZIP
no contienen fuentes sueltas ni configuración privada. El ZIP final de macOS ARM64
se ejecutó también en la Mac del mantenedor: sus 12 pruebas de distribución pasaron,
incluido MCP con CodeGraph real y PATH sin intérpretes. CodeGraph real no se ejecutó
en los runners Windows/Linux; sus contratos optativos se omiten allí.

El manifiesto del motor antiguo y la selección local del usuario se conservan.

La [Release 0.4.4](https://github.com/luxitoppsai/cuy-cli/releases/tag/v0.4.4)
se publicó el 2026-10-12 con los tres ZIP, el instalador Windows y sus cuatro
manifiestos SHA-256. No está marcada como prerelease.

El repositorio remoto actual se verificó público. El usuario aceptó mantener las
fuentes públicas y distribuir mediante Releases allí para llegar primero a una
versión estable. El ajuste se conserva fuera del README de uso.

No hay firma corporativa validada, sandbox ni protección contra extracción del código,
alteración de contabilidad, reloj, precios o uso directo del token en otro cliente.
Las pruebas sintéticas no miden calidad de modelos ni exactitud de la facturación.
