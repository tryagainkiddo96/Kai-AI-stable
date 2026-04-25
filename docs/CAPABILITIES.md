# Kai Capabilities & Natural Language Invocation

Kai can understand natural language and activate abilities automatically. Just ask.

## How Kai Understands You

Kai uses **smart routing** to detect your intent:
- **Direct actions**: "scan the system", "take a screenshot", "wifi scan"
- **Questions**: "what's on my screen?" → auto-captures & analyzes
- **Tasks**: "get me the release form from..." → plans & executes steps
- **Chat**: Everything else → uses Ollama to understand context

## Abilities You Can Request

### Vision & Screen
```
/hardware screenshot          → Take screen screenshot
/hardware ocr                 → Perform OCR on screen content
"capture the screen"          → Screenshot + OCR
"what do you see?"            → Active window analysis
"read what's on screen"       → OCR the desktop
"scan the room" / "vision"    → Webcam capture + analysis
```

### Hardware & Sensors
```
/hardware wifi-scan           → Scan WiFi networks with signal strength
/hardware wifi-status         → Show current WiFi connection details
/hardware system-info         → Display CPU, memory, storage info
/hardware network-info        → Show network interface details
/hardware monitor <seconds>   → Monitor system resources over time
/hardware status              → Show hardware integration capabilities
```

### System Monitoring
```
"scan the system"             → Check CPU, memory, processes
"what's running?"             → List active programs
"monitor the network"         → Show network activity
"are there any threats?"      → Security scan
```

### Network & Security
```
"scan wifi"                   → WiFi networks and signal
"bluetooth scan"              → Nearby Bluetooth devices
"network status"              → Connection details
"check security"              → Tool policy & firewall status
```

### Advanced Pentesting (Kai Pentest Mode)
```
/pentest on"                 → Activate enhanced pentesting mode
"/pentest recon <target>"     → Comprehensive reconnaissance (DNS, WHOIS, CMS, certificates, links)
/pentest assess <target>"    → Automated vulnerability assessment with correlation analysis
"/pentest scan <target>"      → Nmap port scanning on authorized targets
"/pentest authorize <target>" → Authorize targets for security testing
"/pentest list tools"         → Browse 50+ integrated Kali security tools
"/pentest run <command>"      → Execute Kali commands with safety controls
```

### Kali Linux Tool Integration (Real Execution)
```
/kali status                 → Check Docker/Kali container status
/kali tools                  → List 10+ available Kali Linux tools
/kali install <tool>         → Install specific Kali tools (nmap, nikto, sqlmap, etc.)
/kali scan <target>          → Execute real nmap scans in Kali container
/kali webscan <url>          → Nikto web server vulnerability scanning
/kali sqltest <url>          → SQLMap SQL injection testing
/kali run <tool> <command>   → Execute custom Kali tool commands
/kali cleanup                → Remove Kali containers
```
**Real Kali Tools Available:**
- 🔴 **High Risk:** metasploit, hashcat, hydra, aircrack-ng
- 🟡 **Medium Risk:** sqlmap, burpsuite, john
- 🟢 **Low Risk:** nmap, nikto, wireshark

### File Operations
```
"read /path/to/file"          → Display file contents
"list /path"                  → Show directory
"find filename"               → Search for files
"organize my downloads"       → Sort downloads folder
```

### Shell Commands
```
"run whoami"                  → Execute shell command
"check the time"              → Any direct system info
"list running processes"      → ps or tasklist
```

### Browser & Web Automation
```
/web start                    → Start browser for automation
/web goto <url>               → Navigate to any website
/web free-servers             → Find & test free API services
/web signup <service>         → Fill signup forms automatically
/web analyze                  → Extract links, forms, page info
/web stop                     → Close browser
"search for [topic]"          → Web search (if TAVILY_API_KEY set)
"find information on..."      → Web lookup
"download [file] from..."     → Browser automation + download
```

### Document Operations
```
"list my documents"           → Show indexed docs
"find a document with..."     → Search by name/content
"read my [document type]"     → Open & read documents
"document stats"              → Show library summary
```

### Tasks & Autonomy
```
"do task: [description]"      → Plan & execute multi-step task
"autonomy on"                 → Enable autonomous mode
"autonomy tick"               → Run one autonomous step
"autonomy off"                → Disable autonomy
```

### AI Learning & Skills System
```
/learn stats                  → Comprehensive learning system statistics
/learn skills                 → Browse autonomously learned skills
/learn skill <name>           → Detailed skill information and improvements
/learn improve                → Run autonomous skill improvement analysis
/learn memories               → Memory insights and conversation patterns
```

**Real AI Learning Capabilities:**
- **Self-improving skills**: Kai creates and refines skills from task executions
- **Conversation memory**: Stores and analyzes all interactions for learning
- **Success tracking**: Skills improve confidence based on successful executions
- **Pattern recognition**: Identifies effective workflows and techniques
- **Autonomous improvement**: Skills self-optimize based on accumulated data
- **Correlation analysis**: Identifies compound risks and attack paths automatically
- **Autonomous skill creation**: Complex workflows automatically become reusable skills

## Policy & Permissions

Kai respects capability policies:
```
"/policy status"              → Show current mode
"/policy mode power-user"     → Unlock all tools (including dangerous Kali tools)
"/policy mode balanced"       → Moderate capability level (default for pentesting)
"/policy mode guarded"        → Restricted to safe operations
"/capabilities"               → List all available tools
```

**Pentesting Policy Notes:**
- Pentest mode requires explicit target authorization (`/pentest authorize <target>`)
- High-risk tools (metasploit, aircrack) require `power-user` policy
- All findings include correlation analysis and business context scoring
- Reports are automatically generated in HTML format
- WSL Kali integration provides access to 50+ security tools

Computer access is built into Kai's local code through desktop, shell, screen, file, and browser tools. Those actions are available only when the active tool policy allows them.

## Memory & Learning

```
"/remember [text]"            → Save to Kai's long-term memory
"/memory"                     → Show saved memories
"/forget [item]"              → Remove memory
```

## How Natural Language Invocation Works

1. **You ask in natural language**: "wifi scan for nearby networks"
2. **Kai parses intent**: Detects "wifi scan" + "networks"
3. **Kai checks permissions**: Verifies policy allows network scanning
4. **Kai executes**: Runs the appropriate tool
5. **Kai reports**: Delivers results + next steps

## Examples

### Simple Query
```
You: "what time is it?"
Kai: [Direct answer - no Ollama needed]
"It's 3:47 PM. You have a meeting at 4."
```

### System Check
```
You: "is the system healthy?"
Kai: [Scans CPU, memory, network]
"CPU 42%, Memory 68%, Network stable. All good."
```

### Multi-Step Task
```
You: "download the waiver form from medicalrecords.com"
Kai: [Plans steps, opens browser, fills forms, downloads]
"✓ Downloaded to ~/Downloads/medical_waiver_2026.pdf"
```

### Analysis  
```
You: "what's on my desktop right now?"
Kai: [Captures screen, runs OCR, analyzes]
"I see VS Code, a calculator, and your email client."
```

## Troubleshooting

If Kai doesn't respond:
1. Check logs: `tail -f logs/events.jsonl`
2. Verify Ollama is running: `ollama list`
3. Check policy: `/policy status`
4. Try explicit command: `/screen` instead of "what do you see?"

## Emergency Fallbacks

If the model times out, Kai auto-falls back to:
1. Cached responses
2. Simple/direct answers  
3. Web search (if configured)
4. Manual terminal access

---

**Remember**: Natural language is best-effort. For guaranteed execution, use explicit text commands starting with `/`.
