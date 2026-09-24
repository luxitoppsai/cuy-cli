/**
 * Pruebas del tope de gasto mensual.
 * Correr con:  node tests/presupuesto.test.mjs
 */
import assert from "node:assert";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  precioDe, costoDe, buscarUso, evaluar, mesActual, leerGasto, sumarGasto,
  PRECIOS_POR_DEFECTO,
} from "../plugin/lib/presupuesto-core.js";

const pruebas = [];
const prueba = (nombre, fn) => pruebas.push([nombre, fn]);
const temporal = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), "cuy-")), "gasto.json");

prueba("reconoce el precio por familia del modelo", () => {
  assert.deepEqual(precioDe("databricks-claude-opus-4-1"), PRECIOS_POR_DEFECTO.opus);
  assert.deepEqual(precioDe("databricks-claude-haiku-4-5"), PRECIOS_POR_DEFECTO.haiku);
});

prueba("el precio declarado gana sobre el estimado", () => {
  const propio = { "databricks-claude-opus-4-1": { entrada: 1, salida: 2 } };
  assert.deepEqual(precioDe("databricks-claude-opus-4-1", propio), { entrada: 1, salida: 2 });
});

prueba("un modelo desconocido no tiene precio", () => {
  assert.equal(precioDe("databricks-gemma-3-12b"), null);
});

prueba("calcula el costo con las tarifas de Opus", () => {
  // 1M de entrada a $15 + 1M de salida a $75 = $90
  const costo = costoDe({ input_tokens: 1_000_000, output_tokens: 1_000_000 }, "claude-opus-4-1");
  assert.equal(Math.round(costo), 90);
});

prueba("acepta los nombres de contador de OpenAI", () => {
  const a = costoDe({ input_tokens: 1000, output_tokens: 0 }, "claude-haiku-4-5");
  const b = costoDe({ prompt_tokens: 1000, completion_tokens: 0 }, "claude-haiku-4-5");
  assert.equal(a, b);
});

prueba("sin precio conocido el costo es cero, no un invento", () => {
  assert.equal(costoDe({ input_tokens: 999999 }, "modelo-raro"), 0);
});

prueba("no rompe con datos ausentes o basura", () => {
  for (const caso of [null, undefined, {}, "texto", 42]) {
    assert.equal(costoDe(caso, "claude-opus-4-1"), 0);
  }
});

prueba("encuentra el uso aunque esté anidado", () => {
  const evento = { info: { message: { metadata: { usage: { input_tokens: 10 } } } } };
  assert.deepEqual(buscarUso(evento), { input_tokens: 10 });
});

prueba("el gasto se acumula por mes", () => {
  const archivo = temporal();
  assert.equal(leerGasto(archivo, "2026-09").usd, 0);
  sumarGasto(2.5, archivo, "2026-09");
  sumarGasto(1.5, archivo, "2026-09");
  assert.equal(leerGasto(archivo, "2026-09").usd, 4);
});

prueba("el mes nuevo arranca en cero sin borrar el anterior", () => {
  const archivo = temporal();
  sumarGasto(9.99, archivo, "2026-09");
  assert.equal(leerGasto(archivo, "2026-10").usd, 0, "el mes nuevo arranca limpio");
  assert.equal(leerGasto(archivo, "2026-09").usd, 9.99, "el anterior se conserva");
});

prueba("el formato del mes es AAAA-MM", () => {
  assert.equal(mesActual(new Date(2026, 0, 5)), "2026-01");
  assert.equal(mesActual(new Date(2026, 11, 31)), "2026-12");
});

prueba("deja pasar por debajo del umbral", () => {
  assert.equal(evaluar(1, 10, 80).estado, "ok");
});

prueba("avisa al llegar al porcentaje configurado", () => {
  assert.equal(evaluar(8, 10, 80).estado, "aviso");
});

prueba("corta al alcanzar el tope", () => {
  assert.equal(evaluar(10, 10, 80).estado, "excedido");
  assert.equal(evaluar(12.5, 10, 80).estado, "excedido");
});

prueba("un límite de 0 desactiva el control", () => {
  assert.equal(evaluar(999, 0, 80).estado, "ok");
});

let fallos = 0;
for (const [nombre, fn] of pruebas) {
  try { fn(); console.log(`PASS  ${nombre}`); }
  catch (e) { fallos++; console.log(`FAIL  ${nombre}: ${e.message}`); }
}
console.log(fallos ? `\n${fallos} fallo(s)` : `\n${pruebas.length} pruebas en verde`);
process.exit(fallos ? 1 : 0);
