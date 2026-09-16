# WMS 客户端装配

默认入口 `wms_agent.application:app` 使用 Java 客户端。库存查询、冻结前校验和审批后的冻结执行使用同一个库存客户端。

测试或演示可以显式注入同一个模拟客户端实例：

```python
from wms_agent.application import create_app
from wms_agent.apps.wms.clients import MockWmsClient

# 同一实例保证查询和模拟冻结看到一致的数据。
client = MockWmsClient()
app = create_app(inventory_client=client, location_client=client)
```

这里只替换 WMS 数据源，模型和 PostgreSQL 仍需要配置。模拟状态仅保存在实例内，进程重启后重置。

`clients/contracts.py` 定义异步库存和库位契约，`models/` 保存共用返回类型。客户端模拟远端读写行为；参数校验、人工审批、流程控制继续使用原有节点和服务。
