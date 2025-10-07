"""
Taxonomy template library for tenant onboarding.

Provides industry-specific category sets that tenants can optionally use
to bootstrap their taxonomy instead of hardcoded defaults.
"""

from typing import Dict, List, TypedDict


class TaxonomyEntryTemplate(TypedDict):
    """Template for a single taxonomy entry."""
    key: str
    label: str
    synonyms: List[str]
    regex: List[str]  # Regex patterns for query routing
    description: str


# Template definitions
SOFTWARE_TEMPLATE: List[TaxonomyEntryTemplate] = [
    {
        "key": "documentation",
        "label": "Technical Documentation",
        "synonyms": ["docs", "api", "reference", "guide", "manual"],
        "regex": [r"\bdocs?\b", r"\bapi\b", r"\breference\b", r"\bguides?\b", r"\bmanuals?\b", r"\bdocumentation\b"],
        "description": "API docs, technical guides, and reference materials"
    },
    {
        "key": "tutorial",
        "label": "Tutorials & How-Tos",
        "synonyms": ["how-to", "guide", "walkthrough", "example"],
        "regex": [r"\btutorials?\b", r"\bhow-to\b", r"\bhow to\b", r"\bwalkthroughs?\b", r"\bexamples?\b"],
        "description": "Step-by-step tutorials and learning resources"
    },
    {
        "key": "code",
        "label": "Source Code",
        "synonyms": ["implementation", "snippet", "sample", "library"],
        "regex": [r"\bcode\b", r"\bimplementation\b", r"\bsnippets?\b", r"\bsamples?\b", r"\blibrar(y|ies)\b", r"\bsource\b"],
        "description": "Code samples, libraries, and implementations"
    },
    {
        "key": "changelog",
        "label": "Release Notes",
        "synonyms": ["release", "version", "update", "changelog"],
        "regex": [r"\brelease\b", r"\bversions?\b", r"\bupdates?\b", r"\bchangelogs?\b", r"\brelease notes\b"],
        "description": "Version history and release notes"
    },
]

LEGAL_TEMPLATE: List[TaxonomyEntryTemplate] = [
    {
        "key": "contract",
        "label": "Contracts & Agreements",
        "synonyms": ["agreement", "terms", "msa", "nda"],
        "regex": [r"\bcontracts?\b", r"\bagreements?\b", r"\bterms\b", r"\bmsa\b", r"\bnda\b"],
        "description": "Legal contracts and binding agreements"
    },
    {
        "key": "compliance",
        "label": "Compliance Documents",
        "synonyms": ["policy", "regulation", "compliance", "gdpr"],
        "regex": [r"\bpolic(y|ies)\b", r"\bregulations?\b", r"\bcompliance\b", r"\bgdpr\b", r"\bregulatory\b"],
        "description": "Regulatory compliance and policy documents"
    },
    {
        "key": "case-law",
        "label": "Case Law & Briefs",
        "synonyms": ["precedent", "ruling", "brief", "litigation"],
        "regex": [r"\bcase law\b", r"\bprecedents?\b", r"\brulings?\b", r"\bbriefs?\b", r"\blitigation\b"],
        "description": "Legal precedents and case briefs"
    },
    {
        "key": "memorandum",
        "label": "Legal Memos",
        "synonyms": ["memo", "opinion", "analysis"],
        "regex": [r"\bmemoran(dum|da)\b", r"\bmemos?\b", r"\bopinions?\b", r"\banalys[ie]s\b", r"\blegal memo\b"],
        "description": "Internal legal analyses and memos"
    },
]

