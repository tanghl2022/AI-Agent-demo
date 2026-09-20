import asyncio
import logging

from wms_agent.bootstrap import create_runtime
from wms_agent.config import Settings


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s - "
        "%(message)s"
    ),
)


async def main():
    """
    InventoryAnalysisSubAgent 集成测试。

    完整调用链：

    create_runtime
        ↓
    WarehouseContainer
        ↓
    AgentContainer
        ↓
    InventoryAnalysisSubAgent
        ↓
    Tool
        ↓
    Capability
        ↓
    Service
        ↓
    Java API
    """

    # =========================================================
    # 1. 加载项目现有配置
    # =========================================================

    settings = Settings()

    # =========================================================
    # 2. 使用正式 Runtime
    #
    # 这里必须 async with。
    # 因为 create_runtime 是 @asynccontextmanager。
    # =========================================================

    async with create_runtime(settings) as runtime:

        # =====================================================
        # 3. 获取 WarehouseContainer
        # =====================================================

        warehouse = runtime.warehouse

        # =====================================================
        # 4. 获取 SubAgent
        # =====================================================

        subagent = (
            warehouse
            .agent_container
            .inventory_analysis_subagent
        )

        # =====================================================
        # 5. 第一条简单测试
        # =====================================================

        question = (
            "请查询 MAT001 的库存明细，"
            "告诉我总库存、预占库存、"
            "冻结库存和可用库存。"
        )

        print("=" * 80)
        print("测试问题：")
        print(question)
        print("=" * 80)

        # =====================================================
        # 6. 调用 SubAgent
        # =====================================================

        result = await subagent.ainvoke(
            question
        )

        print()
        print("=" * 80)
        print("SubAgent分析结果：")
        print(result)
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())