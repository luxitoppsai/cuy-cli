/** Exclusión entre procesos y reemplazo atómico sin dependencias nativas. */
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";

export function conBloqueo(archivo, operacion) {
  fs.mkdirSync(path.dirname(archivo), { recursive: true });
  const lock = `${archivo}.lock`;
  const hasta = Date.now() + 2000;
  let fd;
  while (fd === undefined) {
    try { fd = fs.openSync(lock, "wx", 0o600); }
    catch (error) {
      if (error.code !== "EEXIST") throw error;
      if (Date.now() >= hasta) throw new Error(`Archivo ocupado: ${lock}. Revisá procesos activos antes de recuperar el lock.`);
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 20);
    }
  }
  try { return operacion(); }
  finally { fs.closeSync(fd); fs.unlinkSync(lock); }
}

export function escribirAtomico(archivo, contenido) {
  const temporal = `${archivo}.${randomUUID()}.tmp`;
  try {
    const fd = fs.openSync(temporal, "wx", 0o600);
    try { fs.writeFileSync(fd, contenido); fs.fsyncSync(fd); }
    finally { fs.closeSync(fd); }
    fs.renameSync(temporal, archivo);
  } finally {
    if (fs.existsSync(temporal)) fs.unlinkSync(temporal);
  }
}
