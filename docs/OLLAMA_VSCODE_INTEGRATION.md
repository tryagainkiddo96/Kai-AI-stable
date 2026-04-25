# Ollama + VS Code Integration Guide
# For Local Ollama Installation

## Available VS Code Extensions for Ollama

### 1. Continue.dev (Recommended)
**Best all-around solution with chat + code completion**

Installation:
1. Install Continue extension in VS Code
2. Configure to use local Ollama:
```json
{
  "models": [
    {
      "title": "Ollama",
      "provider": "ollama",
      "model": "codellama:7b-instruct",
      "apiBase": "http://localhost:11434"
    }
  ]
}
```

Features:
- Code completion as you type
- Chat interface in sidebar
- Context-aware suggestions
- Multiple model support

### 2. Ollama Extension
**Dedicated Ollama integration**

Installation:
1. Search for "Ollama" in VS Code extensions
2. Configure models and endpoints

Features:
- Direct Ollama API integration
- Model management
- Chat interface

### 3. Tabby
**Open-source code completion**

Installation:
1. Install Tabby extension
2. Configure Ollama endpoint:
```json
{
  "tabby.endpoint": "http://localhost:11434",
  "tabby.model": "codellama:7b-code"
}
```

Features:
- Lightweight code completion
- Privacy-focused (local only)
- Fast inference

### 4. LLM Extension
**Multi-provider AI assistant**

Installation:
1. Install "LLM" extension
2. Configure Ollama provider

Features:
- Multiple AI providers
- Code explanation
- Refactoring suggestions

---

## Recommended Setup for Your System

### Step 1: Verify Ollama is Running
```bash
ollama list
ollama serve
```

### Step 2: Install Recommended Extension
**Continue.dev** - Best balance of features and performance

### Step 3: Configuration
```json
// .vscode/settings.json
{
  "continue.models": [
    {
      "title": "CodeLlama 7B",
      "provider": "ollama",
      "model": "codellama:7b-instruct",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "DeepSeek Coder",
      "provider": "ollama", 
      "model": "deepseek-coder:6.7b",
      "apiBase": "http://localhost:11434"
    }
  ]
}
```

### Step 4: RAM-Optimized Models for 8GB System

**Lightweight Models (Good for 8GB RAM):**
```bash
# Install efficient models
ollama pull codellama:7b-code
ollama pull deepseek-coder:6.7b
ollama pull llama2:7b-chat
ollama pull mistral:7b
```

**Avoid Heavy Models:**
- codellama:13b (too big)
- llama2:13b (memory intensive)
- Any 30B+ models

---

## Usage Examples

### Code Completion
- Type code normally, get AI suggestions
- Use Ctrl+Space to trigger completions
- Tab to accept suggestions

### AI Chat
- Open Continue sidebar (Ctrl+Shift+P → "Continue: Open Chat")
- Ask questions about your code
- Get explanations and refactoring suggestions

### Code Actions
- Highlight code → Right-click → "Continue: Explain"
- Get AI-powered code improvements
- Debug assistance

---

## Performance Tips for 8GB RAM

### 1. Model Selection
```bash
# Check memory usage
ollama ps

# Stop unused models
ollama stop model_name

# Use efficient models
ollama pull phi:2.7b    # Very lightweight
ollama pull orca-mini:3b # Small but capable
```

### 2. VS Code Settings
```json
{
  "continue.streaming": true,
  "continue.maxTokens": 256,
  "continue.temperature": 0.3,
  "continue.contextLength": 2048
}
```

### 3. Memory Management
- Close unused VS Code windows
- Disable other extensions temporarily
- Use lightweight themes
- Monitor RAM usage with Task Manager

---

## Integration with Kai

### Use Kai + Ollama Together
```bash
# In Kai terminal
/pentest recon example.com  # Uses cloud server
ollama run codellama:7b     # Local Ollama for code help

# VS Code with both
# - Continue.dev for code completion
# - Kai terminal for security tasks
# - Cloud server for heavy processing
```

### Best Workflow
1. **Code in VS Code** with Ollama completion
2. **Test security** with Kai cloud server
3. **Debug issues** with AI assistance
4. **Deploy to cloud** when ready

---

## Troubleshooting

### Ollama Connection Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve

# Check VS Code extension logs
# View → Output → Continue
```

### Memory Issues
```bash
# Monitor memory
htop  # or Task Manager

# Free up RAM
ollama stop all
kill unnecessary processes
```

### VS Code Performance
- Disable unused extensions
- Use lightweight theme
- Close unused files
- Use "Developer: Reload Window"

---

This setup gives you professional AI coding assistance while staying within your 8GB RAM limits!</content>
<parameter name="filePath">C:\Users\7nujy6xc\OneDrive\Desktop\Kai-AI\docs\OLLAMA_VSCODE_INTEGRATION.md