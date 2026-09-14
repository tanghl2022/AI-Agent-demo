import unittest

from wms_agent.clients.mock.mock_wms_client import MockWmsClient
from wms_agent.models.wms_query_result import StockQueryResult, LocationQueryResult
from wms_agent.services.wms_query_service import WmsQueryService


class MockClientTests(unittest.IsolatedAsyncioTestCase):
    """验证模拟客户端的异步契约及实例隔离。"""

    async def test_queries_and_freeze_are_consistent(self):
        client = MockWmsClient()
        service = WmsQueryService(client, client)
        self.assertIsInstance(await service.query_stock("MAT001"), StockQueryResult)
        self.assertIsInstance(await client.query_locations("MAT001"), LocationQueryResult)
        args = dict(idempotency_key="request-1", material_code="MAT001", quantity=30)
        first = await client.freeze_inventory(**args)
        retry = await client.freeze_inventory(**args)
        self.assertTrue(first.executed)
        self.assertTrue(retry.success)
        self.assertFalse(retry.executed)
        self.assertEqual((await client.query_stock("MAT001")).available_qty, 60)
        self.assertEqual((await MockWmsClient().query_stock("MAT001")).available_qty, 90)

    async def test_rejected_freeze_does_not_change_stock(self):
        client = MockWmsClient()
        before = await client.query_stock("MAT001")
        result = await client.freeze_inventory(
            idempotency_key="request-2", material_code="MAT001", quantity=100,
        )
        self.assertFalse(result.success)
        self.assertEqual(await client.query_stock("MAT001"), before)

    async def test_idempotency_key_cannot_change_quantity(self):
        client = MockWmsClient()
        await client.freeze_inventory(idempotency_key="same", material_code="MAT001", quantity=10)
        result = await client.freeze_inventory(idempotency_key="same", material_code="MAT001", quantity=20)
        self.assertFalse(result.success)
        self.assertEqual((await client.query_stock("MAT001")).available_qty, 80)
