/**
 * Pruebas de la lógica del tope de presupuesto.
 *
 * Se prueba lo que decide y lo que cuenta; la integración con OpenCode se valida
 * usándolo. Correr con:  node tests/presupuesto.test.mjs
 */
import assert from "node:assert";
import { contarTokens, buscarUso, evaluar } from "../plugin/lib/presupuesto-core.js";

const pruebas = [];
const prueba = (nombre, fn) => pruebas.push([nombre, fn]);

prueba("cuenta el formato de Anthropic", () => {
  assert.equal(contarTokens({ input_tokens: 100, output_tokens: 50 }), 150);
});

prueba("cuenta el formato de OpenAI", () => {
  assert.equal(contarTokens({ prompt_tokens: 200, completion_tokens: 30 }), 230);
});

prueba("prefiere el total cuando viene dado", () => {
  assert.equal(contarTokens({ prompt_tokens: 1, completion_tokens: 1, total_tokens: 99 }), 99);
});

prueba("no rompe con datos ausentes o basura", () => {
  for (const caso of [null, undefined, {}, "texto", 42, { usage: "no" }]) {
    assert.equal(contarTokens(caso), 0, `falló con ${JSON.stringify(caso)}`);
  }
});

prueba("encuentra el uso aunque esté anidado", () => {
  const evento = { info: { message: { metadata: { usage: { input_tokens: 10, output_tokens: 5 } } } } };
  assert.deepEqual(buscarUso(evento), { input_tokens: 10, output_tokens: 5 });
});

prueba("devuelve null si no hay uso en ningún lado", () => {
  assert.equal(buscarUso({ a: { b: { c: 1 } } }), null);
});

prueba("no entra en recursión infinita con estructuras hondas", () => {
  let hondo = { fin: true };
  for (let i = 0; i < 50; i++) hondo = { nivel: hondo };
  assert.equal(buscarUso(hondo), null);
});

prueba("deja pasar por debajo del umbral", () => {
  assert.equal(evaluar(1000, 10000, 80).estado, "ok");
});

prueba("avisa al llegar al porcentaje configurado", () => {
  assert.equal(evaluar(8000, 10000, 80).estado, "aviso");
});

prueba("corta al alcanzar el tope", () => {
  assert.equal(evaluar(10000, 10000, 80).estado, "excedido");
  assert.equal(evaluar(12000, 10000, 80).estado, "excedido");
});

prueba("un límite de 0 desactiva el control", () => {
  assert.equal(evaluar(999999, 0, 80).estado, "ok");
});

let fallos = 0;
for (const [nombre, fn] of pruebas) {
  try {
    fn();
    console.log(`PASS  ${nombre}`);
  } catch (e) {
    fallos++;
    console.log(`FAIL  ${nombre}: ${e.message}`);
  }
}
console.log(fallos ? `\n${fallos} fallo(s)` : `\n${pruebas.length} pruebas en verde`);
process.exit(fallos ? 1 : 0);
