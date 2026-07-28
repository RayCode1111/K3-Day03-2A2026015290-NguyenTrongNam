from typing import Any, Dict


CATALOG = {
    "iphone": {"display_name": "iPhone", "price": 25_000_000, "stock": 15, "weight_kg": 0.4},
    "ipad": {"display_name": "iPad", "price": 18_000_000, "stock": 8, "weight_kg": 0.5},
    "macbook": {"display_name": "MacBook", "price": 35_000_000, "stock": 0, "weight_kg": 2.0},
}

COUPONS = {
    "WINNER": {"discount_percent": 10, "valid": True},
    "LEGACY": {"discount_percent": 20, "valid": False},
}

SHIPPING_BY_DESTINATION = {
    "hanoi": {"base_cost": 30_000, "per_kg": 10_000, "estimated_days": 1},
    "ha noi": {"base_cost": 30_000, "per_kg": 10_000, "estimated_days": 1},
    "hà nội": {"base_cost": 30_000, "per_kg": 10_000, "estimated_days": 1},
    "saigon": {"base_cost": 35_000, "per_kg": 12_000, "estimated_days": 2},
    "ho chi minh": {"base_cost": 35_000, "per_kg": 12_000, "estimated_days": 2},
    "hồ chí minh": {"base_cost": 35_000, "per_kg": 12_000, "estimated_days": 2},
}


def _error(code: str, message: str) -> Dict[str, Any]:
    return {"ok": False, "error": code, "message": message}


def check_stock(item_name: str | None = None) -> Dict[str, Any]:
    if not item_name:
        return _error("missing_argument", "item_name is required.")

    item = CATALOG.get(str(item_name).strip().lower())
    if item is None:
        return _error("item_not_found", f"Item '{item_name}' was not found in catalog.")

    status = "in_stock" if item["stock"] > 0 else "out_of_stock"
    return {
        "ok": True,
        "item_name": item["display_name"],
        "price": item["price"],
        "stock": item["stock"],
        "weight_kg": item["weight_kg"],
        "status": status,
    }


def get_discount(coupon_code: str | None = None) -> Dict[str, Any]:
    if not coupon_code:
        return _error("missing_argument", "coupon_code is required.")

    code = str(coupon_code).strip().upper()
    coupon = COUPONS.get(code)
    if coupon is None:
        return {
            "ok": True,
            "coupon_code": code,
            "discount_percent": 0,
            "valid": False,
            "message": "Coupon was not found; no discount applied.",
        }

    return {
        "ok": True,
        "coupon_code": code,
        "discount_percent": coupon["discount_percent"] if coupon["valid"] else 0,
        "valid": coupon["valid"],
        "message": "Coupon accepted." if coupon["valid"] else "Coupon is expired; no discount applied.",
    }


def calc_shipping(weight: float | int | None = None, destination: str | None = None) -> Dict[str, Any]:
    if weight is None:
        return _error("missing_argument", "weight is required.")
    if not destination:
        return _error("missing_argument", "destination is required.")

    try:
        numeric_weight = float(weight)
    except (TypeError, ValueError):
        return _error("invalid_argument", "weight must be a number.")

    if numeric_weight <= 0:
        return _error("invalid_argument", "weight must be greater than zero.")

    destination_key = str(destination).strip().lower()
    shipping = SHIPPING_BY_DESTINATION.get(destination_key)
    if shipping is None:
        return _error("destination_not_supported", f"Destination '{destination}' is not supported.")

    cost = int(shipping["base_cost"] + numeric_weight * shipping["per_kg"])
    return {
        "ok": True,
        "destination": destination,
        "weight": numeric_weight,
        "shipping_cost": cost,
        "estimated_days": shipping["estimated_days"],
    }


def get_tool_registry() -> Dict[str, Dict[str, Any]]:
    return {
        "check_stock": {
            "name": "check_stock",
            "description": "Check catalog price, stock, and package weight for an item. Args: item_name.",
            "function": check_stock,
        },
        "get_discount": {
            "name": "get_discount",
            "description": "Validate a coupon code and return discount_percent. Args: coupon_code.",
            "function": get_discount,
        },
        "calc_shipping": {
            "name": "calc_shipping",
            "description": "Calculate shipping cost and estimated days. Args: weight, destination.",
            "function": calc_shipping,
        },
    }
