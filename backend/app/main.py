from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ALLOWED_ORIGINS, COOKIE_SECURE, ENV, FRONTEND_DIST, SEED_DEMO
from .db import Base, SessionLocal, engine
from .routers import applications, auth, business, platform
from .security import client_ip, limiter

app = FastAPI(title="ARTHA API", version="1.0.0", docs_url="/api/docs" if ENV != "production" else None,
              redoc_url=None, openapi_url="/api/openapi.json" if ENV != "production" else None)

app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["content-type", "x-csrf-token"])

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'")


@app.middleware("http")
async def security_layer(request: Request, call_next):
    if request.url.path.startswith("/api/") and not limiter.hit(f"api:{client_ip(request)}", 600, 60):
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
    if int(request.headers.get("content-length") or 0) > 3 * 1024 * 1024:
        return JSONResponse({"detail": "Request too large"}, status_code=413)
    resp = await call_next(request)
    resp.headers["Content-Security-Policy"] = CSP
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if COOKIE_SECURE:
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errs = [{"field": ".".join(str(p) for p in e["loc"][1:]), "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": "Invalid input: " + "; ".join(f"{e['field']} – {e['msg']}" for e in errs[:3]),
                         "errors": errs}, status_code=422)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    import logging
    logging.getLogger("artha").exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Internal error"}, status_code=500)


for r in (auth.router, business.router, applications.router, platform.router):
    app.include_router(r)


@app.on_event("startup")
def startup():
    from .agents.risk import model
    Base.metadata.create_all(engine)
    model()
    if SEED_DEMO:
        from .seed import seed
        with SessionLocal() as db:
            seed(db)


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        f = (FRONTEND_DIST / path).resolve()
        if path and f.is_file() and FRONTEND_DIST.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(FRONTEND_DIST / "index.html")
