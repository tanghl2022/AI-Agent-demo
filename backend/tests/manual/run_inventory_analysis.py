import asyncio
import logging
import os
import selectors
from pathlib import Path

from dotenv import load_dotenv
from wms_agent.config import load_settings

# ============================================================
# 1. 加载 backend/.env
#
# 注意：
# 必须在导入 wms_agent 项目模块之前执行。
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(
    dotenv_path=ENV_FILE
)


# ============================================================
# 2. 环境变量加载完成后，再导入项目模块
# ============================================================

from wms_agent.bootstrap import create_runtime
from wms_agent.config import Settings


# ============================================================
# 3. 日志配置
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s - "
        "%(message)s"
    ),
)


# ============================================================
# 4. 配置检查
# ============================================================

print(
    "ENV_FILE =",
    ENV_FILE,
)

print(
    "ENV exists =",
    ENV_FILE.exists(),
)

print(
    "CHECKPOINT_DB_URI loaded =",
    bool(
        os.getenv(
            "checkpoint_db_uri"
        )
    ),
)


async def main():

    # ========================================================
    # 5. 创建 Settings
    # ========================================================

    settings = load_settings()

    print(
        "settings.checkpoint_db_uri configured =",
        bool(
            getattr(
                settings,
                "checkpoint_db_uri",
                None,
            )
        ),
    )

    # ========================================================
    # 6. 创建完整 Runtime
    # ========================================================

    async with create_runtime(
        settings
    ) as runtime:

        # ====================================================
        # 7. 获取 WarehouseContainer
        # ====================================================

        warehouse = runtime.warehouse

        # ====================================================
        # 8. 获取 InventoryAnalysisSubAgent
        # ====================================================

        subagent = (
            warehouse
            .agent_container
            .inventory_analysis_subagent
        )

        # ====================================================
        # 9. 第一条 Tool Calling 测试
        # ====================================================

        question = (
            "请查询 MAT001 的库存明细，"
            "告诉我总库存、预占库存、"
            "冻结库存和可用库存。"
        )

        print()
        print("=" * 80)
        print("测试问题：")
        print(question)
        print("=" * 80)

        # ====================================================
        # 10. 调用 SubAgent
        # ====================================================

        result = await subagent.ainvoke(
            question
        )

        print()
        print("=" * 80)
        print("SubAgent分析结果：")
        print(result)
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(
            selectors.SelectSelector()
        ),
    )