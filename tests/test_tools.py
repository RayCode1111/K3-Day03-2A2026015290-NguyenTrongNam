from src.tools.tools import calc_shipping, check_stock, get_discount


def test_check_stock_valid_and_deterministic():
    first = check_stock("iPhone")
    second = check_stock("iPhone")

    assert first == second
    assert first["ok"] is True
    assert first["price"] == 25_000_000
    assert first["stock"] == 15
    assert first["status"] == "in_stock"


def test_check_stock_errors_are_structured():
    assert check_stock("Unknown")["error"] == "item_not_found"
    assert check_stock()["error"] == "missing_argument"


def test_discount_valid_invalid_and_missing():
    assert get_discount("WINNER")["discount_percent"] == 10
    legacy = get_discount("LEGACY")
    assert legacy["valid"] is False
    assert legacy["discount_percent"] == 0
    assert get_discount()["error"] == "missing_argument"


def test_shipping_valid_invalid_missing_and_deterministic():
    first = calc_shipping(0.8, "Hanoi")
    second = calc_shipping(0.8, "Hanoi")

    assert first == second
    assert first["shipping_cost"] == 38_000
    assert calc_shipping(destination="Hanoi")["error"] == "missing_argument"
    assert calc_shipping(weight="bad", destination="Hanoi")["error"] == "invalid_argument"
