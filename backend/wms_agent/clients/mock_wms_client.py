import time


class WmsClientError(RuntimeError):
    pass


class MockWmsClient:
    """内置只读 WMS 数据源，便于无外部系统时部署学习。"""

    _materials = {
        "MAT001": {
            "stock": {"materialCode": "MAT001", "totalQty": 120, "availableQty": 90},
            "detail": {"materialCode": "MAT001", "totalQty": 120, "reservedQty": 20, "frozenQty": 10, "availableQty": 90},
            "location": {"materialCode": "MAT001", "locations": ["A01-01-01", "A01-01-02"]},
        },
        "MAT002": {
            "stock": {"materialCode": "MAT002", "totalQty": 80, "availableQty": 65},
            "detail": {"materialCode": "MAT002", "totalQty": 80, "reservedQty": 10, "frozenQty": 5, "availableQty": 65},
            "location": {"materialCode": "MAT002", "locations": ["B02-03-01"]},
        },
    }

    def _get(self, material_code: str) -> dict:
        code = material_code.upper()
        if code not in self._materials:
            raise WmsClientError(f"物料不存在: {material_code}")
        return self._materials[code]

    def query_stock(self, material_code: str) -> dict:
        time.sleep(2.0)
        return self._get(material_code)["stock"]

    def query_inventory_detail(self, material_code: str) -> dict:
        time.sleep(0.05)
        return self._get(material_code)["detail"]

    def query_location(self, material_code: str) -> dict:
        time.sleep(2.0)
        return self._get(material_code)["location"]
