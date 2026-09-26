"""Audita tarifas locales y compara estimaciones del mismo alcance con facturación."""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from configuracion import escribir_json, leer_gasto, numero_entorno
from tarifas import tarifa_usd, personalizadas, FUENTE, FECHA

RAIZ = Path(__file__).resolve().parent


def auditar(config: dict) -> list[dict]:
    """Compara las tarifas escritas en la configuración contra la referencia pública.

    Sirve para detectar que un ``opencode.json`` quedó con precios viejos después de que
    Databricks cambie su lista, cosa que si no se nota solo aparece como un gasto
    estimado que no cuadra con la factura.

    :param config: Contenido de ``opencode.json``.
    :returns: Una fila por modelo con ``configurada``, ``referencia``, ``estado``
        (``coincide`` | ``difiere`` | ``sin_referencia``) y ``origen``.
    """
    propias = personalizadas()
    filas = []
    for proveedor, datos in config.get('provider', {}).items():
        for nombre, modelo in datos.get('models', {}).items():
            referencia = tarifa_usd(nombre)
            actual = modelo.get('cost')
            filas.append({'modelo': f'{proveedor}/{nombre}', 'configurada': actual,
                          'referencia': referencia,
                          'estado': 'sin_referencia' if referencia is None else
                                    'coincide' if actual == referencia else 'difiere',
                          'origen': 'configurada_por_usuario' if nombre in propias else
                                    'publica_global_pay_per_token' if referencia else 'no_verificada'})
    return filas


def main(argv=None) -> int:
    """Punto de entrada de ``cuy costos``.

    :param argv: Argumentos de línea de comandos; ``None`` usa ``sys.argv``.
    :returns: Código de salida; 0 si la auditoría pudo completarse.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actualizar', action='store_true', help='Actualizar solo las tarifas con referencia conocida; sin inferencia')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--real-usd', type=float, help='Gasto real del mismo mes, equipo y solicitudes para comparar')
    parser.add_argument('--mes', default=datetime.now().strftime('%Y-%m'))
    args = parser.parse_args(argv)
    import os
    import re
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', args.mes):
        parser.error('--mes debe ser AAAA-MM')
    if args.real_usd is not None and (not math.isfinite(args.real_usd) or args.real_usd <= 0):
        parser.error('--real-usd debe ser positivo y finito')
    try:
        ruta = RAIZ / 'opencode.json'
        config = json.loads(ruta.read_text(encoding='utf-8'))
        filas = auditar(config)
        if args.actualizar:
            for fila in filas:
                if fila['referencia'] is not None:
                    proveedor, nombre = fila['modelo'].split('/', 1)
                    config['provider'][proveedor]['models'][nombre]['cost'] = fila['referencia']
            escribir_json(ruta, config)
            filas = auditar(config)
        reporte = {'usd_por_dbu': numero_entorno('CUY_USD_POR_DBU', 0.07), 'fuente': FUENTE,
                   'consultado': FECHA, 'tarifas': filas,
                   'alcance': 'Estimación local; no factura. Referencia pública global, pago por token. In-geo, prioridad, capacidad provisionada y contrato pueden cambiar el precio.'}
        if args.real_usd is not None:
            gasto = leer_gasto(Path(os.environ.get('CUY_GASTO', Path.home()/'.local/share/cuy-cli/gasto.json')))
            if args.mes not in gasto:
                raise ValueError('No hay registro local para ese mes; no se asumirá gasto cero.')
            estimado = gasto[args.mes]
            reporte['comparacion'] = {'mes': args.mes, 'estimado_usd': estimado,
                                     'real_usd': args.real_usd, 'diferencia_usd': estimado - args.real_usd,
                                     'error_porcentual': 100 * (estimado - args.real_usd) / args.real_usd}
        if args.json:
            print(json.dumps(reporte, indent=2, ensure_ascii=False))
        else:
            print(reporte['alcance'])
            print(f"Referencia consultada {FECHA} | USD/DBU: {reporte['usd_por_dbu']}")
            for fila in filas:
                print(f"  {fila['modelo']}: {fila['estado']} ({fila['origen']})")
            print('Para tarifas contractuales: CUY_TARIFAS=ruta.json (USD por millón, claves exactas de endpoint).')
            print('Para actualizar referencias conocidas sin llamar modelos: cuy costos --actualizar')
            print('Las tarifas sin referencia se conservan, pero NO quedan verificadas. Los registros históricos no se recalculan.')
            if 'comparacion' in reporte:
                c = reporte['comparacion']
                print(f"Comparación {c['mes']}: estimado ${c['estimado_usd']:.4f}, real ${c['real_usd']:.4f}, diferencia {c['error_porcentual']:+.2f}%")
                print('La comparación solo mide precisión si ambos importes cubren exactamente el mismo consumo.')
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f'No se pudo auditar costos: {exc}')
        return 1
