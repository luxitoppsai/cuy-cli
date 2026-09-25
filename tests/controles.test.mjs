import assert from "node:assert/strict";
import { test, after } from "node:test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { pathToFileURL } from "node:url";

const root = fs.mkdtempSync(path.join(os.tmpdir(), "cuy-controles-"));
process.env.CUY_GASTO = path.join(root, "gasto.json");
process.env.CUY_AUDITORIA = path.join(root, "auditoria.jsonl");
process.env.CUY_LIMITE_USD = "10";
after(() => fs.rmSync(root, { recursive: true, force: true }));
const { leerGasto, sumarGasto, mesActual } = await import("../plugin/lib/presupuesto-core.js");
const { Presupuesto } = await import("../plugin/presupuesto.js");
const { Auditoria } = await import("../plugin/auditoria.js");
const { redactar, sanearRegistro } = await import("../plugin/lib/secretos-core.js");
const modelo = { model: { cost: { input: 3, output: 15 } } };

const evento = (id, cost = 2) => ({ event: { type: "message.part.updated", properties: {
  part: { id, sessionID: "s1", type: "step-finish", cost },
} } });

test("presupuesto bloquea ANTES de inferencia, sin llamada a herramientas", async () => {
  const plugin = await Presupuesto({ client: {} });
  fs.writeFileSync(process.env.CUY_GASTO, JSON.stringify({ [mesActual()]: 10 }));
  await assert.rejects(plugin["chat.params"](modelo), /Tope mensual/);
  // Se relee el disco: otra sesión y el cambio de mes no quedan en caché.
  fs.writeFileSync(process.env.CUY_GASTO, JSON.stringify({ "2020-01": 99 }));
  await plugin["chat.params"](modelo);
  await assert.rejects(plugin["chat.params"]({ model: {} }), /sin tarifa/);
});

test("cierre duplicado se contabiliza una sola vez", async () => {
  fs.writeFileSync(process.env.CUY_GASTO, "{}");
  const plugin = await Presupuesto({ client: {} });
  await plugin.event(evento("p1"));
  await plugin.event(evento("p1"));
  await plugin.event(evento("p2"));
  assert.equal(leerGasto().usd, 4);
});

test("corrupción y error de escritura nunca se convierten en gasto cero", async () => {
  fs.writeFileSync(process.env.CUY_GASTO, "{roto");
  assert.throws(() => leerGasto(), /no se asumirá/);
  const plugin = await Presupuesto({ client: {} });
  await assert.rejects(plugin["chat.params"](modelo), /no se asumirá/);
  await plugin.event(evento("p3"));
  fs.writeFileSync(process.env.CUY_GASTO, "{}");
  await assert.rejects(plugin["chat.params"](modelo), /no se asumirá/);
});

test("dos procesos conservan todas sus actualizaciones", async () => {
  const archivo = path.join(root, "paralelo.json");
  const modulo = pathToFileURL(path.resolve("plugin/lib/presupuesto-core.js")).href;
  const codigo = `import {sumarGasto} from ${JSON.stringify(modulo)}; for(let n=0;n<20;n++) sumarGasto(1, process.argv[1]);`;
  const correr = () => new Promise((resolve, reject) => {
    const hijo = spawn(process.execPath, ["--input-type=module", "-e", codigo, archivo]);
    let error = "";
    hijo.stderr.on("data", (d) => { error += d; });
    hijo.on("error", reject);
    hijo.on("close", (code) => code === 0 ? resolve() : reject(new Error(error)));
  });
  await Promise.all([correr(), correr(), correr()]);
  assert.equal(leerGasto(archivo).usd, 60);
});

test("redacta JSON, escapes, cabeceras y argumentos sin filtrar valores", () => {
  for (const texto of ['{"password":"secreto-falso"}', 'password = "abc\\"def"', 'Authorization: Bearer abcdefghijklmnop']) {
    assert.ok(redactar(texto).hallazgos.length);
  }
  const safe = sanearRegistro({ command: "curl https://x?token=secreto-falso --password secreto-otro" });
  assert.ok(!JSON.stringify(safe).includes("secreto-falso"));
  assert.ok(!JSON.stringify(safe).includes("secreto-otro"));
});

test("audita intentos, errores y permisos con IDs reales, sin secretos", async () => {
  const plugin = await Auditoria({ directory: root });
  const token = "dapi" + "a".repeat(32);
  await plugin["tool.execute.before"]({ sessionID: "ses-real", callID: "call-real", tool: "bash" }, { args: { command: `echo ${token}` } });
  await plugin.event({ event: { type: "message.part.updated", properties: { part: {
    type: "tool", id: "part-real", sessionID: "ses-real", callID: "call-real", tool: "bash",
    state: { status: "error", input: { command: `echo ${token}` }, error: "contenido confidencial" },
  } } } });
  await plugin.event({ event: { type: "permission.asked", properties: { sessionID: "ses-real", id: "perm-real", permission: "bash", patterns: ["npm test"] } } });
  const text = fs.readFileSync(process.env.CUY_AUDITORIA, "utf8");
  assert.ok(!text.includes(token));
  assert.ok(!text.includes("contenido confidencial"));
  const records = text.trim().split("\n").map(JSON.parse);
  assert.deepEqual(records.map((r) => r.evento), ["herramienta.intento", "herramienta.resultado", "permiso.consultado"]);
  assert.ok(records.every((r) => r.sesion === "ses-real"));
  assert.equal(records[1].estado, "error");
});
