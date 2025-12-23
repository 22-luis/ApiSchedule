from bs4 import BeautifulSoup

def split_html_into_sections(html_content: str):
    soup = BeautifulSoup(html_content, 'html.parser')
    sections = {}
    
    # Extraer el contenido inicial (antes del primer h2) si existe
    intro_content = ""
    first_h2 = soup.find('h2')
    if first_h2:
        for prev in first_h2.find_all_previous():
            # Evitar duplicados y tags raíz
            if prev.parent.name == '[document]':
                intro_content = str(prev) + intro_content
    
    sections["General"] = intro_content

    # Procesar cada h2
    for h2 in soup.find_all('h2'):
        title = h2.get_text(strip=True)
        content = ""
        for sibling in h2.find_next_siblings():
            if sibling.name == 'h2':
                break
            content += str(sibling)
        sections[title] = content
        
    return sections