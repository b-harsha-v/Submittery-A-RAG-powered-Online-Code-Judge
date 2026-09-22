import uuid
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_TYPE = Vector()
except ImportError:
    from sqlalchemy import JSON as Vector
    VECTOR_TYPE = JSON

class ProblemKnowledgeChunk(Base):
    __tablename__ = "problem_knowledge_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_type = Column(String(50), nullable=False, index=True) # e.g. "overview", "editorial_invariant", "hint_tier_1", "hint_tier_2", "hint_tier_3", "target_complexity"
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(VECTOR_TYPE, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    problem = relationship("Problem", backref="knowledge_chunks")


class SubmissionPitfall(Base):
    __tablename__ = "submission_pitfalls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    verdict = Column(String(50), nullable=False, index=True) # e.g. "wrong_answer", "time_limit_exceeded", "runtime_error"
    failed_testcase_summary = Column(Text, nullable=True) # e.g. "Negative numbers with zero target"
    code_pattern = Column(Text, nullable=True) # Anonymized snippet or logic signature
    pitfall_summary = Column(Text, nullable=False) # e.g. "Missing duplicate check in two-pointer scan"
    socratic_guidance = Column(Text, nullable=True) # Guidance question without spoiling
    embedding = Column(VECTOR_TYPE, nullable=True)
    occurrence_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    problem = relationship("Problem", backref="pitfalls")
