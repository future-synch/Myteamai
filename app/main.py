"""
My Team AI — FastAPI application entry point.
Stack: Python 3.11 + FastAPI | Claude API | HubSpot REST v3
Hosting: Render.com Frankfurt
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.auth import LoginRequest, LoginResponse, authenticate, require_auth
from app.classifier import classify, CAPABILITIES
from app.models.schemas import (
    ClassifyResponse,
    WelcomeRequest, WelcomeResponse,
    RegisterApplicantRequest, RegisterApplicantResponse,
    MatchApplicantsRequest, MatchApplicantsResponse,
    ValuationBriefRequest, ValuationBriefResponse,
    DraftOutreachRequest, DraftOutreachResponse,
    KYCStatusRequest, KYCStatusResponse,
)
from app.functions.bot_functions import (
    fn_generate_welcome,
    fn_register_applicant,
    fn_match_applicants,
    fn_valuation_brief,
    fn_draft_outreach,
    fn_kyc_status,
)
from app.services import hubspot_service

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — bootstrap HubSpot custom properties if token is present
    if os.getenv("HUBSPOT_API_KEY"):
        try:
            result = await hubspot_service.ensure_custom_properties()
            log.info("HubSpot properties bootstrap: %s", result)
        except Exception as exc:
            log.warning("HubSpot bootstrap skipped: %s", exc)
    else:
        log.warning("HUBSPOT_API_KEY not set — skipping property bootstrap")
    yield
    # Shutdown — nothing to clean up


app = FastAPI(title="My Team AI", version="1.1.0", lifespan=lifespan)

# CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.1.0"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    result = authenticate(req.email, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result


# ---------------------------------------------------------------------------
# Classify (M1 — no external services)
# ---------------------------------------------------------------------------

@app.post("/classify", response_model=ClassifyResponse)
def classify_endpoint(body: dict, _: dict = Depends(require_auth)):
    text = body.get("text", "")
    result = classify(text)
    if result.is_unknown:
        return ClassifyResponse(
            status="error",
            error_code="UNKNOWN_INTENT",
            message=result.message,
            capabilities=result.capabilities,
        )
    return ClassifyResponse(status="ok", intent=result.intent)


# ---------------------------------------------------------------------------
# Bot function endpoints (M2+)
# ---------------------------------------------------------------------------

@app.post("/bot/welcome", response_model=WelcomeResponse)
async def welcome(req: WelcomeRequest, _: dict = Depends(require_auth)):
    return await fn_generate_welcome(req)


@app.post("/bot/register-applicant", response_model=RegisterApplicantResponse)
async def register_applicant(req: RegisterApplicantRequest, _: dict = Depends(require_auth)):
    return await fn_register_applicant(req)


@app.post("/bot/match-applicants", response_model=MatchApplicantsResponse)
async def match_applicants(req: MatchApplicantsRequest, _: dict = Depends(require_auth)):
    return await fn_match_applicants(req)


@app.post("/bot/valuation-brief", response_model=ValuationBriefResponse)
async def valuation_brief(req: ValuationBriefRequest, _: dict = Depends(require_auth)):
    return await fn_valuation_brief(req)


@app.post("/bot/draft-outreach", response_model=DraftOutreachResponse)
async def draft_outreach(req: DraftOutreachRequest, _: dict = Depends(require_auth)):
    return await fn_draft_outreach(req)


@app.post("/bot/kyc-status", response_model=KYCStatusResponse)
async def kyc_status(req: KYCStatusRequest, _: dict = Depends(require_auth)):
    return await fn_kyc_status(req)


# ---------------------------------------------------------------------------
# Frontend static files
# ---------------------------------------------------------------------------

if os.path.isdir("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

    @app.get("/")
    def root():
        return FileResponse("frontend/index.html")

    @app.get("/chat")
    def chat():
        return FileResponse("frontend/chat.html")
