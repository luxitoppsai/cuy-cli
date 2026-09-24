/**
 * Verifica que los plugins declaren hooks que OpenCode de verdad invoca.
 * Correr con:  node tests/hooks.test.mjs
 *
 * **Por qué existe esta prueba.** OpenCode recorre los hooks por nombre contra su
 * interfaz `Hooks` y **descarta en silencio** cualquier clave que no esté ahí: no hay
 * error, no hay aviso, el handler simplemente no se llama nunca. El presupuesto declaró
 * `"message.updated"` y `"message.part.updated"` —que son nombres de *eventos*, no de
 * hooks— y por eso no contó un centavo durante toda la vida del proyecto. La auditoría
 * tenía lo mismo con `"permission.asked"` (el hook es `permission.ask`) y `"session.idle"`.
 *
 * La lista de nombres válidos se lee del código vendorizado, no se copia acá: si
 * OpenCode renombra un hook al actualizar el subtree, esta prueba se entera.
 */
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const INTERFAZ = path.join(RAIZ, "vendor/opencode/packages/plugin/src/index.ts");

/**
 * Lee los nombres de hook válidos de la interfaz `Hooks` de OpenCode.
 *
 * @returns {Set<string>} Nombres que `Plugin.trigger` puede invocar.
 */
function hooksValidos() {
  const fuente = fs.readFileSync(INTERFAZ, "utf8");
  const bloque = fuente.slice(fuente.indexOf("export interface Hooks {"));
  const validos = new Set();
  // Solo las claves al primer nivel de indentación: las de adentro son campos de los
  // objetos de entrada y salida, no hooks.
  for (const linea of bloque.split("\n")) {
    const m = linea.match(/^ {2}"?([a-zA-Z][a-zA-Z0-9.]*)"?\??:/);
    if (m) validos.add(m[1]);
    if (linea === "}") break;
  }
  return validos;
}

const pruebas = [];
const prueba = (nombre, fn) => pruebas.push([nombre, fn]);

prueba("la interfaz Hooks se pudo leer del vendor", () => {
  const validos = hooksValidos();
  assert.ok(validos.size > 5, `se leyeron ${validos.size} hooks, parece un parseo roto`);
  // Anclas: si estas tres desaparecen, cambió algo de fondo y hay que mirar.
  for (const ancla of ["event", "tool.execute.before", "config"]) {
    assert.ok(validos.has(ancla), `falta el hook conocido "${ancla}"`);
  }
});

prueba("todo hook declarado por los plugins existe en OpenCode", async () => {
  process.env.CUY_AUDITORIA_OFF = "1"; // que la prueba no escriba el registro real
  const validos = hooksValidos();

  const { Presupuesto } = await import("../plugin/presupuesto.js");
  const { Auditoria } = await import("../plugin/auditoria.js");

  const plugins = {
    Presupuesto: await Presupuesto({ client: {} }),
    Auditoria: await Auditoria({ directory: RAIZ }),
  };

  for (const [nombre, hooks] of Object.entries(plugins)) {
    for (const clave of Object.keys(hooks)) {
      assert.ok(
        validos.has(clave),
        `${nombre} declara "${clave}", que OpenCode nunca invoca. ` +
          `Si es un evento, va adentro del hook "event".`
      );
    }
  }
});

prueba("los plugins exportan una sola cosa", async () => {
  // OpenCode invoca **cada export** como fábrica de plugins: un helper exportado de más
  // rompe la carga y deja la configuración nula.
  for (const archivo of ["../plugin/presupuesto.js", "../plugin/auditoria.js"]) {
    const modulo = await import(archivo);
    const exports = Object.keys(modulo);
    assert.equal(exports.length, 1, `${archivo} exporta ${exports.join(", ")}`);
    assert.equal(typeof modulo[exports[0]], "function");
  }
});

let fallos = 0;
for (const [nombre, fn] of pruebas) {
  try { await fn(); console.log(`PASS  ${nombre}`); }
  catch (e) { fallos++; console.log(`FAIL  ${nombre}: ${e.message}`); }
}
console.log(fallos ? `\n${fallos} fallo(s)` : `\n${pruebas.length} pruebas en verde`);
process.exit(fallos ? 1 : 0);
