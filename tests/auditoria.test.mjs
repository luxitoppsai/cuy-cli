/**
 * Pruebas del registro de auditoría.
 * Correr con:  node tests/auditoria.test.mjs
 */
import assert from "node:assert";
import { identidad, resumirLlamada, aplicarRetencion } from "../plugin/auditoria.js";

const pruebas = [];
const prueba = (nombre, fn) => pruebas.push([nombre, fn]);

prueba("identifica usuario y equipo", () => {
  const q = identidad();
  assert.ok(q.usuario && q.usuario.length > 0);
  assert.ok(q.equipo && q.equipo.length > 0);
});

prueba("registra el comando de bash", () => {
  assert.deepEqual(resumirLlamada("bash", { command: "rm -rf /tmp/x" }), { comando: "rm -rf /tmp/x" });
});

prueba("registra la ruta editada, no el contenido", () => {
  const r = resumirLlamada("edit", { filePath: "/src/a.py", oldString: "secreto", newString: "otro" });
  assert.deepEqual(r, { archivo: "/src/a.py" });
  assert.ok(!JSON.stringify(r).includes("secreto"), "no debe filtrar contenido");
});

prueba("recorta comandos larguísimos", () => {
  const largo = "echo " + "x".repeat(2000);
  assert.ok(resumirLlamada("bash", { command: largo }).comando.length <= 500);
});

prueba("no rompe con argumentos ausentes", () => {
  for (const t of ["bash", "edit", "webfetch", "websearch", "otra"]) {
    assert.doesNotThrow(() => resumirLlamada(t, undefined));
    assert.doesNotThrow(() => resumirLlamada(t, null));
  }
});

prueba("la retención descarta lo viejo y conserva lo reciente", () => {
  const ahora = Date.parse("2026-09-23T12:00:00Z");
  const dia = 24 * 60 * 60 * 1000;
  const lineas = [
    JSON.stringify({ cuando: new Date(ahora - 100 * dia).toISOString() }),
    JSON.stringify({ cuando: new Date(ahora - 10 * dia).toISOString() }),
  ];
  const quedan = aplicarRetencion(lineas, 90, ahora);
  assert.equal(quedan.length, 1);
  assert.ok(quedan[0].includes(new Date(ahora - 10 * dia).toISOString()));
});

prueba("retención 0 conserva todo", () => {
  const lineas = [JSON.stringify({ cuando: "2020-01-01T00:00:00Z" })];
  assert.equal(aplicarRetencion(lineas, 0).length, 1);
});

prueba("descarta líneas ilegibles", () => {
  assert.equal(aplicarRetencion(["{roto", "no json"], 90).length, 0);
});

let fallos = 0;
for (const [nombre, fn] of pruebas) {
  try { fn(); console.log(`PASS  ${nombre}`); }
  catch (e) { fallos++; console.log(`FAIL  ${nombre}: ${e.message}`); }
}
console.log(fallos ? `\n${fallos} fallo(s)` : `\n${pruebas.length} pruebas en verde`);
process.exit(fallos ? 1 : 0);
