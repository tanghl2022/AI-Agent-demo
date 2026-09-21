"""HTTP 应用入口，具体对象装配由 bootstrap 负责。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from wms_agent.api.router import router
from wms_agent.bootstrap import RuntimeFactory, create_lifespan, create_runtime
from wms_agent.config import Settings, load_settings


def create_app(settings: Settings | None = None, *, runtime_factory: RuntimeFactory = create_runtime) -> FastAPI:
    settings = settings if settings is not None else load_settings()
    app = FastAPI(title="Warehouse Agent", version="1.0.0",
                  lifespan=create_lifespan(settings, runtime_factory))

    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    app.include_router(router)

    return app


app = create_app()
