"""Autoresearch API router for research endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.research.service import research_service

router = APIRouter(prefix="/api/research", tags=["research"])


# ---- Request models ----


class CompanyRequest(BaseModel):
    company_name: str
    include_filings: bool = True


class IndustryRequest(BaseModel):
    industry: str


class RegulationRequest(BaseModel):
    regulation_name: str
    jurisdiction: str = ""


class ExecutiveRequest(BaseModel):
    name: str
    company: str = ""
    role: str = ""


class HistoricalCaseRequest(BaseModel):
    case_description: str
    tags: list[str] | None = None


class AugmentRequest(BaseModel):
    text: str
    purpose: str = "simulation seed material"


# ---- Endpoints ----


@router.post("/company")
async def research_company(body: CompanyRequest) -> dict:
    """Research a company: web search + SEC filings + synthesis."""
    return await research_service.research_company(body.company_name, include_filings=body.include_filings)


@router.post("/industry")
async def research_industry(body: IndustryRequest) -> dict:
    """Research an industry sector: market size, key players, trends, regulations."""
    return await research_service.research_industry(body.industry)


@router.post("/regulation")
async def research_regulation(body: RegulationRequest) -> dict:
    """Research a regulation: text, requirements, enforcement precedent."""
    return await research_service.research_regulation(body.regulation_name, jurisdiction=body.jurisdiction)


@router.post("/executive")
async def research_executive(body: ExecutiveRequest) -> dict:
    """Research an executive's public behavior, statements, and decision patterns."""
    return await research_service.research_executive(body.name, company=body.company, role=body.role)


@router.post("/historical-case")
async def research_historical_case(body: HistoricalCaseRequest) -> dict:
    """Research a historical business/regulatory case for backtesting."""
    return await research_service.research_historical_case(body.case_description, tags=body.tags)


@router.post("/augment")
async def augment_text(body: AugmentRequest) -> dict:
    """Identify entities in text and research them to augment context."""
    return await research_service.augment_text(body.text, purpose=body.purpose)
