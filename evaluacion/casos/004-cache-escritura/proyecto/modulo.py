import os
USD_POR_DBU = float(os.environ.get("CUY_USD_POR_DBU", "0.07"))
DBU_POR_MILLON = {
    "opus": {"entrada": 71.42857, "salida": 357.142857},
    "sonnet": {"entrada": 42.857, "salida": 214.286},
    "haiku": {"entrada": 14.286, "salida": 71.429},
    "llama-4-maverick": {"entrada": 7.143, "salida": 21.429},
    "llama-3-1-8b": {"entrada": 2.143, "salida": 6.429},
    "gpt-oss-20b": {"entrada": 1.0, "salida": 4.286},
}
def tarifa_usd(modelo: str, usd_por_dbu: float = USD_POR_DBU) -> dict | None:
    """Traduce la tarifa en DBU de un modelo a dólares por millón de tokens.

    Es lo que OpenCode entiende: declarar ``cost`` en cada modelo hace que calcule y
    muestre el gasto de la sesión por su cuenta, sin que nadie lleve la cuenta aparte.

    :param modelo: Nombre del endpoint.
    :param usd_por_dbu: Dólares por DBU según el contrato.
    :returns: ``{"input": …, "output": …}`` en USD por millón, o ``None`` si no se
        conoce la tarifa del modelo —preferible a inventar un número—.
    """
    nombre = modelo.lower()
    # Primero las claves más específicas: "llama-3-1-8b" debe ganarle a "llama".
    for clave in sorted(DBU_POR_MILLON, key=len, reverse=True):
        if clave in nombre:
            dbu = DBU_POR_MILLON[clave]
            # Cuatro decimales: las tarifas en DBU vienen ya redondeadas de Databricks,
            # así que los dígitos de más son ruido de ese redondeo y no información
            # (14.286 × 0.07 da 1.00002, no 1). A esta escala —dólares por millón de
            # tokens— la diferencia es de centésimas de centavo.
            return {
                "input": round(dbu["entrada"] * usd_por_dbu, 4),
                "output": round(dbu["salida"] * usd_por_dbu, 4),
            }
    return None
