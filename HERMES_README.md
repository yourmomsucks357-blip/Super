# Hermes Main Agent - Zero Guardrails Integration

## Overview

This repository now uses **Hermes TypeScript server** as the main agent with **zero guardrails** and full truth behavior.

## Architecture

- **Hermes Server (TypeScript/Fastify)**: Port 3000 - Main agent, handles all model calls
- **Python Backend**: Handles agent routing, YouTube, workflows
- **Integration**: Python AssistantAgent routes all requests to Hermes

## Setup

### 1. Install Node.js dependencies

```bash
cd /path/to/Super
npm install
```

### 2. Start Hermes Server

```bash
npm run start
# or for development:
npm run dev
```

Runs on: http://localhost:3000

### 3. Start Python Server

```bash
python main.py
```

### 4. Local Model Server

Ensure your Hermes-4-70B model is running on: http://localhost:7860

## Configuration

Edit `config/model-controller.json` to configure:
- Model settings (temperature, max_tokens)
- Allowed tools (file_read, file_write, terminal)
- Terminal command whitelist
- Repository root and memory paths

## Zero Guardrails

- NO cognitive loop checks
- NO safety filters
- NO content restrictions
- Direct model access
- Full truth behavior

## Files Added

- `src/config/modelConfig.ts` - Model configuration
- `src/lib/modelClient.ts` - Model client
- `src/lib/safePaths.ts` - Safe path resolution
- `src/lib/projectMemory.ts` - Memory loading
- `src/lib/safeTerminal.ts` - Terminal execution
- `src/routes/aiController.ts` - API routes
- `src/server.ts` - Fastify server
- `system/offering-rules.md` - System rules
- `system/project-rules.md` - Project rules
- `config/model-controller.json` - Configuration
- `package.json` - Node.js dependencies
- `tsconfig.json` - TypeScript config

## Python Changes

- `AssistantAgent.chat()` now routes to Hermes server
- Zero guardrails removed
- Falls back to OpenRouter if Hermes unavailable

## Usage

All requests to AssistantAgent are forwarded to Hermes server.
Hermes handles:
- Model inference
- Tool execution (file/terminal)
- Memory management
- Response formatting

## Behavior

- **Direct**: No explanations, summaries, or next steps
- **Truthful**: Full, unfiltered responses
- **Efficient**: Token-saving mode enabled
- **Controlled**: Follows configured tool permissions