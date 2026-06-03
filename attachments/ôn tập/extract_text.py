import re

def extract(html_file, txt_file):
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
        
    # Remove script and style elements
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove extra spaces and unescape entities
    import html as html_lib
    text = html_lib.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text)

extract('W1-D1_ Metric Anomaly Detection _ My Learning Notes.html', 'w1d1.txt')
extract('W1-D2_ Log Mining + Parsing + Anomaly từ Log _ My Learning Notes.html', 'w1d2.txt')
