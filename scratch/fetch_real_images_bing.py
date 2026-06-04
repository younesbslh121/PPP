import urllib.request
import re
import urllib.parse

def get_real_bing_image(query):
    try:
        url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        # Bing images are in murl (media url) inside m="{\"murl\":\"http...\"}"
        murls = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', html)
        if murls:
            return murls[0]
            
        # Fallback to general image patterns
        img_urls = re.findall(r'src="http([^"]+\.(?:jpg|png|jpeg))"', html)
        if img_urls:
            return "http" + img_urls[0]
    except Exception as e:
        print(f"Error for {query}: {e}")
    return None

restaurants = [
    ("Al Fassia Gueliz Marrakech", "Al Fassia"),
    ("Dar Moha Marrakech", "Dar Moha"),
    ("La Squala Casablanca", "La Squala"),
    ("Le Cabestan Casablanca", "Le Cabestan"),
    ("Dar Naji Rabat", "Dar Naji"),
    ("Riad Fes L'Ambre", "L'Ambre")
]

for q, name in restaurants:
    img = get_real_bing_image(q)
    print(f"Restaurant: {name} -> {img}")
