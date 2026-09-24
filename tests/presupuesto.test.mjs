/**
 * Pruebas del tope de gasto mensual.
 * Correr con:  node tests/presupuesto.test.mjs
 */
import assert from "node:assert";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  dbuDe, costoDe, buscarUso, evaluar, mesActual, leerGasto, sumarGasto,
  DBU_POR_DEFECTO, USD_POR_DBU,
} from "../plugin/lib/presupuesto-core.js";

const pruebas = [];
const prueba = (nombre, fn) => pruebas.push([nombre, fn]);
const temporal = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), "cuy-")), "gasto.json");

prueba("la tarifa de Haiku 4.5 es la real de Databricks", () => {
  // Confirmada: 14.286 / 71.429 DBU, que a $0.07 dan $1 y $5 por millón.
  assert.deepEqual(dbuDe("databricks-claude-haiku-4-5"), { entrada: 14.286, salida: 71.429 });
  const costo = costoDe({ input_tokens: 1_000_000, output_tokens: 0 }, "claude-haiku-4-5");
  assert.equal(Math.round(costo * 100) / 100, 1);
});

prueba("reconoce la tarifa en DBU por familia del modelo", () => {
  assert.deepEqual(dbuDe("databricks-claude-opus-4-1"), DBU_POR_DEFECTO.opus);
  assert.deepEqual(dbuDe("databricks-claude-haiku-4-5"), DBU_POR_DEFECTO.haiku);
});

prueba("la tarifa declarada gana sobre la estimada", () => {
  const propio = { "databricks-claude-opus-4-1": { entrada: 1, salida: 2 } };
  assert.deepEqual(dbuDe("databricks-claude-opus-4-1", propio), { entrada: 1, salida: 2 });
});

prueba("la clave más específica gana sobre la genérica", () => {
  // "llama-3-1-8b" no debe caer en una coincidencia más corta.
  assert.deepEqual(dbuDe("databricks-meta-llama-3-1-8b-instruct"), DBU_POR_DEFECTO["llama-3-1-8b"]);
});

prueba("un modelo desconocido no tiene tarifa", () => {
  assert.equal(dbuDe("databricks-gemma-3-12b"), null);
});

prueba("convierte DBU a dólares con el factor del contrato", () => {
  // Sonnet: 42.857 DBU entrada + 214.286 salida, a $0.07/DBU = $3 + $15 = $18
  const costo = costoDe({ input_tokens: 1_000_000, output_tokens: 1_000_000 }, "claude-sonnet-4");
  assert.equal(Math.round(costo), 18);
});

prueba("un dólar por DBU distinto cambia el costo proporcionalmente", () => {
  const uso = { input_tokens: 1_000_000, output_tokens: 1_000_000 };
  const normal = costoDe(uso, "claude-sonnet-4", {}, USD_POR_DBU);
  const doble = costoDe(uso, "claude-sonnet-4", {}, USD_POR_DBU * 2);
  assert.equal(Math.round(doble), Math.round(normal * 2));
});

prueba("acepta los nombres de contador de OpenAI", () => {
  const a = costoDe({ input_tokens: 1000, output_tokens: 0 }, "claude-haiku-4-5");
  const b = costoDe({ prompt_tokens: 1000, completion_tokens: 0 }, "claude-haiku-4-5");
  assert.equal(a, b);
});

prueba("sin tarifa conocida el costo es cero, no un invento", () => {
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
