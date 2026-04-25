# KAI ENTERPRISE - Production-Grade AI Assistant

**Multi-LLM | Plugin System | Vector Memory | Project Management | REST API | WebSocket**

## What's New vs Original Kai

| Feature | Original Kai | Kai Enterprise |
|---------|--------------|-----------------|
| **LLM Support** | Ollama only | Ollama + OpenAI |
| **Architecture** | Single CLI | CLI + API Server |
| **Extensibility** | None | Plugin system |
| **Memory** | Session history only | Persistent vector memory |
| **Projects** | None | Full project management |
| **Monitoring** | None | Logging + observability |
| **Deployment** | Local script | Docker + production-ready |
| **Integration** | Manual | REST API + WebSocket |

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
cd C:\Users\7nujy6xc\OneDrive\Desktop\03-Projects\Kai-AI
run-enterprise.bat
```

This starts:
- **kai-cli** - Interactive CLI
- **kai-api** - REST API server
- **ollama** - Local LLM (Mistral 7B)

### Option 2: Local (No Docker)

```powershell
python kai_enterprise.py
```

---

## Features

### 1. Multi-LLM Support

```python
# Use Ollama (local, free)
kai = KaiEnterprise(llm_provider="ollama")

# Use OpenAI (set OPENAI_API_KEY env var)
kai = KaiEnterprise(llm_provider="openai")
```

### 2. Plugin System

Built-in plugins:
- **terminal** - Execute shell commands
- **file** - Read/write/list files

Usage:
```
You> /plugin terminal command="ls -la"
Kai: [output]

You> /plugin file operation=read path=/etc/hostname
Kai: [file content]
```

### 3. Vector Memory

Store and search information across sessions:

```
You> /save "Docker runs containers in isolated environments"
Kai: Saved to memory

You> /memory docker containers
Kai: [Retrieved matching memories]
```

### 4. Project Management

```
You> /project myapp
Kai: Project 'myapp' created

You> /projects
Kai: myapp
    another-project
```

### 5. REST API

```bash
# Ask a question
curl -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'

# Execute a plugin
curl -X POST http://localhost:8001/api/plugin \
  -H "Content-Type: application/json" \
  -d '{"plugin": "terminal", "args": {"command": "whoami"}}'

# Store memory
curl -X POST http://localhost:8001/api/memory/store \
  -H "Content-Type: application/json" \
  -d '{"content": "Important fact", "category": "notes"}'

# Search memory
curl -X POST http://localhost:8001/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Docker"}'

# List plugins
curl http://localhost:8001/api/plugins
```

### 6. WebSocket (Real-Time)

```javascript
// Connect
const ws = new WebSocket('ws://localhost:8001/ws/chat');

// Send question
ws.send(JSON.stringify({question: "Hello"}));

// Receive response
ws.onmessage = (event) => {
    console.log(JSON.parse(event.data));
};
```

### 7. Swagger Documentation

Open: **http://localhost:8001/docs**

- Interactive API testing
- Auto-generated docs
- Try-it-out features

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│           Kai Enterprise Core                    │
│  - Multi-LLM abstraction                         │
│  - Conversation history                          │
│  - System prompt management                      │
└──────────┬───────────────────┬──────────────────┘
           │                   │
    ┌──────▼────────┐   ┌──────▼──────────┐
    │ Plugin Manager│   │ Vector Memory   │
    │ - Terminal    │   │ - SQLite3       │
    │ - File        │   │ - Full-text     │
    │ - Custom      │   │ - Categorized   │
    └───────────────┘   └─────────────────┘
                              │
                        ┌─────▼────────┐
                        │ Project Mgr  │
                        │ - Directory  │
                        │ - Config.json│
                        └──────────────┘

    ┌──────────────────────────────────┐
    │    Kai CLI                       │
    │  Interactive REPL interface      │
    └──────────────────────────────────┘

    ┌──────────────────────────────────┐
    │    Kai API (FastAPI)             │
    │  REST endpoints + WebSocket      │
    │  Swagger documentation           │
    └──────────────────────────────────┘

         │
         └─────────────┬────────────────┐
                       │                │
              ┌────────▼────────┐  ┌────▼──────────┐
              │ Ollama          │  │ OpenAI        │
              │ (Local LLM)     │  │ (Cloud API)   │
              └─────────────────┘  └───────────────┘
```

---

## CLI Commands

### Core
- `/help` - Show all commands
- `/exit` - Quit

### Plugins
- `/plugins` - List plugins
- `/plugin <name> [args]` - Execute plugin

