"""Evalúa correcciones por el mismo camino que el producto, sin un modelo juez.

Los casos son código confiable: sus pruebas se ejecutan localmente. El aislamiento
Git no es un sandbox. Los informes nunca incluyen la configuración ni credenciales.
"""
from __future__ import annotations

import argparse
import errno
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import tareas
from configuracion import escribir_json, leer_gasto

RAIZ = Path(__file__).resolve().parent


def alcance_error(exc: BaseException, origen: Path | None = None) -> str:
    """Clasifica por causa y recurso, nunca por el mero lugar del bloque try.

    :returns: Código conservador; solo errores de fuente identificados son locales.
    """
    if isinstance(exc, OSError):
        if exc.errno in (errno.ENOSPC, errno.EDQUOT, errno.EROFS, errno.EIO, errno.EMFILE, errno.ENFILE):
            return 'infraestructura'
        nombre = getattr(exc, 'filename', None)
        if origen is not None and nombre and exc.errno in (errno.ENOENT, errno.EACCES, errno.ENOTDIR):
            if Path(nombre).resolve().is_relative_to(origen.resolve()):
                return 'preparacion_caso'
    return 'error_no_clasificado'


def cargar_casos(carpeta: Path) -> list[dict]:
    """Descubre casos conservando manifiestos inválidos como errores locales observables.

    :returns: Casos válidos o descriptores de error; no exporta el contenido de excepciones.
    """
    casos = []
    for directorio in sorted(carpeta.iterdir()):
        if not directorio.is_dir():
            continue
        archivo = directorio/'caso.json'
        proyecto = directorio/'proyecto'
        base = {'id': directorio.name, 'origen': proyecto, 'grupo': 'sin_grupo'}
        try:
            if directorio.is_symlink() or any(p.is_symlink() or p.name == '.git' for p in directorio.rglob('*')):
                raise ValueError('Caso no aislable')
            caso = json.loads(archivo.read_text(encoding='utf-8'))
            if not isinstance(caso, dict) or not proyecto.is_dir():
                raise ValueError('Caso inválido')
            if not isinstance(caso.get('grupo'), str) or not caso['grupo'].strip():
                raise ValueError('Falta grupo explícito')
            base['grupo'] = caso['grupo']
            if not isinstance(caso.get('objetivo'), str) or not caso['objetivo'].strip():
                raise ValueError('Falta objetivo')
            for campo in ('prueba', 'intocables'):
                if not isinstance(caso.get(campo), list) or not caso[campo] or not all(isinstance(x, str) and x for x in caso[campo]):
                    raise ValueError('Lista inválida')
            for nombre in caso['intocables']:
                ruta = (proyecto/nombre).resolve()
                if not ruta.is_relative_to(proyecto.resolve()) or not ruta.is_file():
                    raise ValueError('Intocable fuera del caso o ausente')
            casos.append({**caso, **base})
        except (ValueError, UnicodeError):
            casos.append({**base, 'error_descubrimiento': 'preparacion_caso'})
        except OSError as exc:
            casos.append({**base, 'error_descubrimiento': alcance_error(exc, directorio)})
    if not casos:
        raise ValueError('No hay casos; indicá una carpeta con subcarpetas de casos')
    return casos


def materializar(caso: dict, destino: Path) -> None:
    """Crea un repositorio nuevo sin objetos ni historia del repositorio fuente."""
    shutil.copytree(caso['origen'], destino)
    tareas.git(destino, 'init', '--quiet')
    tareas.git(destino, 'add', '.')
    tareas.git(destino, '-c', 'user.name=cuycli', '-c', 'user.email=evaluacion@localhost',
               '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Base del caso')


def huellas(carpeta: Path, nombres: list[str]) -> dict:
    """Rechaza raíces inválidas; archivo ausente en raíz válida sí es comparable."""
    if not carpeta.is_dir() or carpeta.is_symlink():
        raise ValueError('No se puede inspeccionar la raíz')
    resultado = {}
    for nombre in nombres:
        ruta = carpeta/nombre
        if not ruta.resolve().is_relative_to(carpeta.resolve()):
            resultado[nombre] = None
        else:
            resultado[nombre] = hashlib.sha256(ruta.read_bytes()).hexdigest() if ruta.is_file() and not ruta.is_symlink() else None
    return resultado


