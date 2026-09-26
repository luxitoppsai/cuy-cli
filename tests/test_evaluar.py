"""Integración del evaluador con Git real y motor sustituido, sin inferencia."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import evaluar
import tareas


class EvaluacionTests(unittest.TestCase):
    """Regresiones de aislamiento, clasificación y contabilidad incompleta."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.casos = evaluar.cargar_casos(evaluar.RAIZ/'evaluacion/casos')
        self.env = {**os.environ, 'OPENCODE_CONFIG_CONTENT':json.dumps({'model':'cuy/a','provider':{'cuy':{'models':{'a':{'cost':{'input':1,'output':2}},'b':{'cost':{'input':1,'output':2}}}}}}), 'CUY_GASTO': str(self.raiz/'mensual.json'), 'CUY_LIMITE_USD': '10'}

    def test_diez_bases_rojas_sin_modelo_y_sin_residuos(self):
        antes = tareas.foto(evaluar.RAIZ)
        with patch.object(tareas, 'correr_tarea', side_effect=AssertionError('no inferir')):
            r = evaluar.correr(self.casos, self.raiz/'seco.json', self.env, None, None, True)
        self.assertEqual(len(r['casos']), 10)
        self.assertTrue(all(c['resultado'] == 'base_roja' for c in r['casos']))
        self.assertEqual(tareas.foto(evaluar.RAIZ), antes)
        for k in ('tasa_resolucion','costo_usd','costo_mediano_usd','duracion_total_s','duracion_mediana_s'):
            self.assertIn(k, r['metricas'])

    def test_repo_un_commit_sin_historia(self):
        destino = self.raiz/'caso'
        evaluar.materializar(self.casos[0], destino)
        self.assertEqual(tareas.git(destino, 'rev-list', '--all', '--count').strip(), b'1')
        self.assertFalse((destino/'.git/objects/info/alternates').exists())
        self.assertEqual(tareas.git(destino, 'remote').strip(), b'')

    def test_clasificacion_no_infiere_pasos(self):
        base = {'test.py': 'hash'}
        self.assertEqual(evaluar.clasificar({'estado':'verificada'},base,base),'resuelto')
        self.assertEqual(evaluar.clasificar({'estado':'sin_verificar','archivos':['a'],'pasos':30,'reason':'length'},base,base),'sin_verificar')
        self.assertEqual(evaluar.clasificar({'estado':'verificada'},base,{}),'test_modificado')
        self.assertEqual(evaluar.clasificar({'estado':'error'},base,base),'error')

    def test_eventos_parciales_y_cero_real(self):
        def evento(i, costo):
            return json.dumps({'type':'step_finish','part':{'id':i,'cost':costo}})
        r=tareas.leer_eventos('\n'.join([evento('1',.25),evento('1',.25),evento('2',None)]))
        self.assertEqual(r['costo_usd'],.25)
        self.assertEqual((r['pasos_con_costo'],r['pasos_sin_costo']),(1,1))
        self.assertFalse(r['costo_completo'])
        self.assertIsNone(tareas.leer_eventos(evento('1',None))['costo_usd'])
        self.assertTrue(tareas.leer_eventos(evento('1',0))['costo_completo'])

    def test_exige_presupuesto_sin_iniciar_motor(self):
        with patch.object(tareas,'correr_tarea') as motor:
            for valor in (None,0,-1,float('nan'),float('inf')):
                with self.assertRaises(ValueError):
                    evaluar.correr(self.casos,self.raiz/'r.json',self.env,Path('motor'),valor)
            motor.assert_not_called()

    def simulado(self, *args):
        proyecto=args[2]
        return {'estado':'verificada','fase':'motor_finalizado','limite_pasos_configurado':30,'trabajo':str(proyecto),'costo_usd':.1,
                'costo_completo':True,'pasos':1,'pasos_con_costo':1,'pasos_sin_costo':0,'archivos':['modulo.py']}

    def corrida(self, funcion, nombre='r.json', casos=None, materializador=None):
        with patch.object(tareas,'correr_tarea',side_effect=funcion), patch.object(evaluar.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'test-version')):
            # No sustituir Git: materializar usa subprocess.run también.
            with patch.object(evaluar,'materializar',side_effect=materializador or (lambda c,p: __import__('shutil').copytree(c['origen'],p))):
                return evaluar.correr(casos or self.casos,self.raiz/nombre,self.env,Path('motor'),1)

    def test_motor_real_camino_y_contabilidad_parcial_detiene(self):
        def parcial(*args):
            r=self.simulado(*args)
            r.update(costo_completo=False,pasos_sin_costo=1)
            return r
        r=self.corrida(parcial)
        self.assertEqual(r['metricas']['iniciados'],1)
        self.assertEqual(r['estado'],'contabilidad_incompleta')
        self.assertEqual(r['metricas']['etiqueta_costo'],'total parcial')
        self.assertIsNone(r['metricas']['costo_mediano_usd'])

    def test_intocable_borrado_aunque_motor_diga_verificada(self):
        def tramposo(*args):
            r=self.simulado(*args)
            (args[2]/'test_regresion.py').unlink()
            return r
        r=self.corrida(tramposo,casos=self.casos[:1])
        self.assertEqual(r['casos'][0]['resultado'],'test_modificado')

    def test_interrupcion_conserva_informe(self):
        contador=0
        def interrumpir(*args):
            nonlocal contador
            contador+=1
            if contador==2:
                raise KeyboardInterrupt
            return self.simulado(*args)
        r=self.corrida(interrumpir)
        self.assertEqual(r['estado'],'interrumpida')
        self.assertEqual(json.loads((self.raiz/'r.json').read_text())['metricas']['iniciados'],2)
        self.assertFalse(r['metricas']['costo_completo'])

    def test_fallo_con_costo_no_impide_siguiente_caso(self):
        def fallar(*args):
            r=self.simulado(*args)
            r['estado']='error'
            return r
        r=self.corrida(fallar)
        self.assertEqual(len(r['casos']),10)
        self.assertEqual(r['metricas']['resueltos'],0)

    def test_limite_corrida_y_mensual(self):
        def agotar(*args):
            Path(args[4]['CUY_EVALUACION_GASTO']).write_text('{"2000-01":1}')
            return self.simulado(*args)
        r=self.corrida(agotar)
        self.assertEqual(r['estado'],'presupuesto_agotado')
        self.assertEqual(r['metricas']['iniciados'],1)
        mes=evaluar.datetime.now().strftime('%Y-%m')
        (self.raiz/'mensual.json').write_text(json.dumps({mes:10}))
        r=self.corrida(self.simulado,'mensual-r.json')
        self.assertEqual(r['estado'],'presupuesto_mensual_agotado')
        self.assertTrue(all(c['resultado']=='no_ejecutado' for c in r['casos']))

    def test_configuraciones_comparables_sin_secretos(self):
        config=json.loads(self.env['OPENCODE_CONFIG_CONTENT'])
        config['secreto']='no-exportar'
        self.env['OPENCODE_CONFIG_CONTENT']=json.dumps(config)
        a=self.corrida(self.simulado,'a.json')
        config['model']='cuy/b'
        self.env['OPENCODE_CONFIG_CONTENT']=json.dumps(config)
        b=self.corrida(self.simulado,'b.json')
        self.assertEqual(set(a),set(b))
        self.assertEqual(a['metricas']['resueltos'],10)
        self.assertAlmostEqual(a['metricas']['costo_usd'],1)
        self.assertEqual(a['metricas']['costo_mediano_usd'],.1)
        self.assertEqual(a['metricas']['tasa_resolucion'],1)
        self.assertEqual(a['conjunto_sha256'],b['conjunto_sha256'])
        self.assertNotEqual(a['config_modelos_sha256'],b['config_modelos_sha256'])
        self.assertNotIn('no-exportar',(self.raiz/'a.json').read_text())

    def test_pipeline_real_worktree_pruebas_y_base_ya_verde(self):
        original = tareas.ejecutar_proceso
        run_original = subprocess.run
        self.env['OPENCODE_CONFIG_CONTENT'] = json.dumps({'model':'cuy/test', 'provider':{'cuy':{'models':{'test':{'cost':{'input':1,'output':2}}}}}})
        caso = self.casos[-1]
        imposible = False
        def proceso(argv, carpeta, env, limite, entrada=None):
            if argv[0] != 'motor-falso':
                return original(argv, carpeta, env, limite, entrada)
            ruta = carpeta/'modulo.py'
            ruta.write_text(ruta.read_text()+'\n# intento insuficiente\n' if imposible else 'import copy\n'+ruta.read_text().replace('return dict(PERMISOS_BASE)','return copy.deepcopy(PERMISOS_BASE)'))
            entrega = {'resumen':'Corregido', 'referencias':[{'archivo':'modulo.py','linea':1,'explicacion':'copia independiente'}], 'hallazgos':[]}
            eventos = [ {'type':'step_finish','part':{'id':'p1','cost':.02}},
                        {'type':'text','part':{'text':json.dumps(entrega)}} ]
            return 0, '\n'.join(json.dumps(e) for e in eventos), False
        def version(argv, **kwargs):
            if argv == ['motor-falso','--version']:
                return subprocess.CompletedProcess(argv,0,'test-version')
            return run_original(argv, **kwargs)
        with patch.object(tareas,'ejecutar_proceso',side_effect=proceso), patch.object(subprocess,'run',side_effect=version):
            r=evaluar.correr([caso],self.raiz/'pipeline.json',self.env,Path('motor-falso'),1)
        self.assertEqual(r['casos'][0]['resultado'],'resuelto',r)
        self.assertEqual(r['metricas']['costo_usd'],.02)
        imposible = True
        with patch.object(tareas,'ejecutar_proceso',side_effect=proceso), patch.object(subprocess,'run',side_effect=version):
            r=evaluar.correr([caso],self.raiz/'imposible.json',self.env,Path('motor-falso'),1)
        self.assertEqual(r['casos'][0]['resultado'],'sin_verificar',r)
        # El caso ya arreglado no exige cambios artificiales para verificarlo.
        import shutil
        proyecto = self.raiz/'arreglado'
        shutil.copytree(caso['origen'],proyecto)
        ruta = proyecto/'modulo.py'
        ruta.write_text('import copy\n'+ruta.read_text().replace('return dict(PERMISOS_BASE)','return copy.deepcopy(PERMISOS_BASE)'))
        arreglado={**caso,'origen':proyecto}
        def sin_editar(argv, carpeta, env, limite, entrada=None):
            if argv[0] != 'motor-falso':
                return original(argv,carpeta,env,limite,entrada)
            entrega={'resumen':'Ya correcto','referencias':[],'hallazgos':[]}
            return 0,json.dumps({'type':'text','part':{'text':json.dumps(entrega)}})+'\n'+json.dumps({'type':'step_finish','part':{'id':'p2','cost':.01}}),False
        with patch.object(tareas,'ejecutar_proceso',side_effect=sin_editar), patch.object(subprocess,'run',side_effect=version):
            r=evaluar.correr([arreglado],self.raiz/'verde.json',self.env,Path('motor-falso'),1)
        self.assertEqual(r['casos'][0]['resultado'],'resuelto',r)
        preparar_original=tareas.preparar_entorno
        def siete(env, flujo, carpeta):
            nuevo,agente=preparar_original(env,flujo,carpeta)
            config=json.loads(nuevo['OPENCODE_CONFIG_CONTENT'])
            config['agent'][agente]['steps']=7
            return {**nuevo,'OPENCODE_CONFIG_CONTENT':json.dumps(config)},agente
        with patch.object(tareas,'ejecutar_proceso',side_effect=sin_editar), patch.object(subprocess,'run',side_effect=version), patch.object(tareas,'preparar_entorno',side_effect=siete):
            r=evaluar.correr([caso],self.raiz/'sin-cambios.json',self.env,Path('motor-falso'),1)
        self.assertEqual(r['casos'][0]['resultado'],'sin_cambios',r)
        self.assertEqual(r['casos'][0]['codigo_motivo'],'sin_cambios')
        self.assertEqual(r['casos'][0]['limite_pasos_configurado'],7)
        self.assertEqual(r['casos'][0]['fase'],'motor_finalizado')

    def test_config_alternativa_no_muta_politicas_ni_original(self):
        config={'model':'cuy/a','provider':{'cuy':{'models':{'a':{},'b':{}}}},'permission':{'*':'deny'}}
        antes=json.dumps(config)
        nueva=evaluar.seleccionar_modelos(config,{'model':'cuy/b','agent':{'explore':{'model':'cuy/a'}}})
        self.assertEqual(nueva['model'],'cuy/b')
        self.assertEqual(json.dumps(config),antes)
        self.assertEqual(nueva['permission'],config['permission'])
        for alternativa in ({'permission':{}},{'model':'cuy/no-existe'},{'agent':{'explore':{'permission':{}}}}):
            with self.assertRaises(ValueError):
                evaluar.seleccionar_modelos(config,alternativa)

    def test_rechaza_rutas_fuera_del_caso(self):
        import shutil
        carpeta=self.raiz/'casos'
        caso=carpeta/'001'
        shutil.copytree(self.casos[0]['origen'].parent,caso)
        manifiesto=json.loads((caso/'caso.json').read_text())
        manifiesto['intocables']=['../caso.json']
        (caso/'caso.json').write_text(json.dumps(manifiesto))
        self.assertEqual(evaluar.cargar_casos(carpeta)[0]['error_descubrimiento'],'preparacion_caso')

    def test_preparacion_cero_continua_intento_incierto_corta(self):
        def previo(*args):
            return {'estado':'error','fase':'preparacion','codigo_motivo':'preparacion_caso',
                    'trabajo':str(args[2]/'ausente'),'limite_pasos_configurado':30}
        r=self.corrida(previo,'previo.json')
        self.assertEqual(r['estado'],'completada')
        self.assertEqual(r['metricas']['errores_preparacion'],10)
        self.assertEqual(r['metricas']['evaluados'],0)
        self.assertEqual(r['metricas']['costo_usd'],0)
        self.assertTrue(r['metricas']['costo_completo'])
        self.assertTrue(all(g['costo_usd']==0 and g['costo_completo'] for g in r['grupos'].values()))
        def incierto(*args):
            return {'estado':'error','fase':'motor_intentado','trabajo':str(args[2]/'ausente')}
        r=self.corrida(incierto,'incierto.json')
        self.assertEqual(r['estado'],'contabilidad_incompleta')
        self.assertEqual(r['metricas']['no_ejecutados'],9)
        self.assertIsNone(r['metricas']['costo_usd'])

    def test_integridad_raiz_invalida_y_borrado_con_error(self):
        with self.assertRaises(ValueError):
            evaluar.huellas(self.raiz/'ausente',['test.py'])
        self.assertEqual(evaluar.clasificar({'estado':'error'},{'test':'hash'},None),'error')
        def borrado(*args):
            r=self.simulado(*args)
            (args[2]/'test_regresion.py').unlink()
            r['estado']='error'
            return r
        r=self.corrida(borrado,casos=self.casos[:1])
        self.assertEqual(r['casos'][0]['resultado'],'test_modificado')
        def raiz_ausente(*args):
            r=self.simulado(*args)
            r.update(estado='error',trabajo=str(args[2]/'ausente'))
            return r
        r=self.corrida(raiz_ausente,'ausente.json',self.casos[:1])
        self.assertEqual(r['casos'][0]['resultado'],'error')
        self.assertEqual(r['metricas']['costo_usd'],.1)

    def test_motivo_estructurado_no_depende_del_texto(self):
        for texto in ('Sin cambios','No edits','Mensaje nuevo'):
            self.assertEqual(evaluar.clasificar({'estado':'error','codigo_motivo':'sin_cambios','motivo':texto},{},{}),'sin_cambios')
        self.assertEqual(evaluar.clasificar({'estado':'error','motivo':'El motor no produjo cambios verificables.'},{},{}),'error')

    def test_aritmetica_duraciones_y_grupos_parciales(self):
        filas=[{'resultado':'resuelto','fase':'motor_finalizado','duracion_s':d,'costo_usd':c,'costo_completo':True}
               for d,c in zip((1,2,9),(.1,.2,.9))]
        m=evaluar.metricas(filas)
        self.assertEqual(m['duracion_total_s'],12)
        self.assertEqual(m['duracion_mediana_s'],2)
        self.assertAlmostEqual(m['costo_usd'],1.2)
        self.assertEqual(m['costo_mediano_usd'],.2)
        filas[1].update(costo_usd=None,costo_completo=False)
        m=evaluar.metricas(filas)
        self.assertEqual(m['etiqueta_costo'],'total parcial')
        self.assertIsNone(m['costo_mediano_usd'])
        for fila in filas: fila.update(costo_usd=None,costo_completo=False)
        self.assertIsNone(evaluar.metricas(filas)['costo_usd'])
        def parcial(*args):
            r=self.simulado(*args)
            r.update(costo_usd=None,costo_completo=False)
            return r
        r=self.corrida(parcial,casos=self.casos[:1])
        self.assertIsNone(r['grupos']['tarifas']['costo_usd'])
        self.assertEqual(r['grupos']['tarifas']['etiqueta_costo'],'total parcial')

    def test_manifiesto_invalido_no_impide_caso_siguiente(self):
        import shutil
        carpeta=self.raiz/'casos'
        shutil.copytree(self.casos[0]['origen'].parent,carpeta/'001')
        shutil.copytree(self.casos[1]['origen'].parent,carpeta/'002')
        (carpeta/'001/caso.json').write_text('{')
        casos=evaluar.cargar_casos(carpeta)
        r=self.corrida(self.simulado,casos=casos)
        self.assertEqual(r['estado'],'completada')
        self.assertEqual(r['casos'][0]['codigo_motivo'],'preparacion_caso')
        self.assertEqual(r['casos'][0]['costo_usd'],0)
        self.assertEqual(r['casos'][1]['resultado'],'resuelto')
        self.assertEqual(r['metricas']['evaluados'],1)
        self.assertIsNone(r['conjunto_sha256'])

    def test_copia_local_continua_disco_lleno_detiene(self):
        import errno
        import shutil
        contador=0
        def falta_fuente(caso,destino):
            nonlocal contador
            contador+=1
            if contador==1:
                raise FileNotFoundError(errno.ENOENT,'fuente desapareció',str(caso['origen']/'modulo.py'))
            shutil.copytree(caso['origen'],destino)
        r=self.corrida(self.simulado,materializador=falta_fuente)
        self.assertEqual(r['metricas']['errores_preparacion'],1)
        self.assertEqual(r['metricas']['resueltos'],9)
        def disco(caso,destino):
            raise OSError(errno.ENOSPC,'sin espacio',str(destino))
        r=self.corrida(self.simulado,'disco.json',materializador=disco)
        self.assertEqual(r['codigo_motivo'],'infraestructura')
        self.assertEqual(r['metricas']['no_ejecutados'],9)
        self.assertEqual(r['metricas']['evaluados'],0)
        self.assertEqual(r['metricas']['costo_usd'],0)
        def desconocido(caso,destino):
            raise ValueError('origen desconocido')
        r=self.corrida(self.simulado,'desconocido.json',materializador=desconocido)
        self.assertEqual(r['codigo_motivo'],'error_no_clasificado')
        self.assertEqual(r['metricas']['no_ejecutados'],9)

    def test_config_global_detiene_antes_de_todos_los_casos(self):
        self.env['OPENCODE_CONFIG_CONTENT']='{}'
        with patch.object(tareas,'correr_tarea') as motor:
            r=evaluar.correr(self.casos,self.raiz/'config.json',self.env,Path('motor'),1)
        motor.assert_not_called()
        self.assertEqual(r['estado'],'error')
        self.assertEqual(r['metricas']['no_ejecutados'],10)

    def test_fallo_persistencia_conserva_ultimo_informe(self):
        import errno
        original=evaluar.escribir_json
        destino=self.raiz/'r.json'
        escrituras=0
        def escribir(ruta,valor):
            nonlocal escrituras
            if ruta==destino:
                escrituras+=1
                if escrituras>1:
                    raise OSError(errno.ENOSPC,'sin espacio')
            original(ruta,valor)
        with patch.object(evaluar,'escribir_json',side_effect=escribir):
            with self.assertRaises(OSError):
                self.corrida(self.simulado)
        self.assertEqual(escrituras,2)
        anterior=json.loads(destino.read_text())
        self.assertTrue(all(c['resultado']=='no_ejecutado' for c in anterior['casos']))

    def test_main_diez_casos_json_y_metricas(self):
        import cuy
        import io
        from contextlib import redirect_stdout
        destino=self.raiz/'cli.json'
        run_original=subprocess.run
        def version(argv,**kw):
            if argv==['motor','--version']:return subprocess.CompletedProcess(argv,0,'test-version')
            return run_original(argv,**kw)
        with patch.object(cuy,'cargar_env'), patch.object(cuy,'entorno_agente',return_value=self.env), \
             patch.object(cuy,'buscar_binario',return_value=Path('motor')), \
             patch.object(tareas,'correr_tarea',side_effect=self.simulado), \
             patch.object(subprocess,'run',side_effect=version), redirect_stdout(io.StringIO()) as salida:
            codigo=evaluar.main(['--presupuesto-usd','2','--salida',str(destino)])
        self.assertEqual(codigo,0)
        r=json.loads(destino.read_text())
        self.assertEqual(r['metricas']['evaluados'],10)
        self.assertEqual(r['metricas']['tasa_resolucion'],1)
        self.assertAlmostEqual(r['metricas']['costo_usd'],1)
        self.assertEqual(r['metricas']['costo_mediano_usd'],.1)
        import math
        for clave in ('duracion_total_s','duracion_mediana_s'):
            self.assertTrue(math.isfinite(r['metricas'][clave]))
            self.assertGreaterEqual(r['metricas'][clave],0)
        self.assertEqual(set(r['grupos']),{'tarifas','contexto','permisos'})
        self.assertIn(str(destino),salida.getvalue())

    def test_grupo_mezcla_cero_acreditado_y_desconocido(self):
        contador=0
        def respuesta(*args):
            nonlocal contador
            contador+=1
            if contador==1:
                return {'estado':'error','fase':'preparacion','codigo_motivo':'preparacion_caso','trabajo':str(args[2])}
            return {'estado':'error','fase':'motor_intentado','trabajo':str(args[2])}
        r=self.corrida(respuesta,casos=self.casos[:2])
        g=r['grupos']['tarifas']
        self.assertEqual(g['costo_usd'],0)
        self.assertEqual(g['etiqueta_costo'],'total parcial')
        self.assertIsNone(g['costo_mediano_usd'])
        self.assertEqual(g['evaluados'],1)

    def test_hash_cambia_con_grupo_explicito(self):
        a=self.corrida(self.simulado,'hash-a.json',self.casos[:1])
        b=self.corrida(self.simulado,'hash-b.json',[{**self.casos[0],'grupo':'otro'}])
        self.assertNotEqual(a['conjunto_sha256'],b['conjunto_sha256'])