MEDICAL_TEMPLATE: List[TaxonomyEntryTemplate] = [
    {
        "key": "clinical-notes",
        "label": "Clinical Notes",
        "synonyms": ["patient", "diagnosis", "treatment", "exam"],
        "regex": [r"\bclinical\b", r"\bpatients?\b", r"\bdiagnos[ie]s\b", r"\btreatments?\b", r"\bexams?\b", r"\bexaminations?\b"],
        "description": "Patient clinical notes and examination records"
    },
    {
        "key": "research",
        "label": "Research & Studies",
        "synonyms": ["study", "trial", "research", "paper"],
        "regex": [r"\bresearch\b", r"\bstud(y|ies)\b", r"\btrials?\b", r"\bpapers?\b", r"\bclinical trial\b"],
        "description": "Medical research papers and clinical trials"
    },
    {
        "key": "protocol",
        "label": "Treatment Protocols",
        "synonyms": ["procedure", "guideline", "standard", "protocol"],
        "regex": [r"\bprotocols?\b", r"\bprocedures?\b", r"\bguidelines?\b", r"\bstandards?\b", r"\btreatment protocol\b"],
        "description": "Standard treatment protocols and procedures"
    },
    {
        "key": "administrative",
        "label": "Administrative",
        "synonyms": ["admin", "billing", "insurance", "scheduling"],
        "regex": [r"\badmin(istrative)?\b", r"\bbilling\b", r"\binsurance\b", r"\bscheduling\b", r"\boperational\b"],
        "description": "Administrative and operational documents"
    },
]

MARKETING_TEMPLATE: List[TaxonomyEntryTemplate] = [
    {
        "key": "campaign",
        "label": "Campaign Materials",
        "synonyms": ["campaign", "ad", "promotion", "marketing"],
        "regex": [r"\bcampaigns?\b", r"\bads?\b", r"\badvertis(ing|ement)s?\b", r"\bpromotions?\b", r"\bmarketing\b"],
        "description": "Marketing campaigns and promotional materials"
    },
    {
        "key": "content",
        "label": "Content Marketing",
        "synonyms": ["blog", "article", "whitepaper", "ebook"],
        "regex": [r"\bcontent\b", r"\bblogs?\b", r"\barticles?\b", r"\bwhitepapers?\b", r"\be-?books?\b"],
        "description": "Blog posts, articles, and educational content"
    },
    {
        "key": "brand",
        "label": "Brand Assets",
        "synonyms": ["logo", "brand", "guidelines", "identity"],
        "regex": [r"\bbrand(ing)?\b", r"\blogos?\b", r"\bguidelines?\b", r"\bidentit(y|ies)\b", r"\bvisual\b"],
        "description": "Brand guidelines and visual assets"
    },
    {
        "key": "analytics",
        "label": "Analytics & Reports",
        "synonyms": ["report", "metrics", "analytics", "performance"],
        "regex": [r"\banalytics?\b", r"\breports?\b", r"\bmetrics?\b", r"\bperformance\b", r"\bkpi\b", r"\bdata\b"],
        "description": "Marketing analytics and performance reports"
    },
]

# Empty template for custom start
EMPTY_TEMPLATE: List[TaxonomyEntryTemplate] = []

# Template registry
TEMPLATES: Dict[str, List[TaxonomyEntryTemplate]] = {
    "software": SOFTWARE_TEMPLATE,
    "legal": LEGAL_TEMPLATE,
    "medical": MEDICAL_TEMPLATE,
    "marketing": MARKETING_TEMPLATE,
    "empty": EMPTY_TEMPLATE,
}


def get_template(template_key: str) -> List[TaxonomyEntryTemplate]:
    """
    Get a taxonomy template by key.

    Args:
        template_key: Template identifier (software, legal, medical, marketing, empty)

    Returns:
        List of taxonomy entry templates

    Raises:
        KeyError: If template_key is not found
    """
    if template_key not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise KeyError(f"Template '{template_key}' not found. Available: {available}")

    return TEMPLATES[template_key]


def list_templates() -> Dict[str, Dict[str, str]]:
    """
    List all available templates with metadata.

    Returns:
        Dictionary mapping template keys to metadata
    """
    return {
        "software": {
            "name": "Software Documentation",
            "description": "For tech companies, developer tools, and SaaS products",
            "category_count": len(SOFTWARE_TEMPLATE),
        },
        "legal": {
            "name": "Legal Documents",
            "description": "For law firms and legal departments",
            "category_count": len(LEGAL_TEMPLATE),
        },
        "medical": {
            "name": "Medical & Healthcare",
            "description": "For hospitals, clinics, and healthcare providers",
            "category_count": len(MEDICAL_TEMPLATE),
        },
        "marketing": {
            "name": "Marketing & Content",
            "description": "For marketing teams and content creators",
            "category_count": len(MARKETING_TEMPLATE),
        },
        "empty": {
            "name": "Start from Scratch",
            "description": "Begin with an empty taxonomy (advanced users)",
            "category_count": 0,
        },
    }
