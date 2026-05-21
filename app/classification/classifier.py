import re
from dataclasses import dataclass, field


@dataclass
class JobClassification:
    function: str
    seniority: str
    seniority_track: str
    geography: str
    domain_tags: list[str] = field(default_factory=list)


_FUNCTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Eng", re.compile(r"\b(engineer|developer|swe|sre|devops|platform|infrastructure|backend|frontend|full.?stack)\b", re.IGNORECASE)),
    ("Data", re.compile(r"\b(data.scientist|data.engineer|data.analyst|analytics|machine.learning|ml.engineer)\b", re.IGNORECASE)),
    ("Product", re.compile(r"\b(product.manager|product.owner|product.lead)\b", re.IGNORECASE)),
    ("Design", re.compile(r"\b(design|ux|ui)\b", re.IGNORECASE)),
    ("Sales", re.compile(r"\b(sales|account.executive|business.development|bdr|sdr|revenue)\b", re.IGNORECASE)),
    ("Clinical", re.compile(r"\b(clinical|nurse|physician|md\b|rn\b|pharmacist|medical.director)\b", re.IGNORECASE)),
    ("Compliance", re.compile(r"\b(compliance|regulatory|legal|counsel|privacy)\b", re.IGNORECASE)),
    ("Ops", re.compile(r"\b(operations|office.manager|people.ops|recruiting|talent|hr\b)\b", re.IGNORECASE)),
]

# Ordered highest to lowest priority
_SENIORITY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("C-Suite", re.compile(r"\b(chief|cto|cfo|ceo|coo|cmo)\b", re.IGNORECASE)),
    ("VP", re.compile(r"\b(vp|vice.president)\b", re.IGNORECASE)),
    ("Director", re.compile(r"\b(director)\b", re.IGNORECASE)),
    ("Manager", re.compile(r"\b(manager|managing)\b", re.IGNORECASE)),
    ("Principal", re.compile(r"\b(principal|distinguished|fellow)\b", re.IGNORECASE)),
    ("Staff", re.compile(r"\b(staff)\b", re.IGNORECASE)),
    ("Senior", re.compile(r"\b(senior|sr\.?)\b", re.IGNORECASE)),
    ("Junior", re.compile(r"\b(junior|jr\.?|entry.level|associate|intern)\b", re.IGNORECASE)),
]

_MGMT_LEVELS = {"Manager", "Director", "VP", "C-Suite"}

_GEOGRAPHY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Remote", re.compile(r"\b(remote|anywhere|distributed)\b", re.IGNORECASE)),
    ("US-West", re.compile(r"\b(san.francisco|sf\b|los.angeles|seattle|denver|california|ca\b|wa\b)\b", re.IGNORECASE)),
    ("US-East", re.compile(r"\b(new.york|nyc|boston|washington|dc\b|virginia|ma\b|ny\b)\b", re.IGNORECASE)),
    ("US-Central", re.compile(r"\b(chicago|austin|dallas|houston|nashville|tx\b|il\b)\b", re.IGNORECASE)),
]

_DOMAIN_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("payer", re.compile(r"\b(payer|payor|health.plan|insurance)\b", re.IGNORECASE)),
    ("prior_auth", re.compile(r"\b(prior.auth|pre.auth|utilization.management)\b", re.IGNORECASE)),
    ("rcm", re.compile(r"\b(revenue.cycle|rcm|billing|claims|coding)\b", re.IGNORECASE)),
    ("voice", re.compile(r"\b(voice|telephony|ivr|call.center|contact.center)\b", re.IGNORECASE)),
    ("browser_automation", re.compile(r"\b(browser.automation|rpa|robotic.process|selenium|playwright)\b", re.IGNORECASE)),
    ("ehr", re.compile(r"\b(ehr|emr|electronic.health|electronic.medical)\b", re.IGNORECASE)),
    ("epic", re.compile(r"\b(epic\b|epic.systems)\b", re.IGNORECASE)),
    ("fhir", re.compile(r"\b(fhir|hl7|interoperability)\b", re.IGNORECASE)),
    ("soc2", re.compile(r"\b(soc.?2)\b", re.IGNORECASE)),
    ("hipaa", re.compile(r"\b(hipaa|phi\b|protected.health)\b", re.IGNORECASE)),
]


def classify_job(title: str, description: str, location: str | None) -> JobClassification:
    title_and_desc = f"{title} {description}".lower()
    title_lower = title.lower()
    location_text = (location or "").lower()

    # Function: first match wins against title + description
    function = "Other"
    for func_name, pattern in _FUNCTION_PATTERNS:
        if pattern.search(title_and_desc):
            function = func_name
            break

    # Seniority: highest match wins against title only
    seniority = "Mid"
    for level, pattern in _SENIORITY_PATTERNS:
        if pattern.search(title_lower):
            seniority = level
            break

    seniority_track = "Mgmt" if seniority in _MGMT_LEVELS else "IC"

    # Geography: first match wins against location
    geography = "Other"
    for geo_name, pattern in _GEOGRAPHY_PATTERNS:
        if pattern.search(location_text):
            geography = geo_name
            break

    # Domain: collect all matches against description
    domain_tags = []
    for tag, pattern in _DOMAIN_PATTERNS:
        if pattern.search(description.lower()):
            domain_tags.append(tag)

    return JobClassification(
        function=function,
        seniority=seniority,
        seniority_track=seniority_track,
        geography=geography,
        domain_tags=domain_tags,
    )
