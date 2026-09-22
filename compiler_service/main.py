import os
import re
import json
import uuid
import tempfile
import shutil
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import docker
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

app = FastAPI(title="Submittery Compiler Service", version="2.0")

# Initialize Docker client
try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"Warning: Failed to connect to Docker daemon: {e}")
    docker_client = None

SANDBOX_IMAGE = "submittery_sandbox:latest"

@app.on_event("startup")
def build_sandbox_image():
    if not docker_client:
        print("Docker client not initialized. Skipping sandbox image build.")
        return
        
    try:
        # Check if image already exists
        docker_client.images.get(SANDBOX_IMAGE)
        print(f"Docker sandbox image '{SANDBOX_IMAGE}' already exists.")
    except docker.errors.ImageNotFound:
        print(f"Building Docker sandbox image '{SANDBOX_IMAGE}'...")
        # Path to sandbox folder
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sandbox_dir = os.path.join(base_dir, "sandbox")
        
        try:
            image, logs = docker_client.images.build(
                path=sandbox_dir,
                dockerfile="Dockerfile.sandbox",
                tag=SANDBOX_IMAGE,
                rm=True
            )
            print("Docker sandbox image built successfully.")
        except Exception as build_err:
            print(f"Error building sandbox image: {build_err}")

class TestCaseExec(BaseModel):
    id: str
    input: str
    expected_output: str

class ExecutionRequest(BaseModel):
    code: str
    language: str = "python"
    test_cases: List[TestCaseExec]
    time_limit: float = 1.0
    memory_limit: int = 256 # in MB

@app.post("/execute")
def execute_code(req: ExecutionRequest):
    if not docker_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Docker daemon is not reachable on the host system."
        )
        
    if req.language != "python":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{req.language}' is not currently supported."
        )

    # 1. Create a host temporary directory
    temp_parent = os.getenv("SANDBOX_TEMP_DIR", None)
    if temp_parent and not os.path.exists(temp_parent):
        os.makedirs(temp_parent, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="submittery_run_", dir=temp_parent)
    
    try:
        # 2. Write code to file
        code_filename = "solution.py"
        code_path_host = os.path.join(temp_dir, code_filename)
        with open(code_path_host, "w", encoding="utf-8") as f:
            f.write(req.code)
            
        # 3. Create runner configuration JSON
        config_data = {
            "code_path": "/workspace/solution.py",
            "time_limit": req.time_limit,
            "memory_limit": req.memory_limit,
            "test_cases": [
                {
                    "id": tc.id,
                    "input": tc.input,
                    "expected_output": tc.expected_output
                }
                for tc in req.test_cases
            ]
        }
        
        config_filename = "config.json"
        config_path_host = os.path.join(temp_dir, config_filename)
        with open(config_path_host, "w", encoding="utf-8") as f:
            json.dump(config_data, f)
            
        # 4. Prepare mounts (mounting host temp_dir as read-only /workspace)
        # On Windows Docker Desktop, we must convert windows paths to absolute paths
        # Docker SDK handles Windows path conversion, but let's make sure it is absolute
        host_abs_path = os.path.abspath(temp_dir)
        
        # 5. Run the sandbox container with strict resources
        # - Network disabled
        # - Read-only root filesystem
        # - CPU: 0.5 CPU limit
        # - Memory: req.memory_limit MB limit (let's give a buffer, e.g. 1.5x for python VM runtime overhead, capped at min 128M)
        container_mem_limit = max(128, int(req.memory_limit * 1.5))
        
        print(f"Launching sandbox container for path {host_abs_path}")
        container = docker_client.containers.run(
            image=SANDBOX_IMAGE,
            command=["/workspace/config.json"],
            volumes={
                host_abs_path: {
                    "bind": "/workspace",
                    "mode": "ro" # read-only mount
                }
            },
            network_mode="none",
            read_only=True,
            nano_cpus=int(0.5 * 1e9), # 0.5 cores
            mem_limit=f"{container_mem_limit}m",
            memswap_limit=f"{container_mem_limit}m",
            user="nobody",
            detach=True
        )
        
        # 6. Wait for container to exit (add a buffer, e.g. time_limit * testcases + 3.0s)
        max_duration = int(req.time_limit * len(req.test_cases)) + 5
        try:
            result = container.wait(timeout=max_duration)
            exit_status = result.get("StatusCode", 0)
        except Exception as wait_err:
            container.kill()
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Sandbox container execution timed out after {max_duration} seconds."
            )
            
        # 7. Collect stdout/stderr
        logs = container.logs(stdout=True, stderr=True).decode("utf-8")
        
        # Clean up the container
        container.remove()
        
        # 8. Parse the output JSON between ---RESULT_START--- and ---RESULT_END---
        match = re.search(r"---RESULT_START---\n(.*?)\n---RESULT_END---", logs, re.DOTALL)
        if not match:
            # Check if logs indicate memory limit or runtime error
            # If exit status is non-zero, check if it was due to OOM
            if exit_status != 0:
                # Docker exit code 137 indicates OOM (killed by Out Of Memory killer)
                if exit_status == 137:
                    # Return memory limit exceeded for the first testcase
                    return [
                        {
                            "id": req.test_cases[0].id,
                            "status": "memory_limit_exceeded",
                            "runtime": 0.0,
                            "memory": req.memory_limit * 1024,
                            "error": "Memory Limit Exceeded (Container OOM)"
                        }
                    ]
            
            # General compilation or runtime failure outside runner execution
            # Try to grab whatever was in logs
            error_msg = logs.strip() if logs else f"Sandbox container exited with status {exit_status}"
            return [
                {
                    "id": req.test_cases[0].id,
                    "status": "runtime_error",
                    "runtime": 0.0,
                    "memory": 0,
                    "error": error_msg
                }
            ]
            
        results = json.loads(match.group(1))
        return results
        
    except Exception as run_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compiler execution error: {str(run_err)}"
        )
    finally:
        # 9. Clean up temporary files on host
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
