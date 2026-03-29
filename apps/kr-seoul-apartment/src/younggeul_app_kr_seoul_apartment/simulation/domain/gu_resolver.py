"""Utilities for resolving Seoul district identifiers from user hints."""

from __future__ import annotations

SEOUL_GU_MAP: dict[str, str] = {
    "11110": "종로구",
    "11140": "중구",
    "11170": "용산구",
    "11200": "성동구",
    "11215": "광진구",
    "11230": "동대문구",
    "11260": "중랑구",
    "11290": "성북구",
    "11305": "강북구",
    "11320": "도봉구",
    "11350": "노원구",
    "11380": "은평구",
    "11410": "서대문구",
    "11440": "마포구",
    "11470": "양천구",
    "11500": "강서구",
    "11530": "구로구",
    "11545": "금천구",
    "11560": "영등포구",
    "11590": "동작구",
    "11620": "관악구",
    "11650": "서초구",
    "11680": "강남구",
    "11710": "송파구",
    "11740": "강동구",
}
SEOUL_NAME_TO_CODE: dict[str, str] = {name: code for code, name in SEOUL_GU_MAP.items()}


def resolve_gu_codes(
    geography_hint: str | None,
    available_gu_codes: list[str],
) -> tuple[list[str], list[str]]:
    """Resolve target district codes from a free-form geography hint.

    Args:
        geography_hint: Free-form district hint from the user query.
        available_gu_codes: District codes available in snapshot coverage.

    Returns:
        A tuple of resolved district codes and warning messages.
    """
    if geography_hint is None:
        return list(available_gu_codes), []

    hint = geography_hint.strip()
    if not hint:
        return list(available_gu_codes), ["Geography hint was empty; using all available districts."]

    warnings: list[str] = []
    available_set = set(available_gu_codes)

    if hint in SEOUL_GU_MAP:
        if hint in available_set:
            return [hint], warnings
        return list(available_gu_codes), [f"Requested gu code '{hint}' is unavailable in snapshot coverage."]

    direct_code = SEOUL_NAME_TO_CODE.get(hint)
    if direct_code is not None:
        if direct_code in available_set:
            return [direct_code], warnings
        return list(available_gu_codes), [f"Requested district '{hint}' is unavailable in snapshot coverage."]

    matched_codes = [
        code for code in available_gu_codes if SEOUL_GU_MAP.get(code) is not None and SEOUL_GU_MAP[code] in hint
    ]
    if matched_codes:
        return matched_codes, warnings

    warnings.append(f"Could not resolve geography hint '{geography_hint}'; using all available districts.")
    return list(available_gu_codes), warnings
