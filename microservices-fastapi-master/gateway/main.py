from fastapi import FastAPI, HTTPException, Request, Body, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import httpx
from typing import Any

app = FastAPI(title="API Gateway", version="2.0.0")

# =========================
# Service URLs
# =========================
SERVICES = {
    "student": "http://localhost:8001",
    "course": "http://localhost:8002"
}

# =========================
# JWT CONFIGURATION
# =========================
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

# =========================
# CREATE ACCESS TOKEN
# =========================
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# =========================
# LOGIN ROUTE
# =========================
@app.post("/login")
def login():
    access_token = create_access_token(data={"sub": "admin"})
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# =========================
# FORWARD REQUEST FUNCTION
# =========================
async def forward_request(service: str, path: str, method: str, **kwargs) -> Any:

    if service not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")

    url = f"{SERVICES[service]}{path}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(method, url, **kwargs)

            # Enhanced Error Handling
            if response.status_code >= 400:
                return JSONResponse(
                    content={
                        "service": service,
                        "error": response.text,
                        "status_code": response.status_code
                    },
                    status_code=response.status_code
                )

            return JSONResponse(
                content=response.json() if response.text else None,
                status_code=response.status_code
            )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"{service} service unavailable: {str(e)}"
            )

# =========================
# REQUEST LOGGING MIDDLEWARE
# =========================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()

    print(f"Incoming request: {request.method} {request.url}")

    response = await call_next(request)

    duration = (datetime.utcnow() - start_time).total_seconds()

    print(f"Completed with status {response.status_code} in {duration:.4f}s")

    return response

# =========================
# ROOT
# =========================
@app.get("/")
def read_root():
    return {
        "message": "API Gateway is running",
        "available_services": list(SERVICES.keys())
    }

# =========================
# PROTECTED STUDENT ROUTE
# =========================
@app.get("/gateway/students")
async def get_all_students(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return await forward_request("student", "/api/students", "GET")

# =========================
# STUDENT CRUD
# =========================

@app.get("/gateway/students/{student_id}")
async def get_student(student_id: int):
    return await forward_request(
        "student",
        f"/api/students/{student_id}",
        "GET"
    )

@app.post("/gateway/students")
async def create_student(body: dict = Body(...)):
    return await forward_request("student", "/api/students", "POST", json=body)

@app.put("/gateway/students/{student_id}")
async def update_student(student_id: int, body: dict = Body(...)):
    return await forward_request(
        "student",
        f"/api/students/{student_id}",
        "PUT",
        json=body
    )

@app.delete("/gateway/students/{student_id}")
async def delete_student(student_id: int):
    return await forward_request(
        "student",
        f"/api/students/{student_id}",
        "DELETE"
    )

# =========================
# COURSE ROUTE
# =========================
@app.get("/gateway/courses")
async def get_courses():
    return await forward_request("course", "/api/courses", "GET")
