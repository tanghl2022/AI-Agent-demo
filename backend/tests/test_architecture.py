"""验证约定的模块依赖边界，防止业务重新耦合具体外部系统。"""
import ast
from pathlib import Path


def test_business_and_infrastructure_dependency_boundaries():
    root = Path(__file__).resolve().parents[1] / "wms_agent"
    errors = []
    for path in root.rglob("*.py"):
        name = path.relative_to(root).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            imports = [node.module or ""] if isinstance(node, ast.ImportFrom) else (
                [item.name for item in node.names] if isinstance(node, ast.Import) else []
            )
            for module in imports:
                if name.startswith("apps/") and module.startswith("wms_agent.integrations"):
                    errors.append((name, module))
                if name.startswith("infrastructure/") and module.startswith("wms_agent.apps"):
                    errors.append((name, module))
                if name.startswith("integrations/") and module.startswith("wms_agent.apps"):
                    if not module.startswith(("wms_agent.apps.warehouse.models", "wms_agent.apps.warehouse.ports")):
                        errors.append((name, module))
    assert errors == []
