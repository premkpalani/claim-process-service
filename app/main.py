from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

from app.config import settings
from app.database import init_db, get_session
from app.models import ClaimCreate, ClaimResponse, TopProviderResponse
from app.services import ClaimService

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Service for processing healthcare claims with transaction-based billing",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    init_db()
    logger.info("Database initialized successfully")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


@app.post("/claims", response_model=ClaimResponse, status_code=201)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_claim(
    request: Request,
    claim_data: ClaimCreate,
    session: Session = Depends(get_session)
):
    """
    Process a new claim with multiple lines.

    This endpoint:
    1. Validates all claim line data (procedure codes, NPI, etc.)
    2. Calculates net fee for each line
    3. Stores claim and lines in database
    4. Sends to payment service for processing

    Rate limit: 10 requests per minute
    """
    try:
        service = ClaimService(session)

        # Check if claim reference already exists
        existing_claim = service.get_claim_by_reference(claim_data.claim_reference)
        if existing_claim:
            raise HTTPException(
                status_code=400,
                detail=f"Claim with reference {claim_data.claim_reference} already exists"
            )

        claim = service.process_claim(claim_data)
        return claim

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error processing claim: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@app.get("/claims/{claim_id}", response_model=ClaimResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_claim(
    request: Request,
    claim_id: int,
    session: Session = Depends(get_session)
):
    """
    Get a claim by ID.

    Rate limit: 10 requests per minute
    """
    service = ClaimService(session)
    claim = service.get_claim_by_id(claim_id)

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    return claim


@app.get("/providers/top", response_model=list[TopProviderResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_top_providers(
    request: Request,
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    Get top N providers by net fees generated.

    This endpoint is optimized for performance using:
    - Database-level aggregation with SQL GROUP BY and SUM
    - Indexed provider_npi column for fast lookups
    - LIMIT applied at database level
    - Single query to avoid N+1 problem

    Algorithm: O(n log n) where n is unique providers (database sorting)
    Space: O(k) where k is the limit

    Rate limit: 10 requests per minute

    Args:
        limit: Number of top providers to return (default: 10)

    Returns:
        List of top providers with their total net fees and claim counts
    """
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100"
        )

    service = ClaimService(session)
    top_providers = service.get_top_providers_by_net_fees(limit=limit)

    return top_providers


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
