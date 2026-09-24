/**
 * Pruebas de la redacción de secretos (RFC-002).
 * Correr con:  node tests/secretos.test.mjs
 *
 * Cada patrón tiene un caso que **debe** redactarse y uno que **no**. Lo segundo importa
 * más: un falso positivo hace que el modelo vea `[REDACTADO]` donde había código bueno y
 * razone sobre una mentira, que es peor que dejar pasar un caso raro.
 */
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  redactar, rutaProhibida, rutaProhibidaEnComando, rutaDe,
} from "../plugin/lib/secretos-core.js";

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pruebas = [];
const prueba = (nombre, fn) => pruebas.push([nombre, fn]);

const redacta = (texto) => redactar(texto).hallazgos.length > 0;

// --- Rutas que se rechazan enteras ------------------------------------------------

prueba("rechaza los archivos cuyo contenido es el secreto", () => {
  for (const ruta of [
    ".env", "proyecto/.env", ".env.production", ".env.local", "C:\\repo\\.env",
    "llave.pem", "cert.p12", "~/.ssh/id_rsa", "/home/luis/.ssh/config",
    ".credentials.json", "terraform.tfvars", ".npmrc", ".databrickscfg",
    "/Users/luis/.aws/credentials", "service-account-prod.json",
  ]) {
    assert.ok(rutaProhibida(ruta), `deberia rechazar ${ruta}`);
  }
});

prueba("no rechaza archivos normales que se le parecen", () => {
  for (const ruta of [
    "generar_config.py", ".env.example", ".env.example.md", ".env.sample",
    "config.template.json", "environment.yml", "docs/env.md",
    "README.md", "src/credentials_test.py", "plugin/secretos.js",
  ]) {
    assert.ok(!rutaProhibida(ruta), `no deberia rechazar ${ruta}`);
  }
});

prueba("encuentra la ruta prohibida dentro de un comando", () => {
  assert.equal(rutaProhibidaEnComando("cat .env"), ".env");
  assert.equal(rutaProhibidaEnComando("grep TOKEN ~/.aws/credentials"), "~/.aws/credentials");
  assert.equal(rutaProhibidaEnComando("cat README.md"), null);
  assert.equal(rutaProhibidaEnComando("python generar_config.py"), null);
});

prueba("saca la ruta de los argumentos sin asumir el nombre del campo", () => {
  assert.equal(rutaDe({ filePath: "a.txt" }), "a.txt");
  assert.equal(rutaDe({ path: "b.txt" }), "b.txt");
  assert.equal(rutaDe({ command: "ls" }), null);
  assert.equal(rutaDe(null), null);
});

// --- Patrones con forma inconfundible ---------------------------------------------

prueba("redacta un PAT de Databricks", () => {
  // Se arma en tiempo de ejecución a propósito: un PAT literal en el archivo lo hace
  // indistinguible de uno real para cualquier escáner —GitHub rechaza el push— y para
  // quien lo lea de paso. Vale para todos los patrones de este archivo.
  const pat = "dapi" + "0123456789abcdef".repeat(2);
  const { texto, hallazgos } = redactar(`DATABRICKS_TOKEN=${pat}`);
  assert.ok(!texto.includes(pat));
  assert.equal(hallazgos[0].tipo, "databricks-pat");
});

prueba("no redacta la palabra dapi suelta ni el patrón escrito como texto", () => {
  // El propio RFC documenta el regex `dapi[0-9a-f]{32}`: no debe redactarse a sí mismo.
  assert.ok(!redacta("el token empieza con dapi seguido de 32 hex"));
  assert.ok(!redacta("Databricks PAT: `dapi[0-9a-f]{32}`"));
});

prueba("redacta claves de AWS, GitHub, Slack, OpenAI, Anthropic y Google", () => {
  const casos = {
    "aws-access-key": "AKIAIOSFODNN7EXAMPLE",
    github: "ghp_" + "a".repeat(36),
    slack: "xoxb-123456789012-abcdefghijkl",
    openai: "sk-" + "A1b2C3d4E5f6G7h8I9j0",
    anthropic: "sk-ant-" + "A1b2C3d4E5f6G7h8I9j0",
    "google-api-key": "AIza" + "B".repeat(35),
  };
  for (const [tipo, valor] of Object.entries(casos)) {
    const { texto, hallazgos } = redactar(`clave: ${valor}`);
    assert.ok(!texto.includes(valor), `no redactó ${tipo}`);
    assert.equal(hallazgos[0].tipo, tipo, `tipo equivocado para ${tipo}`);
  }
});

