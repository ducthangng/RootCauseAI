import re

MD_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)', re.IGNORECASE)
URL_PATTERN = re.compile(r'(https?://[^\s<>"\'\)\]]+|www\.[^\s<>"\'\)\]]+)', re.IGNORECASE)

def _defang(url: str) -> str:
    url = re.sub(r'^https?', lambda m: m.group(0).replace('http', 'hxxp'), url)
    return url.replace('.', '[.]')

def sanitize_urls(text: str) -> str:
    # 1. Triệt cú pháp markdown link trước, để renderer không thấy [text](url) nữa
    text = MD_LINK_PATTERN.sub(lambda m: f"{m.group(1)} ({_defang(m.group(2))})", text)
    # 2. Defang URL trần còn sót lại
    text = URL_PATTERN.sub(lambda m: _defang(m.group(0)), text)
    return text