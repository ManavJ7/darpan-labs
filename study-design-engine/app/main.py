import uuid
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import ensure_readable_study, get_current_user, get_current_user_optional
from app.config import settings
from app.database import get_session
from app.models.study import Study
from app.models.user import User
from app.schemas.study import StudyCreate, StudyResponse
from app.routers import auth as auth_router
from app.routers import studies as studies_router
from app.routers import metrics as metrics_router
from app.routers import audit as audit_router
from app.routers import comments as comments_router
from app.routers import versions as versions_router
from app.routers import export as export_router
from app.routers import concepts as concepts_router
from app.routers import research_design as research_design_router
from app.routers import questionnaire as questionnaire_router
from app.routers import simulation as simulation_router

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Study Design Engine — AI-assisted research study design microservice",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth_router.router)
app.include_router(studies_router.router)
app.include_router(metrics_router.router)
app.include_router(audit_router.router)
app.include_router(comments_router.router)
app.include_router(versions_router.router)
app.include_router(export_router.router)
app.include_router(concepts_router.router)
app.include_router(research_design_router.router)
app.include_router(questionnaire_router.router)
app.include_router(simulation_router.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "study-design-engine"}


@app.post(f"{settings.API_V1_PREFIX}/studies", response_model=StudyResponse)
async def create_study(
    data: StudyCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    study = Study(
        brand_id=data.brand_id,
        question=data.question,
        brand_name=data.brand_name,
        category=data.category,
        context=data.context or {},
        study_metadata={"study_type": data.study_type or "concept_testing"},
        status="init",
        created_by_user_id=current_user.id,
    )
    db.add(study)
    await db.commit()
    await db.refresh(study)
    return StudyResponse(
        id=study.id,
        status=study.status,
        question=study.question,
        title=study.title,
        brand_name=study.brand_name,
        category=study.category,
        context=study.context,
        study_metadata=study.study_metadata,
        created_at=study.created_at,
        updated_at=study.updated_at,
        created_by_user_id=study.created_by_user_id,
        is_public=getattr(study, "is_public", False),
    )


@app.get(f"{settings.API_V1_PREFIX}/studies/{{study_id}}", response_model=StudyResponse)
async def get_study(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Read a study.

    - Public studies: readable by anyone (auth or anon) — powers the demo landing page
    - Private studies: readable by any authenticated user (shared-read policy)
    """
    study = await ensure_readable_study(study_id, current_user, db)
    return StudyResponse(
        id=study.id,
        status=study.status,
        question=study.question,
        title=study.title,
        brand_name=study.brand_name,
        category=study.category,
        context=study.context,
        study_metadata=study.study_metadata,
        created_at=study.created_at,
        updated_at=study.updated_at,
        created_by_user_id=getattr(study, "created_by_user_id", None),
        is_public=getattr(study, "is_public", False),
    )


@app.get(f"{settings.API_V1_PREFIX}/studies", response_model=list[StudyResponse])
async def list_studies(
    brand_id: uuid.UUID | None = None,
    mine: bool = False,
    db: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List studies visible to the caller.

    - Anonymous: only `is_public = True` studies (demo showcase)
    - Authenticated: public studies + own studies (no other users' private work)
    - `?mine=true` + authenticated: only own studies
    """
    if current_user is None:
        # Anon: public studies only. `mine` is ignored — there's no "me" yet.
        query = select(Study).where(Study.is_public.is_(True))
    elif mine:
        query = select(Study).where(Study.created_by_user_id == current_user.id)
    else:
        query = select(Study).where(
            or_(Study.is_public.is_(True), Study.created_by_user_id == current_user.id)
        )

    if brand_id:
        query = query.where(Study.brand_id == brand_id)

    result = await db.execute(query)
    studies = result.scalars().all()
    return [
        StudyResponse(
            id=s.id,
            status=s.status,
            question=s.question,
            title=s.title,
            brand_name=s.brand_name,
            category=s.category,
            context=s.context,
            study_metadata=s.study_metadata,
            created_at=s.created_at,
            updated_at=s.updated_at,
            created_by_user_id=getattr(s, "created_by_user_id", None),
            is_public=getattr(s, "is_public", False),
        )
        for s in studies
    ]