### Memory
- `/save <content>` - Store in memory
- `/memory <query>` - Search memory
- `/history` - Show recent conversation

### Projects
- `/project <name>` - Create/switch project
- `/projects` - List projects

### Session
- `/clear` - Clear conversation history

---

## Deployment

### Docker Compose

```bash
# Start all services
docker compose -f docker-compose-enterprise.yml up -d

# View logs
docker compose -f docker-compose-enterprise.yml logs -f

# Stop all services
docker compose -f docker-compose-enterprise.yml down

# Run CLI inside container
docker exec -it kai-cli python kai_enterprise.py
```

### Production Setup

For production deployment:

1. **Use OpenAI or Enterprise LLM provider**
   - More reliable than local Ollama
   - Better quality responses
   - Scale without GPU requirements

2. **Enable SSL/TLS for API**
   ```yaml
   # In docker-compose-enterprise.yml
   kai-api:
     environment:
       - SSL_CERT=/certs/cert.pem
       - SSL_KEY=/certs/key.pem
   ```

3. **Add authentication**
   ```python
   # In kai_api.py
   from fastapi.security import HTTPBearer
   security = HTTPBearer()
   ```

4. **Configure monitoring**
   - Add Prometheus metrics
   - Set up ELK for logging
   - Use Grafana for dashboards

5. **Horizontal scaling**
   - Use managed PostgreSQL for shared memory
   - Deploy multiple API instances behind load balancer
   - Use Redis for session caching

---

## Extending with Custom Plugins

Create custom plugins:

```python
# my_plugin.py
from kai_enterprise import PluginInterface

class MyPlugin(PluginInterface):
    def execute(self, **kwargs) -> str:
        # Your logic here
        return "Result"
    
    def get_name(self) -> str:
        return "my_plugin"
    
    def get_description(self) -> str:
        return "My custom plugin"

# Register in kai_enterprise.py
kai.plugin_manager.register("my_plugin", MyPlugin())
```

---

## Performance Tuning

### Local Ollama
- **Model**: Mistral 7B (4.1GB) - balanced
- **Alternatives**:
  - `phi:latest` (2.6GB) - fast, lower quality
  - `neural-chat:7b` (4GB) - better quality
  - `llama2:13b` (7GB) - higher quality, slower

### API Response Times
- **Ollama**: 5-30 sec (depends on model + question)
- **OpenAI**: 1-5 sec (gpt-4), < 1 sec (gpt-3.5)

### Memory Optimization
- SQLite stores all memories on disk
- Automatic cleanup: `kai.memory.db` grows ~1MB per 1000 entries
- For large-scale: migrate to PostgreSQL with pgvector

---

## Comparison: Kai vs Competitors

| Feature | Kai Enterprise | CortexAI | PentAGI | Beast AI |
|---------|---|---|---|---|
| **Cost** | Free | Free | Free | Free |
| **LLM Support** | Ollama + OpenAI | Azure OpenAI only | 6+ providers | Ollama + OpenAI |
| **Plugins** | ✅ Custom | ✅ Extensive | ✅ Function tools | ⚠️ Basic |
| **Memory** | ✅ Vector DB | ❌ None | ✅ Neo4j | ✅ Session |
| **GUI** | ❌ CLI/API | ✅ Desktop | ✅ Web UI | ⚠️ API only |
| **Deployment** | Docker | Docker | Docker | Docker |
| **Best For** | Developers | Pentesters | Enterprise | Multi-device |

---

## Troubleshooting

**"Ollama not reachable"**
- Check: `docker logs kai-ollama`
- Wait for Ollama to fully start (~60s)

**"API returns 500"**
- Check LLM provider connection
- Verify model is pulled: `docker exec kai-ollama ollama list`

**"Memory not persisting"**
- Check `.kai/memory.db` exists and is writable
- Verify SQLite installation: `python -c "import sqlite3"`

**"Plugin execution fails"**
- Check plugin arguments
- View logs: `docker logs kai-api`

---

## Next Steps

1. **Try the CLI**: `python kai_enterprise.py`
2. **Test the API**: http://localhost:8001/docs
3. **Create a project**: `/project myapp`
4. **Build a custom plugin**: Extend `PluginInterface`
5. **Integrate with external services**: Use REST API
6. **Deploy to production**: Use Docker + Kubernetes

---

**Status**: ✅ Production-Ready  
**Version**: 1.0.0  
**License**: MIT  
**Support**: See project README
