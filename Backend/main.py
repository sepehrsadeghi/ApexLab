from fastapi import FastAPI
from Backend.Auth.register import router as register_router
from Backend.Auth.login import router as login_router
app = FastAPI(
    title="APEXLAB API",
    description="Backend system for APEXLAB",
    version="1.0.0"
)
app.include_router(register_router)
app.include_router(login_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to APEXLAB Backend",
        "status": "online"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }