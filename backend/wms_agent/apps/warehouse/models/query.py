from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StockQueryResult:
    """
    WMS库存查询结果。

    这里保存的是Java WMS返回给Agent的确定性业务数据。

    注意：
    Agent不能自己计算或虚构库存，
    这里只接受WMS系统实际返回的数据。
    """

    material_code: str

    total_qty: int

    reserved_qty: int

    frozen_qty: int

    available_qty: int


@dataclass(frozen=True, slots=True)
class LocationQueryItem:
    """
    单个库位库存信息。
    """

    location_code: str

    quantity: int


@dataclass(frozen=True, slots=True)
class LocationQueryResult:
    """
    某个物料的库位查询结果。
    """

    material_code: str

    locations: list[LocationQueryItem]