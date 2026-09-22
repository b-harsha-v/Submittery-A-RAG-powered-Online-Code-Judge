import os
import sys
import json
import time
import httpx
from sqlalchemy.orm import Session

# Add project root to path to allow importing backend app modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.app.database import SessionLocal
from backend.app.config import settings
from backend.app.models.submission import Submission, SubmissionStatus
from backend.app.models.problem import Problem, TestCase
from backend.app.services.queue_service import queue_service
from backend.app.services.rag_service import rag_service

def process_submission(submission_id: str):
    db: Session = SessionLocal()
    print(f"[*] Processing submission {submission_id}...")
    
    try:
        # 1. Fetch submission details
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            print(f"[!] Submission {submission_id} not found in database.")
            return

        # 2. Update status to RUNNING
        submission.status = SubmissionStatus.RUNNING
        db.commit()
        db.refresh(submission)
        
        # Publish RUNNING status update
        queue_service.publish_status_update(
            submission_id=submission_id,
            status=SubmissionStatus.RUNNING.value
        )
        
        # 3. Retrieve problem and test cases
        problem = db.query(Problem).filter(Problem.id == submission.problem_id).first()
        if not problem:
            raise ValueError(f"Problem {submission.problem_id} not found.")
            
        test_cases = db.query(TestCase).filter(TestCase.problem_id == problem.id).all()
        if not test_cases:
            raise ValueError(f"No test cases found for problem {problem.title}.")
            
        # 4. Prepare execution payload
        payload = {
            "code": submission.code,
            "language": submission.language,
            "time_limit": problem.time_limit,
            "memory_limit": problem.memory_limit,
            "test_cases": [
                {
                    "id": str(tc.id),
                    "input": tc.input,
                    "expected_output": tc.expected_output
                }
                for tc in test_cases
            ]
        }
        
        # 5. Send code to Compiler Service
        print(f"[*] Sending code to Compiler Service: {settings.COMPILER_SERVICE_URL}/execute")
        with httpx.Client() as client:
            response = client.post(
                f"{settings.COMPILER_SERVICE_URL}/execute",
                json=payload,
                timeout=float(problem.time_limit * len(test_cases)) + 10.0
            )
            
        if response.status_code != 200:
            raise RuntimeError(f"Compiler service returned status {response.status_code}: {response.text}")
            
        results = response.json()
        print(f"[*] Received compiler execution results: {results}")
        
        # 6. Aggregate results across all test cases
        # Verdict logic:
        # - The overall status is the first non-accepted status encountered.
        # - Max runtime across all test cases.
        # - Max memory usage across all test cases.
        overall_status = SubmissionStatus.AC
        max_runtime = 0.0
        max_memory = 0
        error_message = None
        
        for tc_res in results:
            status_str = tc_res.get("status")
            runtime = tc_res.get("runtime", 0.0)
            memory = tc_res.get("memory", 0) # in KB
            error = tc_res.get("error")
            
            # Record maximums
            if runtime > max_runtime:
                max_runtime = runtime
            if memory > max_memory:
                max_memory = memory
                
            # If not accepted and we haven't found a failure yet
            if status_str != "accepted" and overall_status == SubmissionStatus.AC:
                # Map compiler status to SubmissionStatus Enum
                if status_str == "time_limit_exceeded":
                    overall_status = SubmissionStatus.TLE
                elif status_str == "memory_limit_exceeded":
                    overall_status = SubmissionStatus.MLE
                elif status_str == "wrong_answer":
                    overall_status = SubmissionStatus.WA
                elif status_str == "compilation_error":
                    overall_status = SubmissionStatus.CE
                else:
                    overall_status = SubmissionStatus.RE
                    
                error_message = error
                
        # 7. Update Submission in DB
        submission.status = overall_status
        submission.runtime = round(max_runtime, 3)
        # Convert memory to KB (compiler script returns RSS in KB)
        submission.memory = max_memory
        submission.error_message = error_message
        submission.results = results
        db.commit()
        db.refresh(submission)
        
        # 8. Publish final results
        queue_service.publish_status_update(
            submission_id=submission_id,
            status=overall_status.value,
            runtime=submission.runtime,
            memory=submission.memory,
            error_message=submission.error_message,
            results=results
        )
        print(f"[+] Submission {submission_id} finished processing. Verdict: {overall_status.value}")

        # 9. Asynchronously harvest failure pattern into RAG memory if not accepted
        if overall_status not in [SubmissionStatus.AC, SubmissionStatus.INTERNAL_ERROR, SubmissionStatus.CE]:
            try:
                failed_tc_input = None
                for tc_res in (results or []):
                    if tc_res.get("status") != "accepted":
                        failed_tc_input = tc_res.get("input")
                        break
                
                rag_service.harvest_failure_pitfall(
                    db=db,
                    problem_id=submission.problem_id,
                    verdict=overall_status.value,
                    code=submission.code,
                    error_detail=submission.error_message,
                    failed_test_input=failed_tc_input
                )
            except Exception as harvest_err:
                print(f"[*] Note: Non-critical failure in RAG pitfall harvesting: {harvest_err}")
        
    except Exception as e:
        print(f"[!] Error processing submission {submission_id}: {str(e)}")
        # Rollback database changes, update status to INTERNAL_ERROR
        db.rollback()
        try:
            # Re-fetch submission in case of session mismatch
            submission = db.query(Submission).filter(Submission.id == submission_id).first()
            if submission:
                submission.status = SubmissionStatus.INTERNAL_ERROR
                submission.error_message = f"Internal Worker Error: {str(e)}"
                db.commit()
                
                queue_service.publish_status_update(
                    submission_id=submission_id,
                    status=SubmissionStatus.INTERNAL_ERROR.value,
                    error_message=submission.error_message
                )
        except Exception as update_err:
            print(f"[!] Critical: Failed to write fallback error to DB: {update_err}")
    finally:
        db.close()

def main():
    print("[*] Starting Submittery v2 Background Worker...")
    import redis
    
    # Initialize redis connection
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    print(f"[*] Connected to Redis at {settings.REDIS_URL}")
    print("[*] Waiting for submissions queue...")
    
    while True:
        try:
            # BLPOP blocks until a submission is pushed to "submissions_queue"
            # It returns a tuple (queue_name, popped_value)
            job = r.blpop("submissions_queue", timeout=5)
            if job:
                queue_name, submission_id = job
                process_submission(submission_id)
        except redis.exceptions.ConnectionError:
            print("[!] Redis connection lost. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n[*] Shutting down worker.")
            break
        except Exception as e:
            print(f"[!] Worker Loop Exception: {e}")
            time.sleep(2)

if __name__ == '__main__':
    main()
