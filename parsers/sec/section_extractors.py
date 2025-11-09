"""
SEC Filing Section Extractors

Extracts relevant sections from different SEC filing types (10-K, 10-Q, 8-K, S-1).
Handles both XBRL/HTML formatted filings and plain text filings.
"""

import re
from typing import Dict, List, Tuple, Optional
from html.parser import HTMLParser
import html


class MLStripper(HTMLParser):
    """Simple HTML tag stripper."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return ''.join(self.text)


def strip_html_tags(text: str) -> str:
    """Remove HTML/XML tags from text."""
    s = MLStripper()
    try:
        s.feed(text)
        return s.get_data()
    except Exception:
        # Fallback: use regex
        text = re.sub(r'<[^>]+>', '', text)
        return html.unescape(text)


def parse_sec_header(content: str) -> Dict[str, any]:
    """
    Parse SEC-HEADER section to extract structured metadata.

    Returns dict with:
    - accession_number
    - filing_type
    - filing_date
    - report_period
    - cik
    - company_name
    - fiscal_year_end
    - sic_code
    - sic_description
    - state_of_incorporation
    - ein
    """
    metadata = {}

    # Extract SEC-HEADER section
    header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', content, re.DOTALL)
    if not header_match:
        return metadata

    header = header_match.group(1)

    # Extract fields with regex
    patterns = {
        'accession_number': r'ACCESSION NUMBER:\s*([0-9-]+)',
        'filing_type': r'CONFORMED SUBMISSION TYPE:\s*(.+)',
        'report_period': r'CONFORMED PERIOD OF REPORT:\s*(\d{8})',
        'filing_date': r'FILED AS OF DATE:\s*(\d{8})',
        'cik': r'CENTRAL INDEX KEY:\s*(\d+)',
        'company_name': r'COMPANY CONFORMED NAME:\s*(.+)',
        'fiscal_year_end': r'FISCAL YEAR END:\s*(\d{4})',
        'sic_code': r'STANDARD INDUSTRIAL CLASSIFICATION:\s*[^\[]*\[(\d+)\]',
        'sic_description': r'STANDARD INDUSTRIAL CLASSIFICATION:\s*([^\[]+)',
        'state_of_incorporation': r'STATE OF INCORPORATION:\s*(\w+)',
        'ein': r'IRS NUMBER:\s*(\d+)',
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, header)
        if match:
            value = match.group(1).strip()

            # Convert dates from YYYYMMDD to YYYY-MM-DD
            if field in ['report_period', 'filing_date'] and len(value) == 8:
                value = f"{value[:4]}-{value[4:6]}-{value[6:8]}"

            metadata[field] = value

    return metadata


def derive_fiscal_period(report_period: str, fiscal_year_end: str, filing_type: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Derive fiscal_year and fiscal_quarter from report_period.

    Args:
        report_period: Date in YYYY-MM-DD format
        fiscal_year_end: MMDD format (e.g., "1231" for Dec 31)
        filing_type: SEC form type (10-K, 10-Q, etc.)

    Returns:
        (fiscal_year, fiscal_quarter) tuple
    """
    if not report_period:
        return None, None

    # Extract year and month from report_period
    try:
        year, month, day = report_period.split('-')
        year = int(year)
        month = int(month)
    except (ValueError, AttributeError):
        return None, None

    fiscal_year = year
    fiscal_quarter = None

    # For 10-K/10-Q, derive quarter
    if filing_type in ['10-Q', '10-K']:
        # Determine quarter based on month
        quarter_map = {
            (1, 2, 3): 'Q1',
            (4, 5, 6): 'Q2',
            (7, 8, 9): 'Q3',
            (10, 11, 12): 'Q4'
        }

        for months, quarter in quarter_map.items():
            if month in months:
                fiscal_quarter = quarter
                break

        # For 10-K, it's always Q4 (full year)
        if filing_type == '10-K':
            fiscal_quarter = 'Q4'

    return fiscal_year, fiscal_quarter


def extract_document_content(content: str) -> str:
    """
    Extract main document content (everything after SEC-HEADER).
    Strips HTML/XML tags to get plain text.
    """
    # Find end of SEC-HEADER
    header_end = re.search(r'</SEC-HEADER>', content)
    if not header_end:
        return content

    # Get everything after header
    document = content[header_end.end():]

    # Strip HTML/XML tags
    clean_text = strip_html_tags(document)

    # Clean up whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text)
    clean_text = clean_text.strip()

    return clean_text