prueba("redacta un bloque de clave privada entero", () => {
  const bloque = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow...\nlineas\n-----END RSA PRIVATE KEY-----";
  const { texto } = redactar(`antes\n${bloque}\ndespues`);
  assert.ok(texto.includes("antes") && texto.includes("despues"), "conserva el contexto");
  assert.ok(!texto.includes("MIIEow"), "borra el cuerpo");
});

// --- Asignaciones explícitas ------------------------------------------------------

prueba("redacta un secreto asignado entre comillas", () => {
  const { texto } = redactar('PASSWORD = "verano2026!"');
  assert.ok(!texto.includes("verano2026"));
  assert.ok(texto.includes("PASSWORD"), "conserva la clave para que el modelo entienda");
});

prueba("no toca el código normal que menciona esas palabras", () => {
  // Es el falso positivo que rompería el trabajo todo el tiempo: sin comillas es una
  // referencia a una variable, no un secreto pegado a mano.
  for (const linea of [
    "token = response.token",
    "self.api_key = os.environ['CLAVE']",
    "const secret = await vault.get(nombre)",
    "if (password !== confirmacion) return",
    "def validar(api_key: str) -> bool:",
  ]) {
    assert.ok(!redacta(linea), `falso positivo en: ${linea}`);
  }
});

prueba("no toca los placeholders de la propia configuración", () => {
  for (const linea of [
    '"apiKey": "{env:DATABRICKS_TOKEN}"',
    '"Authorization": "Bearer {env:DATABRICKS_TOKEN}"',
    'password = "<tu-contraseña>"',
    'api_key = "********"',
    'secret = "changeme"',
    'PASSWORD="${DB_PASSWORD}"',
  ]) {
    assert.ok(!redacta(linea), `falso positivo en: ${linea}`);
  }
});

prueba("conserva la forma del archivo alrededor de lo redactado", () => {
  const original = 'linea uno\nAPI_KEY = "A1b2C3d4E5f6"\nlinea tres';
  const { texto } = redactar(original);
  assert.equal(texto.split("\n").length, 3, "no borra ni agrega lineas");
  assert.ok(texto.startsWith("linea uno") && texto.endsWith("linea tres"));
});

prueba("no rompe con entradas vacías o que no son texto", () => {
  for (const caso of [null, undefined, "", 42, {}]) {
    assert.deepEqual(redactar(caso).hallazgos, []);
  }
});

// --- Criterio 3 del RFC: nada de falsos positivos sobre este mismo repo -----------

prueba("el propio repo se lee intacto (criterio 3 del RFC)", () => {
  const archivos = [
    "generar_config.py", "instalar.py", "cuy.py", "gasto.py", "auditar.py",
    "plugin/secretos.js", "plugin/presupuesto.js", "plugin/auditoria.js",
    "plugin/lib/secretos-core.js", "plugin/lib/presupuesto-core.js",
    "README.md", "RFC.md", "docs/rfc/RFC-002-redaccion-de-secretos.md",
    "spike/probar_anthropic.py",
  ];
  const sucios = [];
  for (const relativo of archivos) {
    const completo = path.join(RAIZ, relativo);
    if (!fs.existsSync(completo)) continue;
    const { hallazgos } = redactar(fs.readFileSync(completo, "utf8"));
    if (hallazgos.length) sucios.push(`${relativo}: ${JSON.stringify(hallazgos)}`);
  }
  assert.deepEqual(sucios, [], `falsos positivos:\n  ${sucios.join("\n  ")}`);
});

let fallos = 0;
for (const [nombre, fn] of pruebas) {
  try { fn(); console.log(`PASS  ${nombre}`); }
  catch (e) { fallos++; console.log(`FAIL  ${nombre}: ${e.message}`); }
}
console.log(fallos ? `\n${fallos} fallo(s)` : `\n${pruebas.length} pruebas en verde`);
process.exit(fallos ? 1 : 0);
