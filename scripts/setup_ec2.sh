#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  Submittery AWS EC2 Initial Setup Script "
echo "=========================================="

# 1. Update packages
echo "[*] Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install prerequisites
echo "[*] Installing required utilities..."
sudo apt-get install -y curl git ufw ca-certificates gnupg lsb-release

# 3. Install Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo "[*] Installing Docker Engine..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    echo "[+] Docker installed successfully."
fi

# 4. Create host sandbox directory
echo "[*] Preparing sandbox mount directory..."
sudo mkdir -p /tmp/submittery_runs
sudo chmod 777 /tmp/submittery_runs

# 5. Build the Python Sandbox Container Image
echo "[*] Building local sandbox container image (submittery_sandbox:latest)..."
if [ -d "compiler_service/sandbox" ]; then
    docker build -t submittery_sandbox:latest -f compiler_service/sandbox/Dockerfile.sandbox compiler_service/sandbox
    echo "[+] Sandbox image built."
fi

# 6. Configure Basic Firewall
echo "[*] Configuring UFW firewall (SSH, HTTP, HTTPS)..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "=========================================="
echo "  [SUCCESS] EC2 Host Initialized!         "
echo "  Please log out and log back in once to  "
echo "  apply Docker group permissions.         "
echo "=========================================="
