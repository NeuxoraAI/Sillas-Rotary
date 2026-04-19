"""
Folio generation for Sillas Rotary beneficiaries.

Format: {PAIS}-{REGION}-{AÑO}-{NUMERO}
Example: MX-LON-2026-001
"""


def format_folio(pais: str, region: str, year: int, num: int) -> str:
    """
    Format a structured beneficiary folio.

    Args:
        pais:   Country code (e.g. "MX", "US")
        region: Region code (e.g. "LON", "PRL")
        year:   Year of registration (e.g. 2026)
        num:    Sequential number for this pais/region/year combination

    Returns:
        Folio string like "MX-LON-2026-001"

    The number is zero-padded to a minimum of 3 digits but never truncated.
    """
    return f"{pais}-{region}-{year}-{num:03d}"
