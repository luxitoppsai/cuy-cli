# Evidencia — RFC-006

2026-10-08. Implementación y paquete de validación; no se publicó una release.

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

## Plataformas y publicación pendientes

Windows y Linux no se ejecutaron en esta Mac. El workflow manual prepara paquetes
en sus runners nativos; Windows x64 añade un instalador Inno Setup y comprueba una
instalación silenciosa. Ese camino todavía necesita ejecutarse. No hay `.exe` de
instalación validado ni release nueva publicada. La versión distribuida anterior
del motor y la selección local del usuario siguen sin reemplazarse.

El repositorio remoto actual se verificó público. El usuario aceptó mantener las
fuentes públicas y distribuir mediante Releases allí para llegar primero a una
versión estable. El ajuste se conserva fuera del README de uso.

No hay firma corporativa validada, sandbox ni protección contra extracción del código,
alteración de contabilidad, reloj, precios o uso directo del token en otro cliente.
Las pruebas sintéticas no miden calidad de modelos ni exactitud de la facturación.
