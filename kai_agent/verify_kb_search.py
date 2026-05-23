"""Verify KB search returns results across categories."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from kai_agent.knowledge_base import KnowledgeBase

kb = KnowledgeBase(Path(__file__).parent / "memory" / "knowledge_base")
stats = kb.stats()
print(f"Total entries: {stats['total_entries']}")
print()

all_pass = True
for query, label in [
    ("camera rtsp shodan stream", "Camera Check"),
    ("phishing email clone setoolkit evilginx", "Phishing"),
    ("kerberos golden ticket domain admin", "Golden Ticket"),
    ("hashcat john password cracking gpu", "Password Cracking"),
    ("aws s3 bucket cloud leak", "Cloud Bucket"),
    ("privilege escalation linux kernel exploit", "Linux Privesc"),
    ("docker container escape", "Container Escape"),
    ("nuclei vulnerability scan template", "Mass Vuln Scan"),
    ("malicious macro office payload hta", "Macro/HTA"),
    ("sql injection sqlmap database exploit", "SQLi"),
    ("xss cross site scripting steal cookies", "XSS"),
    ("ssh lateral movement pivot network", "Lateral Movement"),
]:
    results = kb.search(query, top_n=1)
    if results:
        r = results[0]
        print(f"  OK  {label}: \"{r['input'][:55]}\" score={r.get('_score', '?')}")
    else:
        print(f"  FAIL {label}: NO RESULTS")
        all_pass = False

print()
print("ALL PASS" if all_pass else "SOME FAILED")
