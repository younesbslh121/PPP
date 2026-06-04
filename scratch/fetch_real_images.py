import urllib.request
import re
import urllib.parse

def get_real_google_image(query):
    try:
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=isch"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('ISO-8859-1')
        
        # Google Image search HTML contains tbn links like:
        # https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9Gc...
        matches = re.findall(r'(https://encrypted-tbn[0-9]\.gstatic\.com/images\?q=tbn:[^"\&\s]+)', html)
        if matches:
            return matches[0] # Return the first matching image
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

results = {}
for q, name in restaurants:
    img = get_real_google_image(q)
    results[name] = img
    print(f"Restaurant: {name} -> {img}")
