# Demo Script: AI Jarvis-style Flows (MCP Hunt + Chess Buddy)

Goal: Sanity-check the safe MCP Hunt flow and Chess Buddy flow in a film-friendly, minimal demo.

Scene 1: Setup
- Host explains the setup: Kai runs a safe, autonomous MCP hunt in a lab environment.
- Show repo layout: kai_agent/mcp_lab, kai_agent/chess_companion, kai_agent/assistant.py.

Scene 2: Trigger MCP Hunt
- Host types or shows: hunt lab_topology
- On-screen: capture agent labels in the log:
  - ReconSim: …
  - PortScanSim: …
  - ReportAgent: …
- Screen shows final report output (text or HTML).
- Narration: Explain that multiple agents run in parallel and summarize findings in a single report.

Scene 3: Chess Buddy Flow
- Show board (camera or screenshot).
- Host types: watch chess
- On-screen: Move suggestion by AI, narration of rationale (friendly tone).
- Screen show: before/after board or FEN updates.

Scene 4: Takeaways
- Side-by-side: MCP Hunt vs Chess Buddy.
- Narration: Emphasize safe, parallel AI work and human-friendly narration.

Appendix: Commands Used
- Hunt MCP: hunt lab_topology
- Chess Buddy: watch chess
- Optional: watch chess <fen-or-source>

Notes for production
- Use a safe lab target; no real systems touched.
- Provide on-screen captions for agent names and key results.
- Record a short host voiceover to explain what happens during each scene.
