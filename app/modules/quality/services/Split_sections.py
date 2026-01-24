from bs4 import BeautifulSoup

def split_html_into_sections(html_content: str):
    soup = BeautifulSoup(html_content, 'html.parser')
    sections = {}
    
    # 1. Encontrar lo que está antes del primer header (h1, h2 o h3) para "General"
    current_element = soup.find(['h1', 'h2', 'h3'])
    
    # Si no hay headers, todo es general
    if not current_element:
        sections["General"] = str(soup)
        return sections

    # Capturar contenido previo al primer header
    intro_parts = []
    # Iterar sobre los elementos del soup que son previos al primer header
    # Como soup.contents devuelve todos los hijos directos del root:
    for element in soup.contents:
        if element == current_element:
            break
        intro_parts.append(str(element))
    
    intro_content = "".join(intro_parts)
    if intro_content.strip():
        sections["General"] = intro_content

    # 2. Procesar todos los headers en orden
    headers = soup.find_all(['h1', 'h2', 'h3'])
    for header in headers:
        title = header.get_text(strip=True)
        content = ""
        
        # Iterar sobre hermanos siguientes hasta encontrar otro header h1/h2/h3
        for sibling in header.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3']:
                break
            content += str(sibling)
        
        # Guardar sección. Si se repite el título, concatenamos
        if title in sections:
            sections[title] += content
        else:
            sections[title] = content
            
    return sections