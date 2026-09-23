"""Corre los tests sin depender de pytest (no está instalado en este Python)."""
import test_rangos as t

fallos = []
for nombre in [n for n in dir(t) if n.startswith("test_")]:
    try:
        getattr(t, nombre)()
        print(f"PASS  {nombre}")
    except AssertionError as e:
        fallos.append(nombre)
        print(f"FAIL  {nombre}")
    except Exception as e:
        fallos.append(nombre)
        print(f"ERROR {nombre}: {type(e).__name__}: {e}")
print()
print(f"{len(fallos)} fallo(s)" if fallos else "todo en verde")
raise SystemExit(1 if fallos else 0)
