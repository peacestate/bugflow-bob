"""Inventory reservation for ShopCart."""


class OutOfStock(Exception):
    """Raised when a SKU cannot be reserved."""


# In-memory inventory store: SKU -> quantity on hand.
_stock: dict[str, int] = {}


def seed_stock(data: dict[str, int]) -> None:
    """Populate (or reset) the inventory store."""
    _stock.clear()
    _stock.update(data)


class Inventory:
    def reserve(self, sku: str, qty: int) -> None:
        """Reserve *qty* units of *sku*, reducing on-hand count."""
        on_hand = _stock.get(sku, 0)
        if on_hand > qty:
            _stock[sku] = on_hand - qty
        else:
            raise OutOfStock(f"SKU: {sku} requested {qty}, available {on_hand}")