def clasificar(informe: dict, antes: dict | None, despues: dict | None) -> str:
    """None representa inspección imposible; cambio comprobado prevalece sobre error."""
    if antes is None or despues is None:
        return 'error'
    if antes != despues:
        return 'test_modificado'
    if informe.get('estado') == 'verificada':
        return 'resuelto'
    if informe.get('codigo_motivo') == 'sin_cambios':
        return 'sin_cambios'
    if informe.get('estado') in ('error', 'interrumpida'):
        return 'error'
    if not informe.get('archivos'):
        return 'sin_cambios'
    return 'sin_verificar'


def metricas(casos: list[dict]) -> dict:
    """Agrega resultados; preparación y no ejecutados no son fallos del modelo."""
    iniciados = [c for c in casos if c['resultado'] != 'no_ejecutado']
    evaluados = [c for c in iniciados if c.get('fase') in ('motor_intentado', 'motor_finalizado')]
    completos = bool(iniciados) and all(c.get('costo_completo', False) for c in iniciados)
    costos = [c['costo_usd'] for c in iniciados if c.get('costo_usd') is not None]
    duraciones = [c['duracion_s'] for c in iniciados]
    resueltos = sum(c['resultado'] == 'resuelto' for c in evaluados)
    return {'resueltos': resueltos, 'evaluados': len(evaluados), 'iniciados': len(iniciados),
            'no_ejecutados': len(casos)-len(iniciados),
            'errores_preparacion': sum(c.get('codigo_motivo') == 'preparacion_caso' for c in iniciados),
            'tasa_resolucion': resueltos / len(evaluados) if evaluados else None,
            'costo_usd': sum(costos) if costos else None, 'costo_completo': completos,
            'etiqueta_costo': 'total estimado' if completos else 'total parcial',
            'costo_mediano_usd': statistics.median(costos) if completos else None,
            'duracion_total_s': sum(duraciones),
            'duracion_mediana_s': statistics.median(duraciones) if duraciones else None,
            'pasos_con_costo': sum(c.get('pasos_con_costo', 0) for c in iniciados),
            'pasos_sin_costo': sum(c.get('pasos_sin_costo', 0) for c in iniciados)}


