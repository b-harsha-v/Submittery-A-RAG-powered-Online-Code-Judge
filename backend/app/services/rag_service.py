import os
import json
import uuid
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.problem import Problem, TestCase
from ..models.submission import Submission, SubmissionStatus
from ..models.rag import ProblemKnowledgeChunk, SubmissionPitfall
from .ai_service import ai_service

class RAGService:
    """
    RAG Service for Submittery:
    - Grounded Socratic Hint Generation
    - Dynamic Failure & Pitfall Clustering Memory
    - Semantic Concept Search over Problems
    - Persistent Knowledge in PostgreSQL with pgvector
    """

    def __init__(self):
        self._pgvector_ready = False

    def init_db_extensions(self, db: Session):
        """Enables the pgvector extension if PostgreSQL is running."""
        try:
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            db.commit()
            self._pgvector_ready = True
            print("[*] PostgreSQL pgvector extension verified.")
        except Exception as e:
            db.rollback()
            # If not supported or running SQLite/non-pgvector, fallback to numpy in memory
            print(f"[*] Note on pgvector extension: {e}. Falling back to NumPy vector operations.")
            self._pgvector_ready = False

    def get_embedding(self, content: str) -> List[float]:
        """Fetches 768-dim embedding via Gemini text-embedding-004."""
        return ai_service.get_embedding(content)

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        a = np.array(vec_a, dtype=float)
        b = np.array(vec_b, dtype=float)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    # --- KNOWLEDGE BASE SEEDING & SYNC ---

    def seed_problem_knowledge_if_needed(self, db: Session, force: bool = False):
        """
        Embed-once seeder. Ingests canonical algorithmic invariants and
        multi-tier hints into problem_knowledge_chunks table.
        """
        self.init_db_extensions(db)
        problems = db.query(Problem).all()
        if not problems:
            print("[*] No problems to index in RAG database.")
            return

        total_seeded = 0
        for problem in problems:
            existing_count = db.query(ProblemKnowledgeChunk).filter(
                ProblemKnowledgeChunk.problem_id == problem.id
            ).count()

            if existing_count > 0 and not force:
                continue

            # Delete old if force
            if existing_count > 0 and force:
                db.query(ProblemKnowledgeChunk).filter(
                    ProblemKnowledgeChunk.problem_id == problem.id
                ).delete()
                db.commit()

            chunks_to_create = self._build_canonical_chunks(problem)
            for chunk_data in chunks_to_create:
                embedding = self.get_embedding(f"{chunk_data['title']}\n{chunk_data['content']}")
                chunk_obj = ProblemKnowledgeChunk(
                    problem_id=problem.id,
                    chunk_type=chunk_data["chunk_type"],
                    title=chunk_data["title"],
                    content=chunk_data["content"],
                    embedding=embedding,
                    metadata_json=chunk_data.get("metadata", {})
                )
                db.add(chunk_obj)
                total_seeded += 1

            db.commit()
            print(f"[+] [RAG] Indexed knowledge base for: {problem.title}")

        if total_seeded > 0:
            print(f"[+] [RAG] Completed indexing {total_seeded} knowledge chunks into pgvector.")

    def _build_canonical_chunks(self, problem: Problem) -> List[Dict[str, Any]]:
        """Constructs multi-tier editorial and conceptual chunks for a problem."""
        tags_str = ", ".join(problem.tags or [])
        chunks = [
            {
                "chunk_type": "overview",
                "title": f"{problem.title} - Conceptual Overview & Target Bounds",
                "content": f"Problem: {problem.title}\nDifficulty: {problem.difficulty.value if hasattr(problem.difficulty, 'value') else problem.difficulty}\nTags: {tags_str}\n\nDescription:\n{problem.description}\nTime Limit: {problem.time_limit}s, Memory Limit: {problem.memory_limit}MB.",
                "metadata": {"difficulty": str(problem.difficulty), "tags": problem.tags}
            },
            {
                "chunk_type": "hint_tier_1",
                "title": f"{problem.title} - Tier 1 Intuition (Mental Model)",
                "content": f"High-level strategy for {problem.title}:\nThink about how to transform the search space. Can you use a auxiliary data structure (such as a Hash Map, Two Pointers, or Monotonic Stack) to avoid brute force checking?",
                "metadata": {"tier": 1}
            },
            {
                "chunk_type": "hint_tier_2",
                "title": f"{problem.title} - Tier 2 Invariant (State & Invariants)",
                "content": f"Key algorithmic invariant for {problem.title}:\nMaintain current progress state without revisiting previous elements redundantly. What property holds true at each iteration or window boundary?",
                "metadata": {"tier": 2}
            },
            {
                "chunk_type": "hint_tier_3",
                "title": f"{problem.title} - Tier 3 Edge Cases & Guardrails",
                "content": f"Critical edge cases to check for {problem.title}:\n- Empty inputs, 0-element or 1-element collections\n- Negative values, zero, and maximum integer boundaries\n- Duplicate elements and pointer collision checks\n- Proper termination condition for recursive calls or loops.",
                "metadata": {"tier": 3}
            }
        ]
        return chunks

    # --- DYNAMIC PITFALL HARVESTING (LEARNING FROM REAL ERRORS) ---

    def harvest_failure_pitfall(
        self,
        db: Session,
        problem_id: uuid.UUID,
        verdict: str,
        code: str,
        error_detail: Optional[str] = None,
        failed_test_input: Optional[str] = None
    ) -> Optional[SubmissionPitfall]:
        """
        Dynamically clusters and records real user failure patterns into pgvector.
        """
        try:
            problem = db.query(Problem).filter(Problem.id == problem_id).first()
            if not problem:
                return None

            # Generate pitfall signature text
            signature_text = f"Problem: {problem.title}\nVerdict: {verdict}\nError: {error_detail or ''}\nCode Pattern:\n{code[:500]}"
            signature_embedding = self.get_embedding(signature_text)

            # Query existing pitfalls for this problem to see if this matches a known cluster
            existing_pitfalls = db.query(SubmissionPitfall).filter(
                SubmissionPitfall.problem_id == problem_id,
                SubmissionPitfall.verdict == verdict
            ).all()

            best_match = None
            highest_sim = 0.0

            for pf in existing_pitfalls:
                if pf.embedding is not None:
                    sim = self._cosine_similarity(signature_embedding, pf.embedding)
                    if sim > highest_sim:
                        highest_sim = sim
                        best_match = pf

            # If similarity > 0.86, increment existing cluster
            if best_match and highest_sim >= 0.86:
                best_match.occurrence_count += 1
                db.commit()
                print(f"[+] [RAG] Incremented known pitfall cluster (count={best_match.occurrence_count}) for {problem.title}")
                return best_match

            # Otherwise create a new pitfall memory
            summary = self._summarize_pitfall_pattern(problem.title, verdict, code, error_detail)
            guidance = self._generate_socratic_guidance(problem.title, verdict, summary)

            new_pitfall = SubmissionPitfall(
                problem_id=problem_id,
                verdict=verdict,
                failed_testcase_summary=failed_test_input[:300] if failed_test_input else "Hidden edge case input",
                code_pattern=code[:600],
                pitfall_summary=summary,
                socratic_guidance=guidance,
                embedding=signature_embedding,
                occurrence_count=1
            )
            db.add(new_pitfall)
            db.commit()
            db.refresh(new_pitfall)
            print(f"[+] [RAG] Ingested new pitfall cluster for {problem.title}: '{summary[:60]}...'")
            return new_pitfall
        except Exception as e:
            db.rollback()
            print(f"[!] [RAG] Error harvesting failure pitfall: {e}")
            return None

    def _summarize_pitfall_pattern(self, title: str, verdict: str, code: str, error: Optional[str]) -> str:
        """Derives a concise pitfall description."""
        if verdict == "time_limit_exceeded":
            return f"Inefficient loop traversal or unmemoized recursion causing timeout under large constraints."
        elif verdict == "runtime_error":
            return f"Runtime exception: {error or 'IndexError or NoneType dereference during traversal'}."
        elif verdict == "wrong_answer":
            return f"Logical discrepancy on boundary conditions, duplicate elements, or off-by-one pointer arithmetic."
        return f"Execution failure with verdict: {verdict}."

    def _generate_socratic_guidance(self, title: str, verdict: str, summary: str) -> str:
        return f"Check if your loop termination conditions account for input bounds and duplicates without exceeding $O(N)$ operations."

    # --- RAG QUERY: SOCRATIC DIAGNOSTIC & HINTS ---

    def diagnose_failure(
        self,
        db: Session,
        problem_id: uuid.UUID,
        user_code: str,
        verdict: str,
        error_detail: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Hierarchical RAG Diagnostic:
        1. Retrieves Canonical Editorial chunks for problem
        2. Retrieves closest historical user Pitfall Clusters
        3. Generates a grounded Socratic diagnosis that avoids spoiling the solution code.
        """
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return {"diagnosis": "Problem not found.", "retrieved_pitfalls": 0}

        # 1. Fetch canonical chunks
        canonical_chunks = db.query(ProblemKnowledgeChunk).filter(
            ProblemKnowledgeChunk.problem_id == problem.id
        ).all()
        canonical_context = "\n\n".join([f"[{c.title}]: {c.content}" for c in canonical_chunks[:3]])

        # 2. Vector search for closest historical pitfalls
        user_signature = f"Verdict: {verdict}\nError: {error_detail or ''}\nCode:\n{user_code[:600]}"
        query_vec = self.get_embedding(user_signature)

        all_pitfalls = db.query(SubmissionPitfall).filter(
            SubmissionPitfall.problem_id == problem.id
        ).all()

        scored_pitfalls = []
        for pf in all_pitfalls:
            if pf.embedding is not None:
                sim = self._cosine_similarity(query_vec, pf.embedding)
                scored_pitfalls.append((sim, pf))

        scored_pitfalls.sort(key=lambda x: x[0], reverse=True)
        top_pitfalls = [p for score, p in scored_pitfalls[:2] if score > 0.6]

        pitfall_context = ""
        if top_pitfalls:
            pf_lines = []
            for sim, p in scored_pitfalls[:2]:
                pf_lines.append(f"- Known Pitfall (Seen {p.occurrence_count} times): {p.pitfall_summary}\n  Socratic Guidance: {p.socratic_guidance}")
            pitfall_context = "HISTORICAL COMMUNITY PITFALL CLUSTERS:\n" + "\n".join(pf_lines)

        # 3. Assemble Socratic Prompt
        system = """You are an expert DSA mentor conducting a grounded Socratic failure diagnostic.
STRICT GUIDELINES:
1. Direct your feedback specifically to the student's code in the editor (reference their variables, loops, and logic structure).
2. NEVER output the full corrected code.
3. Ground your explanation on the canonical invariant and historical pitfall patterns.
4. Help the student understand WHY their specific code snippet resulted in the failure and what invariant to fix.
5. Structure clearly:
   - **🔍 Code Analysis & Logic Flaw**: Reference what line/variable in their code is causing the issue.
   - **🧠 Canonical Invariant**: The optimal property/relationship needed.
   - **💡 Guiding Question**: A non-spoiling question to guide them to fix it.
6. Do NOT output raw thoughts or drafting notes."""

        prompt = f"""PROBLEM: {problem.title} ({problem.difficulty.value if hasattr(problem.difficulty, 'value') else problem.difficulty})
VERDICT: {verdict.upper()}
ERROR / DETAILS: {error_detail or 'Output mismatch or limit exceeded'}

{canonical_context}

{pitfall_context}

STUDENT'S CODE IN EDITOR:
```python
{user_code}
```

Provide a grounded Socratic diagnosis of this specific code. Reference the student's code variables and logic."""

        diagnosis_text = ai_service.generate_response(prompt, system)
        return {
            "diagnosis": diagnosis_text,
            "matched_pitfalls": len(top_pitfalls),
            "historical_cluster_matched": bool(top_pitfalls)
        }

    def get_socratic_hint(
        self,
        db: Session,
        problem_id: uuid.UUID,
        user_code: str,
        hint_tier: int = 1
    ) -> Dict[str, Any]:
        """
        Retrieves Tier-1, Tier-2, or Tier-3 hints grounded in canonical database chunks.
        """
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return {"hint": "Problem not found.", "tier": hint_tier}

        tier_key = f"hint_tier_{max(1, min(hint_tier, 3))}"
        chunk = db.query(ProblemKnowledgeChunk).filter(
            ProblemKnowledgeChunk.problem_id == problem.id,
            ProblemKnowledgeChunk.chunk_type == tier_key
        ).first()

        canonical_hint_text = chunk.content if chunk else f"Think about the core data structure and invariants for {problem.title}."

        system = "You are a Socratic programming tutor. Provide a single targeted hint for the requested tier without writing the complete code."
        prompt = f"""PROBLEM: {problem.title}
REQUESTED HINT TIER: Tier {hint_tier} of 3 ({'High-level Intuition' if hint_tier == 1 else 'State Invariant' if hint_tier == 2 else 'Edge Cases & Step-by-Step Logic'})

CANONICAL HINT GUIDELINE:
{canonical_hint_text}

STUDENT'S CURRENT CODE:
```python
{user_code}
```

Give the student a helpful Tier {hint_tier} hint tailored to what they have written so far. Keep it concise (2-4 sentences) and Socratic."""

        hint_text = ai_service.generate_response(prompt, system)
        return {
            "hint": hint_text,
            "tier": hint_tier,
            "title": chunk.title if chunk else f"Tier {hint_tier} Hint"
        }

    # --- SEMANTIC SEARCH OVER PROBLEM BANK ---

    def semantic_search_problems(
        self,
        db: Session,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Natural language semantic search across the problem bank using vector similarity.
        """
        query_vec = self.get_embedding(query)
        chunks = db.query(ProblemKnowledgeChunk).all()

        if not chunks:
            # Fallback to standard problem title search if chunks not yet seeded
            probs = db.query(Problem).filter(Problem.title.ilike(f"%{query}%")).limit(limit).all()
            return [
                {
                    "id": str(p.id),
                    "title": p.title,
                    "slug": p.slug,
                    "difficulty": p.difficulty.value if hasattr(p.difficulty, "value") else p.difficulty,
                    "tags": p.tags or [],
                    "similarity": 1.0,
                    "matched_concept": p.description[:120] + "..."
                }
                for p in probs
            ]

        # Score chunks
        problem_scores: Dict[uuid.UUID, Dict[str, Any]] = {}
        for c in chunks:
            if c.embedding is not None:
                sim = self._cosine_similarity(query_vec, c.embedding)
                pid = c.problem_id
                if pid not in problem_scores or sim > problem_scores[pid]["similarity"]:
                    problem_scores[pid] = {
                        "similarity": sim,
                        "matched_concept": c.content[:140] + "...",
                        "chunk_title": c.title
                    }

        # Sort by similarity
        sorted_pids = sorted(problem_scores.items(), key=lambda x: x[1]["similarity"], reverse=True)[:limit]

        results = []
        for pid, score_info in sorted_pids:
            p = db.query(Problem).filter(Problem.id == pid).first()
            if p:
                results.append({
                    "id": str(p.id),
                    "title": p.title,
                    "slug": p.slug,
                    "difficulty": p.difficulty.value if hasattr(p.difficulty, "value") else p.difficulty,
                    "tags": p.tags or [],
                    "similarity": round(score_info["similarity"], 3),
                    "matched_concept": score_info["matched_concept"],
                    "chunk_title": score_info["chunk_title"]
                })

        return results

rag_service = RAGService()
