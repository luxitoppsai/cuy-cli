def _nombre_legible(endpoint: str) -> str:
    return endpoint.removeprefix("databricks-").replace("-", " ").title()
def tarifa_usd(endpoint):
    return None
def _describir_modelo(endpoint: str, limite: int) -> dict:
    """Arma la entrada de un modelo: nombre legible, topes y tarifa."""
    modelo = {
        "name": _nombre_legible(endpoint),
        "limit": {"context": 128000, "output": limite},
    }
    # Sin `cost`, OpenCode calcula cero y la TUI no muestra el gasto: el indicador
    # de la barra se omite cuando el costo es 0, no aparece en cero.
    tarifa = tarifa_usd(endpoint)
    if tarifa:
        modelo["cost"] = tarifa
    return modelo