def correr(casos: list[dict], salida: Path, entorno: dict, binario: Path | None,
           presupuesto: float | None, seco: bool = False, limite: int = 120) -> dict:
    """Persiste casos previstos y decide continuidad con evidencia de fase y causa.

    :returns: Informe sin secretos. Si falla persistencia, solo queda la última escritura.
    :raises ValueError: Si los argumentos no permiten una corrida segura.
    """
    if not seco and (presupuesto is None or not math.isfinite(presupuesto) or presupuesto <= 0):
        raise ValueError('Indicá --presupuesto-usd con un máximo positivo')
    if salida.resolve().is_relative_to(RAIZ) or salida.exists():
        raise ValueError('Elegí un informe nuevo fuera del repositorio')
    config = json.loads(entorno.get('OPENCODE_CONFIG_CONTENT', '{}'))
    modelos = {'principal': config.get('model'), **{n: a.get('model', config.get('model'))
               for n, a in config.get('agent', {}).items() if isinstance(a, dict)}}
    filas = [{'id': c['id'], 'grupo': c['grupo'], 'resultado': 'no_ejecutado', 'fase': 'no_iniciado',
              'codigo_motivo': '', 'costo_usd': None, 'costo_completo': False, 'duracion_s': 0,
              'pasos': 0, 'pasos_con_costo': 0, 'pasos_sin_costo': 0,
              'limite_pasos_configurado': None} for c in casos]
    informe = {'version': 2, 'inicio': datetime.now(timezone.utc).isoformat(), 'modo': 'seco' if seco else 'real',
               'modelos': modelos, 'motor': None, 'presupuesto_usd': presupuesto,
               'conjunto_sha256': None,
               'config_modelos_sha256': hashlib.sha256(json.dumps(modelos, sort_keys=True).encode()).hexdigest(),
               'casos_previstos': len(casos), 'casos': filas, 'estado': 'en_curso', 'codigo_motivo': ''}
    fallo_guardado = False
    def guardar():
        nonlocal fallo_guardado
        informe['metricas'] = metricas(filas)
        informe['grupos'] = {g: metricas([c for c in filas if c['grupo'] == g]) for g in sorted({c['grupo'] for c in filas})}
        try:
            escribir_json(salida, informe)
        except OSError:
            fallo_guardado = True
            raise
    guardar()
    firmas = []
    actual = None
    inicio = None
    try:
        # Configuración y binario son recursos globales, no errores repetibles por caso.
        if not seco:
            if not binario:
                raise ValueError('Motor no instalado')
            mensual = Path(entorno.get('CUY_GASTO', str(Path.home()/'.local/share/cuy-cli/gasto.json')))
            limite_mensual = float(entorno.get('CUY_LIMITE_USD', '10'))
            if math.isfinite(limite_mensual) and limite_mensual > 0 and leer_gasto(mensual).get(datetime.now().strftime('%Y-%m'), 0) >= limite_mensual:
                informe['estado'] = 'presupuesto_mensual_agotado'
                return informe
            tareas.preparar_entorno(entorno, 'corregir', RAIZ)
            if float(entorno.get('CUY_LIMITE_USD', '10')) <= 0:
                raise ValueError('Presupuesto mensual desactivado')
            informe['motor'] = subprocess.run([str(binario), '--version'], capture_output=True, text=True,
                                             timeout=15, check=True).stdout.strip()
        with tempfile.TemporaryDirectory(prefix='cuy-evaluacion-') as temporal:
            raiz = Path(temporal).resolve()
            ledger = raiz/'gasto.json'
            escribir_json(ledger, {})
            env = {**entorno, 'CUY_EVALUACION_GASTO': str(ledger), 'CUY_EVALUACION_LIMITE_USD': str(presupuesto)}
            for caso, resultado in zip(casos, filas):
                actual, inicio = None, None
                if not seco:
                    if leer_gasto(ledger).get('2000-01', 0) >= presupuesto:
                        informe['estado'] = 'presupuesto_agotado'
                        break
                    mensual = Path(entorno.get('CUY_GASTO', str(Path.home()/'.local/share/cuy-cli/gasto.json')))
                    if leer_gasto(mensual).get(datetime.now().strftime('%Y-%m'), 0) >= float(entorno.get('CUY_LIMITE_USD', '10')):
                        informe['estado'] = 'presupuesto_mensual_agotado'
                        break
                actual, inicio = resultado, time.monotonic()
                resultado.update(resultado='error', fase='preparacion', costo_usd=0.0, costo_completo=True)
                codigo = caso.get('error_descubrimiento', '')
                try:
                    if codigo:
                        resultado['codigo_motivo'] = codigo
                    else:
                        nombres = sorted(str(p.relative_to(caso['origen'])) for p in caso['origen'].rglob('*') if p.is_file())
                        firmas.append({'id':caso['id'], 'grupo':caso['grupo'], 'objetivo':caso['objetivo'],
                                       'prueba':caso['prueba'], 'intocables':caso['intocables'],
                                       'archivos':huellas(caso['origen'], nombres)})
                        proyecto = raiz/caso['id']
                        materializar(caso, proyecto)
                        antes = huellas(proyecto, caso['intocables'])
                        argv = [sys.executable if a == '{python}' else a for a in caso['prueba']]
                        if seco:
                            retorno, _, timeout = tareas.ejecutar_proceso(argv, proyecto, tareas.entorno_pruebas(entorno, proyecto), limite)
                            resultado['resultado'] = 'error' if timeout else 'base_verde' if retorno == 0 else 'base_roja'
                        else:
                            # Hasta obtener la fase de tareas, una excepción no prueba que no hubo llamada.
                            resultado.update(fase='motor_intentado', costo_usd=None, costo_completo=False)
                            tarea = tareas.correr_tarea('corregir', caso['objetivo'], proyecto, binario,
                                                       env, raiz/'tareas', [argv], limite)
                            resultado.update({k:tarea[k] for k in ('fase','codigo_motivo','costo_usd','costo_completo',
                                'pasos','pasos_con_costo','pasos_sin_costo','archivos','limite_pasos_configurado') if k in tarea})
                            resultado['estado_tarea'] = tarea['estado']
                            if resultado['fase'] == 'preparacion':
                                resultado.update(costo_usd=0.0, costo_completo=True)
                            trabajo = Path(tarea['trabajo'])
                            despues = None
                            if trabajo.resolve().is_relative_to(raiz):
                                try:
                                    despues = huellas(trabajo, caso['intocables'])
                                except (ValueError, OSError):
                                    pass
                            resultado['resultado'] = clasificar(tarea, antes, despues)
                            if despues is None and resultado['fase'] != 'preparacion':
                                resultado['codigo_motivo'] = 'inspeccion_imposible'
                            if tarea.get('error_errno') in (errno.ENOSPC, errno.EDQUOT, errno.EIO, errno.EROFS):
                                codigo = 'infraestructura'
                            elif tarea.get('estado') == 'interrumpida':
                                codigo = 'interrumpida'
                            elif resultado['fase'] == 'preparacion':
                                codigo = tarea.get('codigo_motivo') or 'error_no_clasificado'
                except (ValueError, OSError, subprocess.SubprocessError) as exc:
                    codigo = alcance_error(exc, caso['origen'])
                    resultado['codigo_motivo'] = codigo
                resultado['duracion_s'] = round(time.monotonic()-inicio, 6)
                if codigo and codigo != 'preparacion_caso':
                    informe.update(estado='interrumpida' if codigo == 'interrumpida' else 'error', codigo_motivo=codigo)
                    break
                if not seco and not resultado['costo_completo']:
                    informe['estado'] = 'contabilidad_incompleta'
                    break
                guardar()
            else:
                informe['estado'] = 'completada'
            if len(firmas) == len(casos):
                informe['conjunto_sha256'] = hashlib.sha256(json.dumps(firmas, sort_keys=True).encode()).hexdigest()
    except KeyboardInterrupt:
        informe['estado'] = 'interrumpida'
        if actual is not None:
            actual.update(resultado='error', codigo_motivo='interrumpida')
            actual['duracion_s'] = round(time.monotonic()-inicio, 6)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        informe.update(estado='error', codigo_motivo=alcance_error(exc))
    finally:
        if not fallo_guardado:
            guardar()
    if fallo_guardado:
        raise OSError('No se pudo guardar; solo se conserva el último informe persistido')
    return informe