def chunk_text(text: str, max_tokens: int = 4000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks of approximately max_tokens.

    Args:
        text: Text to chunk
        max_tokens: Approximate max tokens per chunk (rough estimate: 1 token ≈ 4 chars)
        overlap: Number of tokens to overlap between chunks

    Returns:
        List of text chunks
    """
    # Rough estimate: 1 token ≈ 4 characters
    max_chars = max_tokens * 4
    overlap_chars = overlap * 4

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chars

        # If not at the end, try to break at sentence boundary
        if end < len(text):
            # Look for sentence end in last 10% of chunk
            search_start = max(start, end - int(max_chars * 0.1))
            sentence_break = text.rfind('. ', search_start, end)

            if sentence_break > start:
                end = sentence_break + 1

        chunks.append(text[start:end].strip())

        # Move start position with overlap
        start = end - overlap_chars

        if start >= len(text):
            break

    return chunks


def extract_10k_sections(content: str) -> Dict[str, str]:
    """
    Extract key sections from 10-K filing.

    For 10-K filings, we're interested in:
    - Item 1: Business
    - Item 1A: Risk Factors
    - Item 7: Management's Discussion and Analysis

    Due to XBRL complexity, we extract all content and chunk it.
    """
    metadata = parse_sec_header(content)
    document_text = extract_document_content(content)

    # For now, return chunked version of entire document
    # In future: could implement smart section detection
    chunks = chunk_text(document_text, max_tokens=4000, overlap=200)

    return {
        'metadata': metadata,
        'content_chunks': chunks,
        'full_content': document_text
    }


def extract_10q_sections(content: str) -> Dict[str, str]:
    """
    Extract key sections from 10-Q filing.

    For 10-Q filings, we're interested in:
    - Item 1: Financial Statements
    - Item 2: Management's Discussion and Analysis
    """
    metadata = parse_sec_header(content)
    document_text = extract_document_content(content)

    chunks = chunk_text(document_text, max_tokens=4000, overlap=200)

    return {
        'metadata': metadata,
        'content_chunks': chunks,
        'full_content': document_text
    }


def extract_8k_sections(content: str) -> Dict[str, str]:
    """
    Extract key sections from 8-K filing.

    8-K filings report material events:
    - Item 1.01: Entry into Material Agreement
    - Item 2.01: Completion of Acquisition
    - Item 7.01: Regulation FD Disclosure
    - Item 8.01: Other Events
    - Item 9.01: Financial Statements and Exhibits
    """
    metadata = parse_sec_header(content)
    document_text = extract_document_content(content)

    chunks = chunk_text(document_text, max_tokens=4000, overlap=200)

    return {
        'metadata': metadata,
        'content_chunks': chunks,
        'full_content': document_text
    }


def extract_s1_sections(content: str) -> Dict[str, str]:
    """
    Extract key sections from S-1 filing (IPO registration).

    S-1 filings are comprehensive like 10-K:
    - Part I: Business description, risk factors, use of proceeds
    - Part II: Financial information
    """
    metadata = parse_sec_header(content)
    document_text = extract_document_content(content)

    chunks = chunk_text(document_text, max_tokens=4000, overlap=200)

    return {
        'metadata': metadata,
        'content_chunks': chunks,
        'full_content': document_text
    }


# Dispatcher for filing type
SECTION_EXTRACTORS = {
    '10-K': extract_10k_sections,
    '10-Q': extract_10q_sections,
    '8-K': extract_8k_sections,
    'S-1': extract_s1_sections,
}


def extract_sections(content: str, filing_type: str) -> Dict[str, any]:
    """
    Extract sections from SEC filing based on filing type.

    Args:
        content: Full filing content
        filing_type: SEC form type (10-K, 10-Q, 8-K, S-1)

    Returns:
        Dict with metadata, content_chunks, and full_content
    """
    extractor = SECTION_EXTRACTORS.get(filing_type)

    if not extractor:
        # Fallback: generic extraction
        metadata = parse_sec_header(content)
        document_text = extract_document_content(content)
        chunks = chunk_text(document_text, max_tokens=4000, overlap=200)

        return {
            'metadata': metadata,
            'content_chunks': chunks,
            'full_content': document_text
        }

    return extractor(content)
