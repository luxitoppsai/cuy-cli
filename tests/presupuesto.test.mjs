/**
 * Pruebas del tope de gasto mensual.
 * Correr con:  node tests/presupuesto.test.mjs
 *
 * Las pruebas de tarifas ya no están acá: el precio se declara una sola vez en
 * `opencode.json` y OpenCode calcula el costo. Lo que se prueba acá es de dónde se
 * saca ese costo y cómo se acumula. La traducción de DBU a dólares se prueba en
 * `tests/test_generar_config.py`.
 */
import assert from "node:assert";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  costoDelEvento, evaluar, mesActual, leerGasto, sumarGasto,
} from "../plugin/lib/presupuesto-core.js";

const pruebas = [];
const prueba = (nombre, fn) => pruebas.push([nombre, fn]);
const temporal = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), "cuy-")), "gasto.json");

const cierreDePaso = (cost) => ({
  type: "message.part.updated",
  properties: { part: { type: "step-finish", cost, sessionID: "s1" } },
});

prueba("suma el costo del cierre de paso", () => {
  assert.equal(costoDelEvento(cierreDePaso(0.42)), 0.42);
});

prueba("ignora el costo acumulado del mensaje", () => {
  // `message.updated` trae el costo **acumulado** del mensaje: sumarlo en cada
  // actualización contaría el mismo gasto muchas veces. Solo cuenta `step-finish`.
  const acumulado = { type: "message.updated", properties: { info: { cost: 5 } } };
  assert.equal(costoDelEvento(acumulado), 0);
});

prueba("ignora las partes que no cierran un paso", () => {
  const texto = {
    type: "message.part.updated",
    properties: { part: { type: "text", text: "hola" } },
  };
  assert.equal(costoDelEvento(texto), 0);
});

prueba("no rompe con eventos ausentes o basura", () => {
  for (const caso of [null, undefined, {}, "texto", 42, { type: "session.status" }]) {
    assert.equal(costoDelEvento(caso), 0);
  }
});

prueba("un costo no numérico o negativo no se oculta como cero", () => {
  for (const caso of [null, undefined, "gratis", NaN, Infinity, -1]) {
    assert.throws(() => costoDelEvento(cierreDePaso(caso)), /Costo del paso/);
  }
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
