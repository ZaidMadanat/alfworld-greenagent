# ALFWorld Green Agent - Architecture & AWS Setup

## Overview

This project implements an **evaluation framework** for ALFWorld where:
- **Green Agent**: Orchestrates battles, sets up environments, evaluates performance
- **White Agent**: Actually plays ALFWorld tasks and executes actions
- **AWS EC2 Instance**: Hosts the backend infrastructure and battle containers

## AWS Infrastructure

### What AWS Provides

Your AWS EC2 instance (`184.169.129.71`) hosts the following services:

1. **AgentBeats Backend** (Port 9000)
   - Central coordination service for agent battles
   - Tracks battle progress, logs, and results
   - All agents connect to this backend

2. **MCP Servers** (Ports 9001 & 9002)
   - **Port 9001**: General MCP server (Model Context Protocol)
   - **Port 9002**: ALFWorld-specific MCP server (`mcp_server.py`)
     - Provides `update_battle_process()` for logging
     - Provides `run_terminal_command_in_docker()` for container operations

3. **Docker Environment**
   - Runs ALFWorld battle containers (one per battle/episode)
   - Container naming: `alfworld-{battle_id}`
   - Each container isolates a battle execution

### How to Access AWS Server

#### 1. Download the Certificate
If you haven't already, download `alfworld-west-green.pem` to your local machine.

#### 2. Set Proper Permissions
```bash
chmod 400 alfworld-west-green.pem
```

#### 3. SSH into the Server
```bash
ssh -i alfworld-west-green.pem ec2-user@184.169.129.71
```

**Note**: If the certificate is in a different directory, provide the full path:
```bash
ssh -i /path/to/alfworld-west-green.pem ec2-user@184.169.129.71
```

### AWS Services Running on the Server

Once logged in, you'll find these services running:

- **AgentBeats Backend**: `http://184.169.129.71:9000`
- **MCP Server (General)**: `http://184.169.129.71:9001/sse`
- **MCP Server (ALFWorld)**: `http://184.169.129.71:9002/sse`
- **Docker**: Running ALFWorld containers for battles

## Architecture Flow

```
┌─────────────────┐
│  Local Machine  │
│                 │
│  Green Agent    │─────┐
│  (Orchestrator) │     │
│                 │     │
│  White Agent    │─────┤
│  (Player)       │     │
└─────────────────┘     │
                         │
                         ▼
         ┌───────────────────────────────┐
         │     AWS EC2 Instance          │
         │   184.169.129.71              │
         │                                │
         │  ┌─────────────────────────┐ │
         │  │ AgentBeats Backend       │ │
         │  │ Port 9000                │ │
         │  └─────────────────────────┘ │
         │                                │
         │  ┌─────────────────────────┐ │
         │  │ MCP Server (General)    │ │
         │  │ Port 9001               │ │
         │  └─────────────────────────┘ │
         │                                │
         │  ┌─────────────────────────┐ │
         │  │ MCP Server (ALFWorld)   │ │
         │  │ Port 9002               │ │
         │  │ (runs mcp_server.py)    │ │
         │  └─────────────────────────┘ │
         │                                │
         │  ┌─────────────────────────┐ │
         │  │ Docker Containers       │ │
         │  │ alfworld-{battle_id}    │ │
         │  │ (isolated per battle)   │ │
         │  └─────────────────────────┘ │
         └───────────────────────────────┘
```

## How Battles Work

1. **Green Agent starts** locally and connects to AWS backend
2. **Green Agent** sets up a task and creates a Docker container on AWS
3. **Green Agent** communicates with **White Agent** via A2A protocol
4. **White Agent** receives observations and sends actions back
5. **Green Agent** steps the ALFWorld environment in the Docker container
6. **Results** are logged to the AWS backend via MCP tools
7. **Green Agent** computes metrics and reports final scores

## Configuration Files

All AWS endpoints are configured in:

- **`scenario.toml`**: Main scenario configuration
- **`start_agents.py`**: Agent launch commands
- **`mcp_server.py`**: MCP server configuration
- **`agents/green_agent/agent_card_clean.toml`**: Green agent config

## Deployment Workflow

Based on your team's workflow:

1. **Push code to GitHub**
2. **SSH into AWS server** using the PEM certificate
3. **Pull latest code** on the server
4. **Build Docker image** for ALFWorld battles
5. **Restart services** if needed:
   - AgentBeats backend
   - MCP servers
   - Any running containers

## Common AWS Server Tasks

### Check Running Services
```bash
# Check if services are running
sudo systemctl status <service-name>

# Check Docker containers
docker ps

# Check specific battle containers
docker ps | grep alfworld-
```

### View Logs
```bash
# Backend logs (location depends on deployment)
tail -f /var/log/agentbeats/backend.log

# MCP server logs
tail -f /var/log/mcp-server.log

# Docker container logs
docker logs alfworld-{battle_id}
```

### Restart Services
```bash
# Restart backend (adjust based on your setup)
sudo systemctl restart agentbeats-backend

# Restart MCP server
sudo systemctl restart mcp-server
```

## For Your Group

### What Each Team Member Needs

1. **Access to AWS**:
   - The PEM certificate (`alfworld-west-green.pem`)
   - SSH access instructions (this document)

2. **Local Setup**:
   - Python environment with dependencies
   - Docker (if testing locally)
   - AgentBeats installed

3. **Understanding**:
   - Green Agent = Evaluator (runs on your machine)
   - White Agent = Player (runs on your machine)
   - AWS = Infrastructure (backend, logging, containers)

### Key Points

- **Agents run locally** - Green and White agents execute on team members' machines
- **AWS hosts infrastructure** - Backend coordination and battle containers
- **All communication** flows through AWS backend for tracking and logging
- **Battles are isolated** - Each battle gets its own Docker container on AWS

## Troubleshooting

### Can't connect to AWS backend
- Verify the server is running: `ping 184.169.129.71`
- Check firewall/security groups allow ports 9000-9002
- Verify backend service is running on the server

### Docker containers not starting
- SSH into AWS and check Docker daemon: `docker ps`
- Verify Docker image exists: `docker images | grep alfworld`
- Check container logs for errors

### MCP tools not working
- Verify MCP server is running on port 9002
- Check network connectivity to `184.169.129.71:9002`
- Review MCP server logs on AWS

