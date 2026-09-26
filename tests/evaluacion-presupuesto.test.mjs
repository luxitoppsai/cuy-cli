import assert from 'node:assert/strict';
import { test, after } from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const carpeta = fs.mkdtempSync(path.join(os.tmpdir(), 'cuy-eval-'));
after(() => fs.rmSync(carpeta, {recursive:true, force:true}));
process.env.CUY_GASTO = path.join(carpeta,'mensual.json');
process.env.CUY_EVALUACION_GASTO = path.join(carpeta,'corrida.json');
process.env.CUY_EVALUACION_LIMITE_USD = '1';
process.env.CUY_LIMITE_USD = '10';
const { Presupuesto } = await import('../plugin/presupuesto.js');
const modelo = {model:{cost:{input:3,output:15}}};
const evento = (id,cost) => ({event:{type:'message.part.updated',properties:{part:{type:'step-finish',sessionID:'s',id,cost}}}});
function limpiar() {
  fs.writeFileSync(process.env.CUY_GASTO,'{}');
  fs.writeFileSync(process.env.CUY_EVALUACION_GASTO,'{}');
}
test('tope de corrida corta entre inferencias y conserva el mensual',async()=>{
  limpiar();
  const p=await Presupuesto({client:{}});
  await p['chat.params'](modelo);
  await p.event(evento('a',.7));
  await p.event(evento('a',.7));
  await p['chat.params'](modelo);
  await p.event(evento('b',.4));
  await assert.rejects(p['chat.params'](modelo),/Tope de evaluación/);
  assert.equal(JSON.parse(fs.readFileSync(process.env.CUY_EVALUACION_GASTO))['2000-01'],1.1);
  assert.ok(Object.values(JSON.parse(fs.readFileSync(process.env.CUY_GASTO))).includes(1.1));
});
test('costo desconocido bloquea incluso despues de un paso cero válido',async()=>{
  limpiar();
  const p=await Presupuesto({client:{}});
  await p.event(evento('c',0));
  await p['chat.params'](modelo);
  await p.event(evento('d',null));
  await assert.rejects(p['chat.params'](modelo),/ausente o inválido/);
});
test('ledger de corrida corrupto falla cerrado',async()=>{
  limpiar();
  fs.writeFileSync(process.env.CUY_EVALUACION_GASTO,'{');
  const p=await Presupuesto({client:{}});
  await assert.rejects(p['chat.params'](modelo),/no se asumirá/);
});

test('máximo inválido no rompe la fábrica y rechaza antes del proveedor', async()=>{
  limpiar();
  for (const valor of ['', 'NaN', '-1', '0', 'Infinity']) {
    process.env.CUY_EVALUACION_LIMITE_USD = valor;
    const p = await Presupuesto({client:{}});
    let llamadas = 0;
    await assert.rejects(async()=>{
      await p['chat.params'](modelo);
      llamadas++;
    }, /Presupuesto de evaluación inválido/);
    assert.equal(llamadas,0);
  }
  process.env.CUY_EVALUACION_LIMITE_USD = '1';
});
