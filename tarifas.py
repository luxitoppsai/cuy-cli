"""Tarifas públicas por versión. Referencia estimada, no precio contractual."""
import json
import math
import os
from pathlib import Path
from configuracion import numero_entorno

FUENTE = 'https://learn.microsoft.com/en-us/azure/databricks/resources/pricing'
FECHA = '2026-09-25'
# DBU por millón: entrada, salida, lectura de caché, escritura de caché (5 min).
# Contexto <=200k y endpoint global. No se extrapolan versiones desconocidas.
DBU = {
    'claude-opus-4': (214.286, 1071.43, 21.429, 267.857),
    'claude-opus-4-1': (214.286, 1071.43, 21.429, 267.857),
    'claude-opus-4-5': (71.429, 357.143, 7.143, 89.286),
    'claude-sonnet-3-7': (42.857, 214.286, 4.286, 53.571),
    'claude-sonnet-4': (42.857, 214.286, 4.286, 53.571),
    'claude-sonnet-4-1': (42.857, 214.286, 4.286, 53.571),
    'claude-sonnet-4-5': (42.857, 214.286, 4.286, 53.571),
    'claude-haiku-4-5': (14.286, 71.429, 1.429, 17.857),
    'meta-llama-4-maverick': (7.143, 21.429),
    'llama-4-maverick': (7.143, 21.429),
    'meta-llama-3-1-8b-instruct': (2.143, 6.429),
    'llama-3-1-8b': (2.143, 6.429),
    'gpt-oss-20b': (1., 4.286),
    'gpt-oss-120b': (2.143, 8.571),
    'gemma-3-12b': (2.143, 7.143),
}

def personalizadas() -> dict:
    """Carga las tarifas del contrato propio, si se declararon.

    La tabla ``DBU`` son precios públicos de lista; cada empresa negocia los suyos.
    ``CUY_TARIFAS`` apunta a un JSON con los reales, ya en USD por millón de tokens y
    con el nombre exacto del endpoint como clave.

    :returns: ``{endpoint: {"input": …, "output": …}}``, o ``{}`` si no se declararon.
    :raises ValueError: Si el archivo no tiene la forma esperada. Se falla en vez de
        ignorarlo: una tarifa mal escrita daría un gasto equivocado sin avisar.
    """
    ruta = os.environ.get('CUY_TARIFAS')
    if not ruta:
        return {}
    datos = json.loads(Path(ruta).read_text(encoding='utf-8-sig'))
    if not isinstance(datos, dict):
        raise ValueError('CUY_TARIFAS debe contener un objeto por nombre exacto de endpoint.')
    campos = {'input', 'output', 'cache_read', 'cache_write'}
    for nombre, precio in datos.items():
        if not isinstance(precio, dict) or not {'input', 'output'} <= precio.keys() or precio.keys() - campos:
            raise ValueError(f'Tarifa inválida para {nombre}: usar input/output y opcionalmente cache_read/cache_write en USD por millón.')
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in precio.values()):
            raise ValueError(f'Tarifa inválida para {nombre}: los valores deben ser finitos y no negativos.')
    return datos

def tarifa_usd(modelo: str, usd_por_dbu: float | None = None) -> dict | None:
    """Traduce la tarifa de un modelo a dólares por millón de tokens.

    Es lo que OpenCode entiende: declarar ``cost`` en cada modelo hace que calcule y
    muestre el gasto por su cuenta. Databricks publica en **DBU por millón**, y el dólar
    por DBU depende del contrato, así que el cálculo son dos factores separados.

    La búsqueda es por **nombre exacto de versión**, no por familia: las versiones de una
    misma familia no comparten precio —Opus 4.1 y Opus 4.5 difieren por un factor 3— y
    buscar por subcadena les daría la misma tarifa.

    :param modelo: Nombre del endpoint, con o sin el prefijo ``databricks-``.
    :param usd_por_dbu: Dólares por DBU; por defecto ``CUY_USD_POR_DBU`` o 0.07.
    :returns: Tarifa en USD por millón, o ``None`` si la versión no está en la tabla.
        Devolver ``None`` es deliberado: preferible no contabilizar a inventar un número.
    :raises ValueError: Si el factor de conversión no es finito y no negativo.
    """
    configuradas = personalizadas()
    if modelo in configuradas:
        return dict(configuradas[modelo])
    nombre = modelo.lower().removeprefix('databricks-')
    dbu = DBU.get(nombre)
    if dbu is None:
        return None
    factor = numero_entorno('CUY_USD_POR_DBU', 0.07) if usd_por_dbu is None else usd_por_dbu
    if not math.isfinite(factor) or factor < 0:
        raise ValueError('USD por DBU debe ser finito y no negativo.')
    precio = dict(zip(('input', 'output', 'cache_read', 'cache_write'), (round(v * factor, 4) for v in dbu)))
    if nombre in {'claude-sonnet-3-7', 'claude-sonnet-4', 'claude-sonnet-4-1', 'claude-sonnet-4-5'}:
        precio['context_over_200k'] = dict(zip(('input','output','cache_read','cache_write'),
            (round(v * factor, 4) for v in (85.714,321.429,8.571,107.143))))
    return precio
