from rangos import fusionar, total


def test_sin_solapamiento():
    assert fusionar([(1, 2), (5, 6)]) == [(1, 2), (5, 6)]


def test_solapados():
    assert fusionar([(1, 5), (3, 8)]) == [(1, 8)]


def test_contiguos_se_unen():
    # Dos bloques pegados son un solo bloque continuo: 9-10 y 10-11 son 9-11.
    assert fusionar([(9, 10), (10, 11)]) == [(9, 11)]


def test_total():
    assert total([(1, 5), (3, 8), (10, 12)]) == 9
