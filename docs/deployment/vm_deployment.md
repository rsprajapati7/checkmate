# CheckMate - OCI VM Backend Deployment & Offline LLM Configuration

This document provides a guide for deploying the CheckMate / Suraksha 2.0 Backend Core on an Oracle Cloud Infrastructure (OCI) VM instance running fully offline using a host-installed Ollama model.

---

## 1. VM Hardware Specifications
The backend is deployed on a VM with the following details:
- **Provider**: Oracle Cloud Infrastructure (OCI)
- **Shape**: `VM.Standard.E5.Flex`
- **CPU**: 1 OCPU (AMD E5 processor)
- **RAM**: 12 GB RAM
- **OS**: Ubuntu 22.04 LTS

---

## 2. Docker Compose Backend Deployment
The backend core is containerized and managed using Docker Compose.

### Directory Structure on VM
The project is cloned at `~/checkmate` on the remote instance:
```
~/checkmate/
├── docker-compose.yml
├── Dockerfile
├── backend/
│   ├── main.py
│   └── ...
└── .env
```

### docker-compose.yml configuration
The compose file maps port `8000` to the host and defines `extra_hosts` to resolve `host.docker.internal` to the host gateway:
```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./tmp:/app/tmp
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### .env Configuration (VM)
Configure the backend to use the host's Ollama service by setting `OLLAMA_API_BASE` to `host.docker.internal`:
```ini
LLM_PROVIDER=ollama
LLM_MODEL=gemma:2b
OLLAMA_API_BASE=http://host.docker.internal:11434
ENVIRONMENT=development
PORT=8000
```

---

## 3. Host Ollama Installation & Configuration
To run Gemma fully offline without a GPU, Ollama is installed directly on the VM host.

### Step 1: Install Ollama
Install Ollama via the official installation script:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Systemd Global Binding
By default, Ollama binds only to `127.0.0.1:11434`. To allow access from the Docker container bridge interface, configure a systemd override.

Create the override directory:
```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
```

Create `/etc/systemd/system/ollama.service.d/override.conf` and specify the bind address:
```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
```

Reload systemd daemon and restart Ollama service:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Step 3: Pull Gemma Model
Pull the light weight Gemma model:
```bash
ollama pull gemma:2b
```

---

## 4. Firewall & Routing Configuration
On Ubuntu VMs, `iptables` and local firewall chains block internal Docker bridge traffic from reaching services listening on the host. 

Traffic sent from the API container to `host.docker.internal` (resolving to the host gateway IP) hits the host's `INPUT` chain, which by default rejects all traffic not matching pre-existing rules.

### Port 11434 Accept Rule Placement
To fix the `No route to host` error, the `ACCEPT` rule for port `11434` must be positioned *before* the general `REJECT` rule in the `INPUT` chain.

Insert the ACCEPT rule at line 5 (prior to the reject rule):
```bash
sudo iptables -I INPUT 5 -p tcp --dport 11434 -j ACCEPT
```

### Verify Rules
Verify that the `ACCEPT` rule is active and placed above the `REJECT` rule:
```bash
sudo iptables -L INPUT -n -v --line-numbers
```

Expected Output:
```
num   pkts bytes target     prot opt in     out     source               destination         
...
5        0     0 ACCEPT     tcp  --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:11434
6       13  1336 REJECT     all  --  *      *       0.0.0.0/0            0.0.0.0/0            reject-with icmp-host-prohibited
```

Save the rules to make them persistent across reboots:
```bash
sudo netfilter-persistent save
```

---

## 5. Client CLI Connection Setup
To route your local CheckMate CLI commands to the remote OCI VM backend, update the client configuration.

Modify `~/.checkmate/config.json` on your local system:
```json
{
  "api_url": "http://<VM_PUBLIC_IP>:8000"
}
```

Start the interactive CLI:
```bash
python -m checkmate_cli
```
On startup, the CLI will output `[ OK ] Gemma LLM: ollama/gemma:2b — ok` indicating that the backend can successfully query Ollama.
