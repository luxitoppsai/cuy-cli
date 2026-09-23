"""Fusiona rangos de fechas solapados. Usado para calcular tiempo dedicado."""


def fusionar(rangos):
    """Une los rangos que se solapan y devuelve la lista ordenada.

    :param rangos: Lista de tuplas (inicio, fin) con números.
    :returns: Lista de tuplas sin solapamientos, ordenada por inicio.
    """
    if not rangos:
        return []
    ordenados = sorted(rangos)
    resultado = [ordenados[0]]
    for inicio, fin in ordenados[1:]:
        ultimo_inicio, ultimo_fin = resultado[-1]
        if inicio < ultimo_fin:
            resultado[-1] = (ultimo_inicio, max(ultimo_fin, fin))
        else:
            resultado.append((inicio, fin))
    return resultado


def total(rangos):
    """Suma la duración de los rangos ya fusionados."""
    return sum(fin - inicio for inicio, fin in fusionar(rangos))
