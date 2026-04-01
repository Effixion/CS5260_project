import re


def parse_file_refs(content: str, available_files: list[str]) -> tuple[str, list[str]]:
    """
    Extract @filename references from message content.
    Returns (original_content, list_of_referenced_filenames).

    Matches: @filename.csv, @"filename with spaces.csv"
    Only matches against files that actually exist in the project.
    """
    pattern = r'@"([^"]+)"|@(\S+)'
    refs = []
    for match in re.finditer(pattern, content):
        ref = match.group(1) or match.group(2)
        if ref in available_files:
            refs.append(ref)
    return content, refs
