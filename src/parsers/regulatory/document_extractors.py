"""
Regulatory Document Metadata Extractors
Author: Pura Vida Sloth Intelligence System

Regex-based utilities to extract structured metadata from Federal Register markdown documents.
"""

import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


def parse_federal_register_header(content: str) -> Dict[str, Any]:
    """
    Extract Federal Register volume, issue, date from header.

    Example header:
    "Federal Register/Vol. 89, No. 215/Wednesday, November 6, 2024/Notices"

    Returns:
        Dict with volume, issue, date, section
    """
    pattern = r"Federal Register/Vol\.\s*(\d+),\s*No\.\s*(\d+)/([^/]+)/(.+)"
    match = re.search(pattern, content[:500])  # Search first 500 chars

    if match:
        volume = match.group(1)
        issue = match.group(2)
        date_str = match.group(3).strip()  # e.g., "Wednesday, November 6, 2024"
        section = match.group(4).strip()    # e.g., "Notices"

        # Parse date string
        try:
            # Remove day name if present
            if ',' in date_str:
                parts = date_str.split(',', 1)
                if len(parts) > 1:
                    date_str = parts[1].strip()

            # Parse date
            parsed_date = datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
        except:
            parsed_date = None

        return {
            "federal_register_volume": volume,
            "federal_register_issue": issue,
            "published_at": parsed_date,
            "section": section
        }

    return {
        "federal_register_volume": None,
        "federal_register_issue": None,
        "published_at": None,
        "section": None
    }


def extract_agency_info(content: str) -> Dict[str, str]:
    """
    Extract regulatory_body and sub_agency from document headers.

    Example:
    DEPARTMENT OF TRANSPORTATION
    Federal Aviation Administration

    Returns:
        Dict with regulatory_body, sub_agency
    """
    # Extract department
    dept_pattern = r"DEPARTMENT OF (.+?)(?:\n|$)"
    dept_match = re.search(dept_pattern, content[:2000])
    department = dept_match.group(1).strip() if dept_match else None

    # Extract agency name (usually follows DEPARTMENT or is in **AGENCY:** field)
    agency_pattern = r"\*\*AGENCY:\*\*\s+([^(\n]+)"
    agency_match = re.search(agency_pattern, content[:3000])

    if agency_match:
        agency_full = agency_match.group(1).strip()

        # Parse agency name (may include abbreviation in parentheses)
        # Example: "Federal Aviation Administration (FAA)"
        if '(' in agency_full:
            regulatory_body = agency_full.split('(')[0].strip()
            abbrev = re.search(r'\(([^)]+)\)', agency_full)
            regulatory_body_abbrev = abbrev.group(1) if abbrev else regulatory_body
        else:
            regulatory_body = agency_full
            regulatory_body_abbrev = agency_full
    else:
        # Fallback: Try to extract from lines after DEPARTMENT
        if dept_match:
            lines_after_dept = content[dept_match.end():dept_match.end()+500].split('\n')
            for line in lines_after_dept[:5]:
                line = line.strip().replace('*', '')
                if line and not line.startswith('['): # Skip docket lines
                    regulatory_body = line
                    regulatory_body_abbrev = line
                    break
            else:
                regulatory_body = department
                regulatory_body_abbrev = department
        else:
            regulatory_body = None
            regulatory_body_abbrev = None

    # Extract sub-agency (if present, usually second line or in specific pattern)
    sub_agency = None
    if dept_match and agency_match:
        # Look for sub-agency between department and main agency
        between_text = content[dept_match.end():agency_match.start()]
        lines = [l.strip().replace('*', '') for l in between_text.split('\n') if l.strip()]

        for line in lines:
            if line and not line.startswith('[') and line != regulatory_body:
                sub_agency = line
                break

    # Map common agency names to abbreviations
    agency_abbrev_map = {
        "Federal Aviation Administration": "FAA",
        "Environmental Protection Agency": "EPA",
        "National Aeronautics and Space Administration": "NASA",
        "Federal Communications Commission": "FCC",
        "Department of Defense": "DoD",
        "Department of Transportation": "DOT"
    }

    if regulatory_body in agency_abbrev_map:
        regulatory_body_abbrev = agency_abbrev_map[regulatory_body]

    return {
        "regulatory_body": regulatory_body_abbrev or regulatory_body,
        "sub_agency": sub_agency
    }


def extract_docket_number(content: str) -> Optional[str]:
    """
    Extract docket number from header.

    Examples:
    [Docket No. FAA-2024-1988]
    [Docket ID EPA-HQ-OAR-2024-0001]

    Returns:
        Docket number string or None
    """
    pattern = r"\[Docket (?:No\.|ID)[:=]?\s*([^\]]+)\]"
    match = re.search(pattern, content[:2000])

    if match:
        return match.group(1).strip()

    return None


def extract_document_type_and_action(content: str) -> Dict[str, str]:
    """
    Extract document_type and ACTION field text.

    ACTION examples:
    - "Notice and request for comments"
    - "Proposed rule"
    - "Final rule"
    - "Notice of availability"

    Returns:
        Dict with document_type, action_text
    """
    action_pattern = r"\*\*ACTION:\*\*\s+(.+?)(?=\n\n|\*\*SUMMARY)"
    match = re.search(action_pattern, content[:5000], re.DOTALL)

    action_text = match.group(1).strip() if match else ""

    # Map ACTION text to document_type
    action_lower = action_text.lower()

    if "final rule" in action_lower:
        document_type = "final_rule"
    elif "proposed rule" in action_lower or "notice of proposed" in action_lower:
        document_type = "proposed_rule"
    elif "guidance" in action_lower:
        document_type = "guidance"
    else:
        document_type = "notice"  # Default

    return {
        "document_type": document_type,
        "action_text": action_text
    }


