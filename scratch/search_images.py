import urllib.request
import re
import json

def get_image_urls(query):
    try:
        # Use DuckDuckGo HTML search for images
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}+restaurant"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
        
        # Look for standard http links in the HTML
        links = re.findall(r'href="([^"]+)"', html)
        img_links = []
        for link in links:
            if 'tripadvisor' in link or 'booking.com' in link or 'restaurant' in link or 'instagram' in link or 'facebook' in link:
                if link.startswith('http'):
                    img_links.append(link)
        return img_links[:5]
    except Exception as e:
        print(f"Error for {query}: {e}")
        return []

queries = [
    "Al Fassia Gueliz Marrakech",
    "Dar Moha Marrakech",
    "La Squala Casablanca",
    "Le Cabestan Casablanca",
    "Dar Naji Rabat",
    "L'Ambre Riad Fes"
]

for q in queries:
    print(f"Query: {q}")
    links = get_image_urls(q)
    for l in links:
        print("  - ", l)
