import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";

test("el entorno no cambia ni desactiva el presupuesto fijo", () => {
  for (const valor of ["0", "99999", "NaN", "-1"]) {
    const codigo = 'import {LIMITE_USD,AVISO} from "./plugin/lib/presupuesto-core.js"; console.log(JSON.stringify({limite:LIMITE_USD,aviso:AVISO}));';
    const result = spawnSync(process.execPath, ["--input-type=module", "-e", codigo], {
      env: { ...process.env, CUY_LIMITE_USD: valor, CUY_AVISO_PORCENTAJE: "999" }, encoding: "utf8",
    });
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(JSON.parse(result.stdout), { limite: 10, aviso: 80 });
  }
});