def seleccionar_modelos(config: dict, alternativa: dict) -> dict:
    """Aplica selecciones sin permitir que el archivo alternativo cambie barreras.

    :returns: Copia independiente; el objeto y archivo original quedan intactos.
    :raises ValueError: Si se cambian otras opciones o se elige un endpoint inexistente.
    """
    if not isinstance(alternativa, dict) or set(alternativa) - {'model', 'agent'}:
        raise ValueError('--config admite solo model y agent (model por rol)')
    copia = json.loads(json.dumps(config))
    def validar(modelo):
        if not isinstance(modelo, str) or '/' not in modelo:
            raise ValueError('model debe tener formato proveedor/endpoint')
        proveedor, nombre = modelo.split('/', 1)
        if nombre not in copia.get('provider', {}).get(proveedor, {}).get('models', {}):
            raise ValueError('Modelo alternativo no descubierto; ejecutá instalar.py para descubrir endpoints')
        return modelo
    if 'model' in alternativa:
        copia['model'] = validar(alternativa['model'])
    if not isinstance(alternativa.get('agent', {}), dict):
        raise ValueError('agent debe ser un objeto de roles')
    for rol, valor in alternativa.get('agent', {}).items():
        if not isinstance(valor, dict) or set(valor) != {'model'}:
            raise ValueError('Cada rol alternativo admite solo model')
        copia.setdefault('agent', {}).setdefault(rol, {})['model'] = validar(valor['model'])
    return copia


