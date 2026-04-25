"""
Correlation and scoring engine integrating ghostscan capabilities into Kai.
Provides intelligent vulnerability prioritization and correlation analysis.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from kai_agent.vulnerability_assessment import Vulnerability


@dataclass
class CorrelatedFinding:
    """Enhanced finding with correlation and scoring"""
    id: str
    title: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    score: float  # 0.0 to 10.0
    confidence: float  # 0.0 to 1.0
    impact: float  # 0.0 to 10.0
    exploitability: str  # pre-auth, auth-required, etc.
    business_context: str
    remediation: str
    evidence: List[str] = field(default_factory=list)
    correlated_findings: List[str] = field(default_factory=list)  # IDs of related findings
    tags: Set[str] = field(default_factory=set)
    cvss_vector: Optional[str] = None
    cve_ids: List[str] = field(default_factory=list)
    affected_assets: List[str] = field(default_factory=list)


class KaiCorrelationEngine:
    """
    Intelligent vulnerability correlation and scoring system.
    Inspired by ghostscan's approach to prioritizing real risks over noise.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.correlation_rules = self._load_correlation_rules()

    def _load_correlation_rules(self) -> Dict:
        """Load correlation rules for compound risk detection"""
        return {
            # Login + SQLi = CRITICAL
            'auth_sqli': {
                'conditions': ['auth_endpoint', 'sqli'],
                'severity_boost': 2,
                'title': 'SQL Injection on Authentication Endpoint',
                'business_context': 'Authentication bypass + database compromise = full system takeover',
                'remediation': 'Use parameterized queries, input validation, WAF rules'
            },

            # API + No Auth = HIGH
            'api_no_auth': {
                'conditions': ['api_endpoint', 'missing_auth'],
                'severity_boost': 1.5,
                'title': 'Unauthenticated API Access',
                'business_context': 'API exposure without authentication = data breach risk',
                'remediation': 'Implement proper authentication, authorization, rate limiting'
            },

            # Database + External Exposure = CRITICAL
            'db_external': {
                'conditions': ['database_port', 'external_access'],
                'severity_boost': 2.5,
                'title': 'Database Server Exposed Externally',
                'business_context': 'Direct database access from internet = immediate compromise',
                'remediation': 'Restrict to VPN, implement firewall rules, use cloud security groups'
            },

            # Secrets + No WAF = CRITICAL
            'secrets_no_waf': {
                'conditions': ['secrets_exposed', 'no_waf'],
                'severity_boost': 2,
                'title': 'Secrets Exposed Without WAF Protection',
                'business_context': 'API keys/tokens exposed without protection = credential theft',
                'remediation': 'Remove exposed secrets, implement WAF, use secret management'
            },

            # Admin Panel + Default Creds = CRITICAL
            'admin_default_creds': {
                'conditions': ['admin_panel', 'default_credentials'],
                'severity_boost': 3,
                'title': 'Admin Panel with Default Credentials',
                'business_context': 'Administrative access with known passwords = instant compromise',
                'remediation': 'Change all default credentials, implement MFA, monitor access'
            },

            # Payment + XSS = CRITICAL
            'payment_xss': {
                'conditions': ['payment_flow', 'xss'],
                'severity_boost': 2.5,
                'title': 'XSS in Payment Flow',
                'business_context': 'JavaScript injection in payment pages = card data theft',
                'remediation': 'Input sanitization, CSP headers, secure coding practices'
            }
        }

    def correlate_findings(self, vulnerabilities: List[Vulnerability]) -> List[CorrelatedFinding]:
        """Correlate and score vulnerabilities using intelligent rules"""

        # First pass: convert to CorrelatedFinding objects
        correlated = []
        for vuln in vulnerabilities:
            finding = self._create_correlated_finding(vuln)
            correlated.append(finding)

        # Second pass: apply correlation rules
        self._apply_correlation_rules(correlated)

        # Third pass: recalculate scores based on correlations
        self._recalculate_scores(correlated)

        # Sort by score (highest first)
        correlated.sort(key=lambda x: x.score, reverse=True)

        return correlated

    def _create_correlated_finding(self, vuln: Vulnerability) -> CorrelatedFinding:
        """Convert Vulnerability to CorrelatedFinding with initial scoring"""
        finding = CorrelatedFinding(
            id=self._generate_finding_id(vuln),
            title=vuln.title,
            severity=vuln.severity,
            score=self._calculate_base_score(vuln),
            confidence=vuln.confidence,
            impact=self._calculate_impact(vuln),
            exploitability=self._determine_exploitability(vuln),
            business_context=self._generate_business_context(vuln),
            remediation=vuln.remediation,
            evidence=[vuln.evidence],
            tags=set(vuln.tags) if vuln.tags else set(),
            cve_ids=[vuln.cve_id] if vuln.cve_id else [],
            affected_assets=[vuln.affected_url] if vuln.affected_url else []
        )

        return finding

    def _generate_finding_id(self, vuln: Vulnerability) -> str:
        """Generate unique finding ID"""
        import hashlib
        content = f"{vuln.title}{vuln.evidence}{vuln.affected_url or ''}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def _calculate_base_score(self, vuln: Vulnerability) -> float:
        """Calculate base CVSS-like score"""
        severity_scores = {
            'CRITICAL': 9.5,
            'HIGH': 7.5,
            'MEDIUM': 5.0,
            'LOW': 3.0,
            'INFO': 1.0
        }

        base_score = severity_scores.get(vuln.severity.upper(), 1.0)

        # Adjust for confidence
        base_score *= vuln.confidence

        # Adjust for specific indicators
        if 'exposed' in vuln.title.lower() or 'missing' in vuln.title.lower():
            base_score *= 0.8  # Slightly reduce for common false positives

        if 'default' in vuln.title.lower() or 'weak' in vuln.title.lower():
            base_score *= 1.2  # Increase for confirmed weaknesses

        return min(10.0, max(0.0, base_score))

    def _calculate_impact(self, vuln: Vulnerability) -> float:
        """Calculate impact score based on vulnerability type"""
        impact_indicators = {
            'data_breach': 9.0,
            'system_takeover': 10.0,
            'credential_theft': 8.5,
            'denial_service': 6.0,
            'information_disclosure': 4.0,
            'privilege_escalation': 8.0,
            'remote_code_execution': 9.5,
        }

        title_lower = vuln.title.lower()
        description_lower = vuln.description.lower()

        for indicator, score in impact_indicators.items():
            if indicator.replace('_', ' ') in title_lower or indicator.replace('_', ' ') in description_lower:
                return score

        # Default impact based on severity
        severity_impacts = {
            'CRITICAL': 9.0,
            'HIGH': 7.0,
            'MEDIUM': 5.0,
            'LOW': 3.0,
            'INFO': 1.0
        }

        return severity_impacts.get(vuln.severity.upper(), 1.0)

    def _determine_exploitability(self, vuln: Vulnerability) -> str:
        """Determine exploitability level"""
        title_lower = vuln.title.lower()
        desc_lower = vuln.description.lower()

        if any(word in title_lower + desc_lower for word in ['default', 'weak', 'exposed', 'missing']):
            return 'easy'

        if 'authentication' in desc_lower or 'auth' in desc_lower:
            return 'requires_auth'

        if 'remote' in desc_lower or 'network' in desc_lower:
            return 'remote'

        if 'local' in desc_lower or 'physical' in desc_lower:
            return 'local_access'

        return 'unknown'

    def _generate_business_context(self, vuln: Vulnerability) -> str:
        """Generate business impact context"""
        contexts = {
            'sql': 'Database compromise = data loss, compliance violations, financial impact',
            'xss': 'Client-side attacks = user session theft, malware delivery, trust erosion',
            'auth': 'Authentication bypass = unauthorized access, data breaches, legal liability',
            'encryption': 'Weak encryption = data interception, privacy violations, regulatory fines',
            'exposure': 'Information exposure = competitive disadvantage, privacy breaches',
            'default': 'Known weaknesses = easy exploitation, automated attacks, rapid compromise',
            'admin': 'Administrative access = full system control, data manipulation, trust breach',
            'payment': 'Financial systems = monetary loss, fraud, customer impact, regulatory scrutiny',
        }

        combined_text = (vuln.title + ' ' + vuln.description).lower()

        for key, context in contexts.items():
            if key in combined_text:
                return context

        return 'Security vulnerability requiring remediation to prevent potential compromise'

    def _apply_correlation_rules(self, findings: List[CorrelatedFinding]) -> None:
        """Apply correlation rules to detect compound risks"""
        finding_tags = {}
        finding_ids = {}

        # Build tag and ID mappings
        for finding in findings:
            for tag in finding.tags:
                if tag not in finding_tags:
                    finding_tags[tag] = []
                finding_tags[tag].append(finding.id)
            finding_ids[finding.id] = finding

        # Apply each correlation rule
        for rule_name, rule in self.correlation_rules.items():
            conditions = rule['conditions']
            matching_findings = set()

            # Find findings that match all conditions
            for condition in conditions:
                if condition in finding_tags:
                    if not matching_findings:
                        matching_findings = set(finding_tags[condition])
                    else:
                        matching_findings = matching_findings.intersection(set(finding_tags[condition]))

            # If we have correlated findings, create compound vulnerability
            if len(matching_findings) >= 2:
                correlated_ids = list(matching_findings)
                primary_finding = finding_ids[correlated_ids[0]]

                # Create correlated finding
                correlated = CorrelatedFinding(
                    id=f"compound_{rule_name}_{len(correlated_ids)}",
                    title=rule['title'],
                    severity='CRITICAL',  # Compound risks are critical
                    score=min(10.0, primary_finding.score * rule['severity_boost']),
                    confidence=min(1.0, primary_finding.confidence * 0.9),  # Slightly reduce confidence for correlation
                    impact=primary_finding.impact,
                    exploitability='high',
                    business_context=rule['business_context'],
                    remediation=rule['remediation'],
                    evidence=[f"Correlated {len(correlated_ids)} related findings"],
                    correlated_findings=correlated_ids,
                    tags={'compound', 'correlated', rule_name}
                )

                # Add to findings list
                findings.append(correlated)

                # Update original findings to reference correlation
                for finding_id in correlated_ids:
                    if finding_id in finding_ids:
                        finding_ids[finding_id].correlated_findings.append(correlated.id)

    def _recalculate_scores(self, findings: List[CorrelatedFinding]) -> None:
        """Recalculate scores based on correlations and context"""
        for finding in findings:
            # Boost score if part of correlation
            if finding.correlated_findings:
                correlation_boost = 1.2  # 20% boost for correlated findings
                finding.score = min(10.0, finding.score * correlation_boost)

            # Context-based adjustments
            context_multipliers = {
                'payment': 1.5,
                'admin': 1.4,
                'database': 1.45,
                'authentication': 1.3,
                'encryption': 1.2,
                'external': 1.25,
                'internet': 1.2,
            }

            combined_text = (finding.title + ' ' + finding.business_context).lower()
            for context, multiplier in context_multipliers.items():
                if context in combined_text:
                    finding.score = min(10.0, finding.score * multiplier)
                    break

    def generate_executive_report(self, findings: List[CorrelatedFinding], target: str) -> Dict:
        """Generate executive summary with key insights"""
        total_findings = len(findings)
        critical_count = sum(1 for f in findings if f.severity == 'CRITICAL')
        high_count = sum(1 for f in findings if f.severity == 'HIGH')

        # Calculate risk score (weighted average)
        if findings:
            weighted_score = sum(f.score * f.confidence for f in findings) / sum(f.confidence for f in findings)
        else:
            weighted_score = 0.0

        # Identify top risks
        top_risks = sorted(findings, key=lambda x: x.score, reverse=True)[:5]

        # Risk distribution
        severity_dist = {}
        for finding in findings:
            severity_dist[finding.severity] = severity_dist.get(finding.severity, 0) + 1

        # Business impact assessment
        business_impacts = {
            'data_breach': any('breach' in f.business_context.lower() for f in findings),
            'financial_loss': any('payment' in f.title.lower() or 'financial' in f.business_context.lower() for f in findings),
            'compliance_violation': any('compliance' in f.business_context.lower() for f in findings),
            'reputation_damage': any('trust' in f.business_context.lower() for f in findings),
        }

        return {
            'target': target,
            'total_findings': total_findings,
            'risk_score': round(weighted_score, 1),
            'severity_distribution': severity_dist,
            'critical_high_count': critical_count + high_count,
            'top_risks': [
                {
                    'title': risk.title,
                    'score': round(risk.score, 1),
                    'severity': risk.severity,
                    'business_context': risk.business_context[:100] + '...' if len(risk.business_context) > 100 else risk.business_context
                }
                for risk in top_risks
            ],
            'business_impacts': {k: v for k, v in business_impacts.items() if v},
            'recommendations': self._generate_recommendations(findings),
            'correlation_insights': self._generate_correlation_insights(findings)
        }

    def _generate_recommendations(self, findings: List[CorrelatedFinding]) -> List[str]:
        """Generate prioritized remediation recommendations"""
        recommendations = []

        # Count issue types
        issue_types = {}
        for finding in findings:
            for tag in finding.tags:
                issue_types[tag] = issue_types.get(tag, 0) + 1

        # Generate recommendations based on issue types
        if issue_types.get('auth', 0) > 0:
            recommendations.append("Implement multi-factor authentication (MFA) across all access points")

        if issue_types.get('encryption', 0) > 0:
            recommendations.append("Upgrade to TLS 1.3 and implement HSTS headers")

        if issue_types.get('exposure', 0) > 0:
            recommendations.append("Restrict unnecessary service exposure and implement network segmentation")

        if issue_types.get('default', 0) > 0:
            recommendations.append("Audit and change all default credentials and configurations")

        if issue_types.get('web', 0) > 0:
            recommendations.append("Implement Web Application Firewall (WAF) and regular security assessments")

        if issue_types.get('database', 0) > 0:
            recommendations.append("Restrict database access to authorized hosts only and encrypt sensitive data")

        # Add general recommendations
        recommendations.extend([
            "Conduct regular automated security scanning and manual penetration testing",
            "Implement security monitoring and alerting for suspicious activities",
            "Develop and maintain an incident response plan",
            "Provide security awareness training for development and operations teams"
        ])

        return recommendations[:10]  # Limit to top 10

    def _generate_correlation_insights(self, findings: List[CorrelatedFinding]) -> List[str]:
        """Generate insights about correlated findings"""
        insights = []

        correlated_findings = [f for f in findings if f.correlated_findings]

        if correlated_findings:
            insights.append(f"Found {len(correlated_findings)} compound risks where multiple vulnerabilities combine for greater impact")

            # Most common correlations
            correlation_types = {}
            for finding in correlated_findings:
                for tag in finding.tags:
                    if 'compound' in tag or 'correlated' in tag:
                        correlation_types[tag] = correlation_types.get(tag, 0) + 1

            if correlation_types:
                top_correlation = max(correlation_types.items(), key=lambda x: x[1])
                insights.append(f"Most common risk pattern: {top_correlation[0].replace('_', ' ').title()} ({top_correlation[1]} instances)")

        # Risk concentration
        high_risk_findings = [f for f in findings if f.score >= 7.0]
        if high_risk_findings:
            insights.append(f"{len(high_risk_findings)} high-risk findings (score ≥7.0) require immediate attention")

        # Low-hanging fruit
        easy_fixes = [f for f in findings if f.exploitability == 'easy' and f.score < 5.0]
        if easy_fixes:
            insights.append(f"{len(easy_fixes)} quick wins available with easy remediation and moderate impact")

        return insights

    def export_findings(self, findings: List[CorrelatedFinding], filepath: Path, format: str = 'json') -> None:
        """Export findings in various formats"""
        if format == 'json':
            data = {
                'findings': [
                    {
                        'id': f.id,
                        'title': f.title,
                        'severity': f.severity,
                        'score': round(f.score, 2),
                        'confidence': round(f.confidence, 2),
                        'impact': round(f.impact, 2),
                        'exploitability': f.exploitability,
                        'business_context': f.business_context,
                        'remediation': f.remediation,
                        'evidence': f.evidence,
                        'correlated_findings': f.correlated_findings,
                        'tags': list(f.tags),
                        'cve_ids': f.cve_ids,
                        'affected_assets': f.affected_assets,
                    }
                    for f in findings
                ],
                'summary': self.generate_executive_report(findings, 'export_target')
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format == 'csv':
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Title', 'Severity', 'Score', 'Confidence', 'Impact', 'Exploitability', 'Business Context', 'Remediation', 'Tags'])

                for finding in findings:
                    writer.writerow([
                        finding.id,
                        finding.title,
                        finding.severity,
                        round(finding.score, 2),
                        round(finding.confidence, 2),
                        round(finding.impact, 2),
                        finding.exploitability,
                        finding.business_context,
                        finding.remediation,
                        ','.join(finding.tags)
                    ])

        print("[+] Exported {} findings to {}".format(len(findings), filepath))
