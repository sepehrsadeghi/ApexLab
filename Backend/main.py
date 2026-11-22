
from contextlib import asynccontextmanager

from fastapi import FastAPI

from Backend.database import Base, engine

# Register all models before create_all
from Backend import models  # noqa: F401

from Backend.Auth.register_api import router as register_router
from Backend.Auth.login_api import router as login_router
from Backend.Tests.routes import router as test_results_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="APEXLAB API",
    description="Backend for athlete accounts and performance test data",
    version="1.2.0",
    lifespan=lifespan,
)

app.include_router(register_router)
app.include_router(login_router)
app.include_router(test_results_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to APEXLAB Backend",
        "status": "online",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