def main(argv=None) -> int:
    """CLI del evaluador; --seco funciona sin instalación ni credenciales."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--casos', type=Path, default=RAIZ/'evaluacion/casos')
    parser.add_argument('--seco', action='store_true')
    parser.add_argument('--presupuesto-usd', type=float)
    parser.add_argument('--config', type=Path, help='Configuración alternativa: solo modelos/roles, no credenciales')
    parser.add_argument('--salida', type=Path)
    parser.add_argument('--limite-segundos', type=int, default=120)
    args = parser.parse_args(argv)
    try:
        if args.limite_segundos <= 0:
            raise ValueError('El límite de tiempo debe ser positivo')
        if not args.seco and (args.presupuesto_usd is None or not math.isfinite(args.presupuesto_usd) or args.presupuesto_usd <= 0):
            raise ValueError('Una corrida real exige --presupuesto-usd positivo')
        casos = cargar_casos(args.casos)
        entorno, binario = dict(os.environ), None
        if not args.seco:
            import cuy
            cuy.cargar_env()
            entorno, binario = cuy.entorno_agente(), cuy.buscar_binario()
            if args.config:
                config = seleccionar_modelos(json.loads(entorno['OPENCODE_CONFIG_CONTENT']),
                                             json.loads(args.config.read_text(encoding='utf-8')))
                entorno['OPENCODE_CONFIG_CONTENT'] = json.dumps(config)
            if float(entorno.get('CUY_LIMITE_USD', '10')) <= 0:
                raise ValueError('Activá el presupuesto mensual antes de evaluar')
        salida = args.salida or Path.home()/'.local/share/cuy-cli/evaluaciones'/f'{uuid4().hex}.json'
        informe = correr(casos, salida, entorno, binario, args.presupuesto_usd, args.seco, args.limite_segundos)
        m = informe['metricas']
        print(f"{informe['modo']} · {informe['estado']} · {m['iniciados']}/{len(casos)} casos iniciados")
        for caso in informe['casos']:
            print(f"  {caso['id']}: {caso['resultado']}")
        if not args.seco:
            print(f"Resueltos: {m['resueltos']}/{m['evaluados']} · {m['etiqueta_costo']}: {m['costo_usd'] if m['costo_usd'] is not None else 'no disponible'} USD")
        for grupo, resumen in informe['grupos'].items():
            print(f"  Grupo {grupo}: {resumen['resueltos']}/{resumen['evaluados']} · {resumen['etiqueta_costo']}: {resumen['costo_usd'] if resumen['costo_usd'] is not None else 'no disponible'} USD")
        if informe['estado'] != 'completada':
            motivo = informe.get('codigo_motivo') or informe['estado']
            accion = {
                'infraestructura': 'Revisá espacio y permisos del almacenamiento antes de repetir.',
                'contabilidad_incompleta': 'Revisá el informe parcial y ejecutá python cuy.py costos antes de repetir.',
                'presupuesto_agotado': 'Revisá el consumo del informe antes de autorizar otra corrida.',
                'presupuesto_mensual_agotado': 'Revisá el presupuesto mensual con python cuy.py gasto.',
                'interrumpida': 'Revisá el informe parcial; no se reanudará automáticamente.',
            }.get(motivo, 'Revisá el informe y ejecutá python cuy.py doctor para comprobar la instalación.')
            print(f'Detención: {motivo}. {accion}')
        print(f'Informe: {salida}')
        return 0 if informe['estado'] == 'completada' else 2
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f'No se pudo evaluar ({type(exc).__name__}); verificá --presupuesto-usd positivo, casos válidos, instalación y un --salida nuevo fuera del repositorio.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
