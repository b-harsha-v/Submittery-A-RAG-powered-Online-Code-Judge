from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db
from ..models.problem import Problem
from ..models.submission import Submission
from ..models.user import User, UserRole
from ..services.ai_service import ai_service
from ..services.rag_service import rag_service
from .deps import get_current_user

from ..core.rate_limiter import RateLimiter

router = APIRouter(prefix="/ai", tags=["ai"])
rate_limit_ai = RateLimiter(requests_limit=15, window_seconds=60, scope="ai_service")

class ComplexityRequest(BaseModel):
    code: str
    problem_id: UUID

class QARequest(BaseModel):
    question: str
    problem_id: UUID
    code: Optional[str] = None

class AIResponse(BaseModel):
    response: str

class ProblemRecommendResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    difficulty: str
    tags: Optional[List[str]] = []

    class Config:
        from_attributes = True

@router.post("/analyze-complexity", response_model=AIResponse, dependencies=[Depends(rate_limit_ai)])
def analyze_complexity(
    req: ComplexityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    problem = db.query(Problem).filter(Problem.id == req.problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
        
    analysis = ai_service.analyze_complexity(req.code, problem.title)
    return {"response": analysis}

@router.post("/code-review/{submission_id}", response_model=AIResponse, dependencies=[Depends(rate_limit_ai)])
def code_review(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
        
    # Check authorization
    if submission.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this submission"
        )
        
    problem = db.query(Problem).filter(Problem.id == submission.problem_id).first()
    review = ai_service.provide_code_review(submission.code, problem.title, submission.status.value)
    return {"response": review}

@router.post("/debug-hints/{submission_id}", response_model=AIResponse, dependencies=[Depends(rate_limit_ai)])
def debug_hints(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
        
    # Check authorization
    if submission.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this submission"
        )
        
    problem = db.query(Problem).filter(Problem.id == submission.problem_id).first()
    error_msg = submission.error_message or "Submission was not accepted."
    hints = ai_service.generate_debug_hints(submission.code, problem.title, error_msg)
    return {"response": hints}

@router.post("/ask", response_model=AIResponse, dependencies=[Depends(rate_limit_ai)])
def ask_question(
    req: QARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    problem = db.query(Problem).filter(Problem.id == req.problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
        
    answer = ai_service.answer_question(req.question, problem, code=req.code)
    return {"response": answer}

@router.get("/recommend/{problem_id}", response_model=List[ProblemRecommendResponse])
def recommend_problems(
    problem_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not current_problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
        
    all_problems = db.query(Problem).filter(Problem.is_public == True).all()
    recommendations = ai_service.recommend_problems(current_problem, all_problems)
    
    # Map model difficulty Enum if needed
    for rec in recommendations:
        if hasattr(rec.difficulty, "value"):
            rec.difficulty_str = rec.difficulty.value
        else:
            rec.difficulty_str = rec.difficulty
            
    return recommendations

# --- RAG ADVANCED ENDPOINTS ---

class DiagnoseFailureRequest(BaseModel):
    problem_id: UUID
    submission_id: Optional[UUID] = None
    code: Optional[str] = None
    verdict: Optional[str] = "wrong_answer"
    error_message: Optional[str] = None

class DiagnoseFailureResponse(BaseModel):
    response: str
    historical_cluster_matched: bool = False
    matched_pitfalls: int = 0

class SocraticHintRequest(BaseModel):
    problem_id: UUID
    code: str
    tier: int = 1 # 1 = Intuition, 2 = State Invariant, 3 = Edge Cases

class SocraticHintResponse(BaseModel):
    response: str
    tier: int
    title: str

class SemanticSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 6

class SemanticSearchResultItem(BaseModel):
    id: str
    title: str
    slug: str
    difficulty: str
    tags: List[str] = []
    similarity: float
    matched_concept: str
    chunk_title: Optional[str] = None

@router.post("/diagnose-failure", response_model=DiagnoseFailureResponse, dependencies=[Depends(rate_limit_ai)])
def diagnose_failure(
    req: DiagnoseFailureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG-driven failure diagnostic.
    Retrieves canonical problem invariants and nearest historical failed submission pitfall clusters.
    """
    user_code = (req.code or "").strip()
    verdict = req.verdict or "wrong_answer"
    error_detail = req.error_message

    if req.submission_id:
        sub = db.query(Submission).filter(Submission.id == req.submission_id).first()
        if sub:
            if not user_code:
                user_code = sub.code
            verdict = sub.status.value
            error_detail = sub.error_message

    if not user_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code is required for failure diagnosis"
        )

    res = rag_service.diagnose_failure(
        db=db,
        problem_id=req.problem_id,
        user_code=user_code,
        verdict=verdict,
        error_detail=error_detail
    )

    return {
        "response": res.get("diagnosis", "Could not produce diagnostic."),
        "historical_cluster_matched": res.get("historical_cluster_matched", False),
        "matched_pitfalls": res.get("matched_pitfalls", 0)
    }

@router.post("/socratic-hint", response_model=SocraticHintResponse, dependencies=[Depends(rate_limit_ai)])
def socratic_hint(
    req: SocraticHintRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves tiered, non-spoiling Socratic hints grounded in vector knowledge base.
    """
    res = rag_service.get_socratic_hint(
        db=db,
        problem_id=req.problem_id,
        user_code=req.code,
        hint_tier=req.tier
    )

    return {
        "response": res.get("hint", ""),
        "tier": res.get("tier", req.tier),
        "title": res.get("title", f"Tier {req.tier} Hint")
    }

@router.post("/semantic-search", response_model=List[SemanticSearchResultItem])
def semantic_search(
    req: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Natural language semantic search over problem concepts & invariants.
    """
    results = rag_service.semantic_search_problems(
        db=db,
        query=req.query,
        limit=req.limit or 6
    )
    return results
