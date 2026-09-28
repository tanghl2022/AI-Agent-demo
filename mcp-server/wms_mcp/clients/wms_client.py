"""真实 WMS 只读适配器；失败时绝不补零或返回演示数据。"""
from urllib.parse import quote
import httpx
from pydantic import BaseModel, Field, ValidationError


class QueryError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class Stock(BaseModel):
    material_code: str = Field(alias="materialCode", min_length=1)
    total_qty: int = Field(alias="totalQty", strict=True, ge=0)
    reserved_qty: int = Field(alias="reservedQty", strict=True, ge=0)
    frozen_qty: int = Field(alias="frozenQty", strict=True, ge=0)
    available_qty: int = Field(alias="availableQty", strict=True, ge=0)


class Location(BaseModel):
    location_code: str = Field(alias="locationCode", min_length=1)
    quantity: int | None = Field(default=None, strict=True, ge=0)


class Locations(BaseModel):
    material_code: str = Field(alias="materialCode", min_length=1)
    locations: list[Location]


class WmsClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client

    async def query(self, material_code: str, *, locations: bool = False) -> dict:
        prefix = "api/wms/inventory/location/" if locations else "api/wms/inventory/"
        try:
            response = await self.http_client.get(prefix + quote(material_code, safe=""))
            response.raise_for_status()
            data = response.json()
            if locations and isinstance(data, dict) and isinstance(data.get("locations"), list):
                # 编码列表没有数量时保留 null，不能编造为零。
                data["locations"] = [{"locationCode": item} if isinstance(item, str) else item for item in data["locations"]]
            parsed = (Locations if locations else Stock).model_validate(data)
            if parsed.material_code != material_code:
                raise ValueError("返回物料不匹配")
            return parsed.model_dump()
        except httpx.TimeoutException as exc:
            raise QueryError("UPSTREAM_TIMEOUT", "WMS 查询超时") from exc
        except httpx.HTTPStatusError as exc:
            code, message = {
                401: ("UNAUTHORIZED", "WMS 身份验证失败"),
                403: ("FORBIDDEN", "无权查询此库存数据"),
                404: ("NOT_FOUND", "WMS 接口或物料不存在，请核实"),
                429: ("RATE_LIMITED", "WMS 查询被限流，请稍后重试"),
            }.get(exc.response.status_code, ("UPSTREAM_ERROR", "WMS 服务查询失败"))
            raise QueryError(code, message) from exc
        except httpx.HTTPError as exc:
            raise QueryError("UPSTREAM_UNAVAILABLE", "无法连接 WMS 服务") from exc
        except (ValidationError, ValueError, TypeError) as exc:
            raise QueryError("INVALID_RESPONSE", "WMS 返回数据不符合查询契约") from exc
