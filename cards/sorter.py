import re
import unicodedata

def clean_and_sort_lines(raw_text, remove_duplicates=False):
    """
    Equivalente exacto del script de n8n:
    1. Elimina espacios, comillas, guiones o viñetas al inicio y al final (^[-*•\\s"'`]+|["'`\\s]+$)
    2. Reduce múltiples espacios o tabulaciones internas a un solo espacio (\\s+ -> ' ')
    3. Filtra elementos vacíos
    4. Ordenamiento estricto en español ignorando puntuación/símbolos residuales
    """
    if not raw_text:
        return {
            'original_count': 0,
            'result_count': 0,
            'duplicates_removed': 0,
            'result_text': '',
            'items': []
        }

    lines = raw_text.splitlines()
    original_count = len(lines)

    cleaned = []
    for line in lines:
        # 1. Elimina espacios, comillas, guiones o viñetas al inicio y al final
        item = re.sub(r'^[-*•\s"\'`]+|["\'`\s]+$', '', line)
        # 2. Reduce múltiples espacios o tabulaciones internas a un solo espacio
        item = re.sub(r'\s+', ' ', item).strip()
        # 3. Filtrar vacíos
        if item:
            cleaned.append(item)

    initial_cleaned_count = len(cleaned)
    duplicates_removed = 0

    if remove_duplicates:
        unique_cleaned = list(dict.fromkeys(cleaned))
        duplicates_removed = initial_cleaned_count - len(unique_cleaned)
        cleaned = unique_cleaned

    # 4. Ordenamiento estricto en español ignorando puntuación/símbolos residuales
    # Similar a a.localeCompare(b, 'es', { sensitivity: 'base', ignorePunctuation: true })
    def spanish_sort_key(s):
        # Ignorar puntuación y símbolos matemáticos/residuales para el orden base
        clean_s = re.sub(r'[^\w\s]', '', s, flags=re.UNICODE).lower()
        # Descomposición NFD para normalizar tildes y caracteres base
        # pero conservando la 'ñ' en su orden
        # En español: 'ñ' viene después de la 'n'
        tokens = []
        for char in clean_s:
            if char == 'ñ':
                tokens.append('n~')
            else:
                norm = unicodedata.normalize('NFD', char)
                base = norm[0] if norm else ''
                tokens.append(base)
        return (''.join(tokens), s.lower(), s)

    cleaned.sort(key=spanish_sort_key)

    return {
        'original_count': original_count,
        'result_count': len(cleaned),
        'duplicates_removed': duplicates_removed,
        'result_text': '\n'.join(cleaned),
        'items': cleaned
    }
