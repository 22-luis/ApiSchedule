
from typing import List
from dataclasses import dataclass

# Mocking the Order class to match the structure relevant to the issue
@dataclass
class Order:
    lote: int
    quantity: float
    code: str
    # id is intentionally missing to reproduce the error

# Mocking the ProgrammingUtils class with the problematic method
class ProgrammingUtils:
    @staticmethod
    def extract_order_data(orders: List[Order]) -> List[dict]:
        """
        Extrae datos básicos de una lista de órdenes.
        """
        extracted_data = []
        for order in orders:
            extracted_data.append({
                "lote": order.lote,
                "quantity": order.quantity,
                "code": order.code,
                "order_id": order.lote # This should pass now
            })
        return extracted_data

def test_extract_order_data():
    print("Starting test...")
    orders = [
        Order(lote=123, quantity=10.0, code="ABC"),
        Order(lote=456, quantity=5.0, code="DEF")
    ]
    
    try:
        ProgrammingUtils.extract_order_data(orders)
        print("Test PASSED")
    except AttributeError as e:
        print(f"Test FAILED with error: {e}")
    except Exception as e:
        print(f"Test FAILED with unexpected error: {e}")

if __name__ == "__main__":
    test_extract_order_data()
