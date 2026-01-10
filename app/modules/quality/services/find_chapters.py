from bs4 import BeautifulSoup


def find_chapters(html_content):
    chapters = []

    if isinstance(html_content, dict):
        for value in html_content.values():
            chapters += find_chapters(value)

    elif isinstance(html_content, list):
        for item in html_content:
            chapters += find_chapters(item)

    elif isinstance(html_content, str):
        if "<h1>" in html_content.lower():
            soup = BeautifulSoup(html_content, 'html.parser')
            chapters.extend([h1.get_text(strip=True) for h1 in soup.find_all('h1')])

    return chapters