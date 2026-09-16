-- 部署时执行；审计业务表由仓储模块定义，不由公共基础设施隐式创建。
CREATE TABLE IF NOT EXISTS wms_agent_approval_audit (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    business_type TEXT NOT NULL,
    material_code TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    approved BOOLEAN NOT NULL,
    approver_id VARCHAR(64) NOT NULL,
    remark TEXT NOT NULL DEFAULT '',
    approval_time TIMESTAMPTZ NOT NULL,
    UNIQUE (thread_id, business_type)
);
