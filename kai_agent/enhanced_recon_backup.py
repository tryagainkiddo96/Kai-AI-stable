"""
Enhanced reconnaissance module integrating ghost_eye capabilities into Kai.
Provides comprehensive information gathering and reconnaissance tools.
"""

import asyncio
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class ReconResult:
    """Structured reconnaissance result"""
    target: str
    timestamp: str
    dns_records: Dict[str, List[str]]
    whois_info: Optional[Dict] = None
    ip_location: Optional[Dict] = None
    http_headers: Optional[Dict] = None
    cms_detection: Optional[str] = None
    traceroute: Optional[List[str]] = None
    certificate_info: Optional[Dict] = None
    robots_txt: Optional[str] = None
    links_found: Optional[List[str]] = None


class KaiReconnaissance:
    """
    Enhanced reconnaissance module with ghost_eye-inspired capabilities.
    Provides comprehensive information gathering for security assessments.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.results_dir = workspace / "recon_results"
        self.results_dir.mkdir(exist_ok=True)

    def dns_lookup(self, target: str) -> Dict[str, List[str]]:
        """Perform comprehensive DNS enumeration"""
        records = {}

        # Clean target (remove protocol if present)
        clean_target = target.replace('http://', '').replace('https://', '').split('/')[0]

        record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'SOA', 'CNAME']

        for record_type in record_types:
            try:
                # Use nslookup for Windows compatibility
                result = subprocess.run(
                    ['nslookup', '-type=' + record_type, clean_target],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )

                if result.returncode == 0 and result.stdout.strip():
                    # Parse nslookup output
                    lines = result.stdout.split('\n')
                    record_data = []
                    in_records = False

                    for line in lines:
                        line = line.strip()
                        if f'{record_type} record' in line.lower() or f'{record_type}:' in line.lower():
                            in_records = True
                            continue
                        elif in_records and line and not line.startswith('>') and not line.startswith('Server:'):
                            # Extract the actual record data
                            if record_type == 'A' and re.match(r'\d+\.\d+\.\d+\.\d+', line):
                                record_data.append(line)
                            elif record_type == 'AAAA' and ':' in line and len(line.split(':')) >= 3:
                                record_data.append(line)
                            elif record_type in ['MX', 'NS', 'TXT', 'SOA', 'CNAME']:
                                if len(line) > 2 and not line.startswith(' '):
                                    record_data.append(line)

                    if record_data:
                        records[record_type] = record_data[:10]  # Limit results

            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                continue

        return records

    def whois_lookup(self, target: str) -> Optional[Dict]:
        """Perform WHOIS lookup with enhanced error handling"""
        if not WHOIS_AVAILABLE:
            return None

        try:
            clean_target = target.replace('http://', '').replace('https://', '').split('/')[0]
            w = whois.whois(clean_target)

            return {
                'domain_name': str(w.domain_name) if w.domain_name else None,
                'registrar': str(w.registrar) if w.registrar else None,
                'creation_date': str(w.creation_date) if w.creation_date else None,
                'expiration_date': str(w.expiration_date) if w.expiration_date else None,
                'updated_date': str(w.updated_date) if w.updated_date else None,
                'name_servers': str(w.name_servers) if w.name_servers else None,
                'status': str(w.status) if w.status else None,
                'emails': str(w.emails) if w.emails else None,
            }
        except Exception as e:
            return {'error': f'WHOIS lookup failed: {str(e)}'}

    def ip_location_finder(self, ip: str) -> Optional[Dict]:
        """Find IP geolocation information"""
        if not REQUESTS_AVAILABLE:
            return None

        try:
            # Use ipapi.co for free IP geolocation
            response = requests.get(f'http://ipapi.co/{ip}/json/', timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'ip': data.get('ip'),
                    'city': data.get('city'),
                    'region': data.get('region'),
                    'country': data.get('country_name'),
                    'country_code': data.get('country_code'),
                    'postal': data.get('postal'),
                    'latitude': data.get('latitude'),
                    'longitude': data.get('longitude'),
                    'timezone': data.get('timezone'),
                    'org': data.get('org'),
                    'asn': data.get('asn'),
                }
        except Exception:
            pass

        return None

    def http_header_grabber(self, url: str) -> Optional[Dict]:
        """Grab HTTP headers from target URL"""
        if not REQUESTS_AVAILABLE:
            return None

        try:
            # Add http:// if no protocol specified
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url

            response = requests.head(url, timeout=10, allow_redirects=True)
            return dict(response.headers)
        except Exception:
            return None

    def cms_detection(self, url: str) -> Optional[str]:
        """Detect Content Management System"""
        if not REQUESTS_AVAILABLE:
            return None

        try:
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url

            response = requests.get(url, timeout=10)

            # Check for common CMS signatures
            content = response.text.lower()

            cms_signatures = {
                'WordPress': ['wp-content', 'wp-includes', 'wordpress'],
                'Joomla': ['joomla', 'com_content', 'mod_menu'],
                'Drupal': ['drupal', 'sites/all', 'node/'],
                'Magento': ['mage', 'var/cache', 'skin/frontend'],
                'Shopify': ['cdn.shopify.com', 'shopify'],
                'Squarespace': ['squarespace', 'static.squarespace'],
                'Wix': ['wix.com', 'wixstatic.com'],
            }

            for cms, signatures in cms_signatures.items():
                if any(sig in content for sig in signatures):
                    return cms

            # Check headers
            server = response.headers.get('server', '').lower()
            if 'apache' in server:
                return 'Apache (unknown CMS)'
            elif 'nginx' in server:
                return 'Nginx (unknown CMS)'
            elif 'iis' in server:
                return 'IIS (unknown CMS)'

        except Exception:
            pass

        return 'Unknown'

    def traceroute(self, target: str) -> Optional[List[str]]:
        """Perform traceroute to target"""
        try:
            clean_target = target.replace('http://', '').replace('https://', '').split('/')[0]

            # Use tracert on Windows
            result = subprocess.run(
                ['tracert', '-d', clean_target],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                hops = []
                for line in lines:
                    if re.match(r'\s*\d+\s+', line):  # Lines starting with hop number
                        parts = line.split()
                        if len(parts) >= 3:
                            hop_num = parts[0].strip()
                            ip = parts[1].strip()
                            timing = ' '.join(parts[2:]) if len(parts) > 2 else ''
                            hops.append(f"{hop_num}: {ip} ({timing})")
                return hops[:20]  # Limit to 20 hops

        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

        return None

    def certificate_transparency(self, domain: str) -> Optional[Dict]:
        """Check certificate transparency logs"""
        if not REQUESTS_AVAILABLE:
            return None

        try:
            clean_domain = domain.replace('http://', '').replace('https://', '').split('/')[0]
            url = f"https://crt.sh/?q=%.{clean_domain}&output=json"

            response = requests.get(url, timeout=15, headers={'User-Agent': 'Kai-Recon/1.0'})
            if response.status_code == 200:
                data = response.json()
                certs = []
                for cert in data[:10]:  # Limit to 10 certificates
                    certs.append({
                        'name': cert.get('name_value', ''),
                        'issuer': cert.get('issuer_name', ''),
                        'not_before': cert.get('not_before', ''),
                        'not_after': cert.get('not_after', ''),
                    })

                return {
                    'domain': clean_domain,
                    'certificates_found': len(certs),
                    'certificates': certs,
                }

        except Exception:
            pass

        return None

    def robots_txt_scanner(self, url: str) -> Optional[str]:
        """Fetch and analyze robots.txt"""
        if not REQUESTS_AVAILABLE:
            return None

        try:
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url

            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                return response.text

        except Exception:
            pass

        return None

    def link_grabber(self, url: str) -> Optional[List[str]]:
        """Extract links from webpage"""
        if not REQUESTS_AVAILABLE:
            return None

        try:
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Simple regex-based link extraction
                link_pattern = r'href=["\']([^"\']+)["\']'
                links = re.findall(link_pattern, response.text, re.IGNORECASE)

                # Filter and clean links
                clean_links = []
                for link in links[:50]:  # Limit to 50 links
                    if link and not link.startswith(('javascript:', 'mailto:', '#')):
                        if not link.startswith('http'):
                            parsed = urlparse(url)
                            if link.startswith('/'):
                                link = f"{parsed.scheme}://{parsed.netloc}{link}"
                            else:
                                link = f"{parsed.scheme}://{parsed.netloc}/{link}"
                        clean_links.append(link)

                return list(set(clean_links))  # Remove duplicates

        except Exception:
            pass

        return None

    async def comprehensive_recon(self, target: str) -> ReconResult:
        """Perform comprehensive reconnaissance on target"""
        print(f"[+] Starting comprehensive reconnaissance on: {target}")

        # DNS Lookup
        dns_records = self.dns_lookup(target)
        print(f"[+] DNS enumeration completed - {sum(len(records) for records in dns_records.values())} records found")

        # WHOIS Lookup
        whois_info = self.whois_lookup(target)
        if whois_info and 'error' not in whois_info:
            print("[+] WHOIS lookup completed")
        else:
            print("[-] WHOIS lookup failed or unavailable")

        # IP Location (if we have an IP)
        ip_location = None
        clean_target = target.replace('http://', '').replace('https://', '').split('/')[0]
        if re.match(r'\d+\.\d+\.\d+\.\d+', clean_target):
            ip_location = self.ip_location_finder(clean_target)
            if ip_location:
                print(f"[+] IP geolocation: {ip_location.get('city', 'Unknown')}, {ip_location.get('country', 'Unknown')}")

        # HTTP Headers
        http_headers = self.http_header_grabber(target)
        if http_headers:
            print(f"[+] HTTP headers retrieved - {len(http_headers)} headers")

        # CMS Detection
        cms = self.cms_detection(target)
        if cms and cms != 'Unknown':
            print(f"[+] CMS detected: {cms}")

        # Traceroute
        traceroute_data = self.traceroute(clean_target)
        if traceroute_data:
            print(f"[+] Traceroute completed - {len(traceroute_data)} hops")

        # Certificate Transparency
        cert_info = self.certificate_transparency(clean_target)
        if cert_info:
            print(f"[+] Certificate transparency checked - {cert_info.get('certificates_found', 0)} certificates found")

        # Robots.txt
        robots = self.robots_txt_scanner(target)
        if robots:
            print("[+] robots.txt retrieved")

        # Link extraction
        links = self.link_grabber(target)
        if links:
            print(f"[+] Links extracted - {len(links)} links found")

        result = ReconResult(
            target=target,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            dns_records=dns_records,
            whois_info=whois_info,
            ip_location=ip_location,
            http_headers=http_headers,
            cms_detection=cms,
            traceroute=traceroute_data,
            certificate_info=cert_info,
            robots_txt=robots,
            links_found=links,
        )

        # Save results
        self.save_recon_result(result)

        return result

    def save_recon_result(self, result: ReconResult) -> None:
        """Save reconnaissance results to file"""
        filename = f"recon_{result.target}_{result.timestamp}.json".replace(' ', '_').replace(':', '_')
        filepath = self.results_dir / filename

        data = {
            'target': result.target,
            'timestamp': result.timestamp,
            'dns_records': result.dns_records or {},
            'whois_info': result.whois_info or {},
            'ip_location': result.ip_location or {},
            'http_headers': result.http_headers or {},
            'cms_detection': result.cms_detection or 'Unknown',
            'traceroute': result.traceroute or [],
            'certificate_info': result.certificate_info or {},
            'robots_txt': result.robots_txt or '',
            'links_found': result.links_found or [],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
