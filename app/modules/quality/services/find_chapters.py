from bs4 import BeautifulSoup

def find_chapters(html_content):
    if not html_content:
        return []
    
    chapters = []

    if isinstance(html_content, dict):
        # Format 1: New structured format with 'sections' metadata
        if "sections" in html_content and isinstance(html_content["sections"], list):
            for s in html_content["sections"]:
                if isinstance(s, dict) and s.get("title"):
                    chapters.append(s["title"])
            if chapters:
                unique_chapters = []
                seen = set()
                for c in chapters:
                    trimmed = c.strip()
                    if trimmed and trimmed not in seen:
                        unique_chapters.append(trimmed)
                        seen.add(trimmed)
                return unique_chapters

        # Format 2: Contains the full 'content_html'
        if "content_html" in html_content and isinstance(html_content["content_html"], str):
            # Recurse specifically with the HTML content string
            return find_chapters(html_content["content_html"])

        # Format 3: Legacy split format or basic keys
        ignored_keys = ["General", "content_html", "sections", "hierarchy", "capitulos", "version", "id", "name"]
        for key, value in html_content.items():
            if key not in ignored_keys:
                chapters.append(key)
            
            # Also check within the value if it's a string, just in case
            if isinstance(value, str) and "<h" in value.lower():
                chapters += find_chapters(value)

    elif isinstance(html_content, list):
        for item in html_content:
            chapters += find_chapters(item)

    elif isinstance(html_content, str):
        # Extract headers from a raw HTML string
        if "<h" in html_content.lower():
            soup = BeautifulSoup(html_content, 'html.parser')
            # Look for h1, h2 and h3
            headers = soup.find_all(['h1', 'h2', 'h3'])
            for h in headers:
                text = h.get_text(strip=True)
                if text:
                    chapters.append(text)

    # Clean up results
    unique_chapters = []
    seen = set()
    for c in chapters:
        trimmed = c.strip()
        if trimmed and trimmed not in seen:
            unique_chapters.append(trimmed)
            seen.add(trimmed)
            
    return unique_chapters