def compute_decision_type(action_text: str, content: str) -> str:
    """
    Determine decision_type from ACTION field and content.

    Types: approval, denial, proposal, certification_requirement

    Returns:
        decision_type string
    """
    action_lower = action_text.lower()
    content_lower = content[:5000].lower()

    # Check for keywords in ACTION field
    if "approval" in action_lower or "approved" in action_lower:
        return "approval"
    elif "denial" in action_lower or "denied" in action_lower or "disapproval" in action_lower:
        return "denial"
    elif ("certification" in action_lower or "requirement" in action_lower or
          "certification" in content_lower[:3000]):
        return "certification_requirement"
    elif "proposed" in action_lower or "proposal" in action_lower:
        return "proposal"
    else:
        # Default to proposal for most notices
        return "proposal"


def extract_dates_section(content: str) -> Dict[str, Optional[str]]:
    """
    Extract dates from DATES section.

    Looks for:
    - effective_date (when regulation takes effect)
    - comment_deadline (when comments are due)

    Returns:
        Dict with effective_date, comment_deadline
    """
    # Find DATES section
    dates_pattern = r"\*\*DATES:\*\*\s+(.+?)(?=\n\n\*\*|\n\n[A-Z])"
    match = re.search(dates_pattern, content[:10000], re.DOTALL)

    if not match:
        return {"effective_date": None, "comment_deadline": None}

    dates_text = match.group(1)

    # Extract effective date
    effective_date = None
    effective_patterns = [
        r"effective\s+(?:on\s+)?([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
        r"effective\s+date[:\s]+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
        r"becomes?\s+effective\s+(?:on\s+)?([A-Z][a-z]+\s+\d{1,2},\s+\d{4})"
    ]

    for pattern in effective_patterns:
        match = re.search(pattern, dates_text, re.IGNORECASE)
        if match:
            try:
                date_str = match.group(1)
                effective_date = datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
                break
            except:
                pass

    # Extract comment deadline
    comment_deadline = None
    comment_patterns = [
        r"comments?\s+(?:must be received|due|should be submitted)\s+(?:by\s+)?([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
        r"(?:on or )?before\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})"
    ]

    for pattern in comment_patterns:
        match = re.search(pattern, dates_text, re.IGNORECASE)
        if match:
            try:
                date_str = match.group(1)
                comment_deadline = datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
                break
            except:
                pass

    return {
        "effective_date": effective_date,
        "comment_deadline": comment_deadline
    }


def extract_contact_email(content: str) -> Optional[str]:
    """
    Extract contact email from FOR FURTHER INFORMATION CONTACT section.

    Returns:
        Email address or None
    """
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    # Look in FURTHER INFORMATION section first
    info_pattern = r"\*\*FOR FURTHER INFORMATION CONTACT:\*\*(.+?)(?=\n\n\*\*|\n\n[A-Z])"
    info_match = re.search(info_pattern, content[:10000], re.DOTALL)

    if info_match:
        info_text = info_match.group(1)
        email_match = re.search(email_pattern, info_text)
        if email_match:
            return email_match.group(0)

    # Fallback: Search entire first 10K chars
    email_match = re.search(email_pattern, content[:10000])
    if email_match:
        return email_match.group(0)

    return None


def extract_fr_doc_from_filename(filename: str) -> Optional[str]:
    """
    Extract Federal Register document ID from filename.

    Example: "federal-aviation-administration_2024-25812.md" → "2024-25812"

    Returns:
        FR Doc number or None
    """
    pattern = r"_(\d{4}-\d+)\.md$"
    match = re.search(pattern, filename)

    if match:
        return match.group(1)

    return None


def extract_all_metadata(content: str, filename: str) -> Dict[str, Any]:
    """
    Extract all metadata from regulatory document.

    Args:
        content: Full markdown content
        filename: Document filename

    Returns:
        Dict with all extracted metadata fields
    """
    # Extract FR header info
    fr_header = parse_federal_register_header(content)

    # Extract agency info
    agency_info = extract_agency_info(content)

    # Extract docket number
    docket_number = extract_docket_number(content)

    # Extract document type and action
    doc_type_info = extract_document_type_and_action(content)

    # Compute decision type
    decision_type = compute_decision_type(doc_type_info["action_text"], content)

    # Extract dates
    dates = extract_dates_section(content)

    # Extract contact email
    contact_email = extract_contact_email(content)

    # Extract FR doc number from filename
    fr_doc_id = extract_fr_doc_from_filename(filename)

    # Combine all metadata
    metadata = {
        **fr_header,
        **agency_info,
        "docket_number": docket_number,
        **doc_type_info,
        "decision_type": decision_type,
        **dates,
        "contact_email": contact_email,
        "federal_register_doc_id": fr_doc_id
    }

    return metadata


def chunk_text(text: str, chunk_size: int = 5000) -> list[str]:
    """
    Split text into chunks for LLM processing.

    Args:
        text: Full text content
        chunk_size: Maximum characters per chunk

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at paragraph boundary
        if end < len(text):
            # Look for double newline
            paragraph_break = text.rfind('\n\n', start, end)
            if paragraph_break > start:
                end = paragraph_break

        chunks.append(text[start:end])
        start = end

    return chunks
