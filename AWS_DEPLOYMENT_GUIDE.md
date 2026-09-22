# 🚀 AWS EC2 Deployment & Continuous Delivery (CI/CD) Guide

This guide explains how to deploy **Submittery** to an **AWS EC2 instance** with continuous automatic deployment via **GitHub Actions** and **guaranteed database persistence** (pgvector + Redis).

---

## 📌 Architectural Guarantees

- **Zero Data Loss on Updates**: PostgreSQL and Redis data are stored in persistent Docker volumes backed by AWS EBS storage.
- **Continuous Deployment (CI/CD)**: Every `git push` to your GitHub branch automatically updates your live application via GitHub Actions.
- **Micro-Container Isolation**: The compiler sandbox executes untrusted Python code safely using Docker-out-of-Docker sandboxing.

---

## 🛠️ Step 1: Launch an AWS EC2 Instance

1. Log into your **AWS Management Console** and navigate to **EC2 -> Launch Instance**.
2. **Name**: `submittery-prod` (or your choice).
3. **OS Image (AMI)**: `Ubuntu Server 24.04 LTS` (or `22.04 LTS`), 64-bit (x86_64).
4. **Instance Type**: 
   - `t3.small` (2 vCPU, 2GB RAM) — Minimum recommended
   - `t3.medium` (2 vCPU, 4GB RAM) — Optimal for multi-user real-time judge & sandboxes
5. **Key Pair**: Create or select an existing `.pem` key pair (e.g. `submittery-key.pem`). **Download and keep this file safe.**
6. **Storage**: Set EBS root volume to at least **25 GB - 30 GB gp3**.
7. **Network / Security Group**:
   - Allow **SSH (Port 22)** from `0.0.0.0/0` (or your specific IP).
   - Allow **HTTP (Port 80)** from `0.0.0.0/0`.
   - Allow **HTTPS (Port 443)** from `0.0.0.0/0`.
8. Click **Launch Instance**.

---

## 💻 Step 2: Initial Server Setup (One-Time)

1. SSH into your newly created EC2 instance:
   ```bash
   ssh -i /path/to/submittery-key.pem ubuntu@<YOUR_EC2_PUBLIC_IP>
   ```

2. Clone your GitHub repository onto the instance:
   ```bash
   git clone https://github.com/<YOUR_GITHUB_USERNAME>/Submittery-An-AI-online-judge.git
   cd Submittery-An-AI-online-judge
   ```

3. Run the automated setup script:
   ```bash
   chmod +x scripts/*.sh
   ./scripts/setup_ec2.sh
   ```
   *(This installs Docker, Docker Compose, sets up the sandbox directory `/tmp/submittery_runs`, builds the sandbox image, and configures the firewall).*

4. Log out and log back in once to apply Docker user permissions:
   ```bash
   exit
   ssh -i /path/to/submittery-key.pem ubuntu@<YOUR_EC2_PUBLIC_IP>
   cd Submittery-An-AI-online-judge
   ```

5. Create your production `.env` file on the server:
   ```bash
   cp .env.example .env
   nano .env
   ```
   Fill in your production secrets:
   ```env
   # App
   SECRET_KEY=generate_a_secure_random_hex_key_here
   DEBUG=False

   # AI & OAuth
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   GOOGLE_CLIENT_ID=your_google_oauth_client_id.apps.googleusercontent.com

   # Database credentials (used inside Docker network)
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_strong_postgres_password_here
   POSTGRES_DB=submittery
   ```

6. Start the production stack for the first time:
   ```bash
   ./scripts/deploy.sh
   ```
   *Your app is now live at `http://<YOUR_EC2_PUBLIC_IP>`!*

---

## ⚡ Step 3: Configure Automated GitHub Actions CI/CD

To make GitHub automatically update your AWS server whenever you `git push`:

1. Go to your GitHub repository in your browser.
2. Click **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**.
3. Add the following secrets:

| Secret Name | Value Description |
| :--- | :--- |
| `AWS_HOST` | The **Public IPv4 address** (or Elastic IP) of your EC2 instance. |
| `AWS_USER` | `ubuntu` |
| `AWS_SSH_KEY` | The **entire contents of your `.pem` file** (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`). |
| `PROJECT_DIR` | (Optional) Path on EC2: `/home/ubuntu/Submittery-An-AI-online-judge` |

---

## 🔄 How the CI/CD Pipeline Works

Whenever you push commits to GitHub:
```bash
git add .
git commit -m "Add new feature"
git push origin main
```

1. GitHub Actions triggers the workflow in [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml).
2. It securely connects to your AWS EC2 instance via SSH.
3. It runs `scripts/deploy.sh`, which:
   - Pulls the newest code (`git pull`).
   - Rebuilds only the updated application images.
   - Restarts `backend`, `worker`, `compiler`, and `nginx`.
   - **Leaves `submittery_db` and `submittery_redis` untouched**, ensuring **100% data persistence and zero downtime**.

---

## 🔒 Optional: Free SSL / HTTPS with Let's Encrypt

If you point a custom domain (e.g. `judge.yourdomain.com`) to your EC2 IP:

1. Install Certbot on EC2:
   ```bash
   sudo apt-get install -y certbot python3-certbot-nginx
   ```
2. Stop the docker nginx temporarily or use certbot standalone:
   ```bash
   docker stop submittery_nginx
   sudo certbot certonly --standalone -d judge.yourdomain.com
   docker start submittery_nginx
   ```
3. Mount the certificates into `docker-compose.prod.yml` and enable HTTPS in `nginx/nginx.conf`.

---

## 💾 Automated Database Backups

A backup script is included at `scripts/backup_db.sh`.
To run automated daily backups at 3:00 AM, add a cron job on your EC2 instance:
```bash
crontab -e
```
Add the line:
```cron
0 3 * * * /home/ubuntu/Submittery-An-AI-online-judge/scripts/backup_db.sh >> /home/ubuntu/submittery_backup.log 2>&1
```
