#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  Deploying Latest Submittery Release...  "
echo "=========================================="

# 1. Pull latest code from GitHub
echo "[*] Pulling latest commits from GitHub..."
git pull

# 2. Ensure sandbox temp directory exists
mkdir -p /tmp/submittery_runs
chmod 777 /tmp/submittery_runs 2>/dev/null || true

# 3. Ensure sandbox image is up-to-date
if [ -d "compiler_service/sandbox" ]; then
    echo "[*] Updating sandbox runtime image..."
    docker build -t submittery_sandbox:latest -f compiler_service/sandbox/Dockerfile.sandbox compiler_service/sandbox
fi

# 4. Start DB & Redis if not already running (preserves existing volumes)
echo "[*] Ensuring persistent database and redis state..."
docker compose -f docker-compose.prod.yml up -d db redis

# 5. Build and reload Application Containers seamlessly
echo "[*] Building and reloading application containers..."
docker compose -f docker-compose.prod.yml build backend worker compiler
docker compose -f docker-compose.prod.yml up -d --no-deps backend worker compiler nginx

# 6. Clean up unused build cache & dangling images to save EBS storage
echo "[*] Cleaning up dangling Docker images..."
docker image prune -f

echo "=========================================="
echo "  [SUCCESS] Deployment Completed!         "
echo "=========================================="
docker compose -f docker-compose.prod.yml ps
