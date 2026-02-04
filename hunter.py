import requests
from bs4 import BeautifulSoup

# The keywords you want to find
KEYWORDS = ["hacking", "cyber", "ai", "python", "bug bounty", "nmap", "sqlmap", "burp", "pentest", "security", "javascript"]

def get_coupons():
    url = "https://couponscorpion.com/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
                try:
                        response = requests.get(url, headers=headers)
                                soup = BeautifulSoup(response.text, 'html.parser')
                                        
                                                # Find all course articles
                                                        articles = soup.find_all('article')
                                                                
                                                                        print(f"--- 🔎 Scanned {len(articles)} recent courses ---\n")
                                                                                
                                                                                        found = False
                                                                                                for article in articles:
                                                                                                            title_element = article.find('h3', class_='title')
                                                                                                                        if title_element:
                                                                                                                                        title = title_element.get_text().strip()
                                                                                                                                                        link = title_element.find('a')['href']
                                                                                                                                                                        
                                                                                                                                                                                        # Check if any of your keywords are in the title
                                                                                                                                                                                                        if any(word.lower() in title.lower() for word in KEYWORDS):
                                                                                                                                                                                                                            print(f"✅ MATCH FOUND: {title}")
                                                                                                                                                                                                                                                print(f"🔗 LINK: {link}\n")
                                                                                                                                                                                                                                                                    found = True
                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                    if not found:
                                                                                                                                                                                                                                                                                                print("❌ No matching coupons found in the latest batch. Check back in an hour!")
                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                except Exception as e:
                                                                                                                                                                                                                                                                                                                        print(f"⚠️ Error: {e}")

                                                                                                                                                                                                                                                                                                                        if __name__ == "__main__":
                                                                                                                                                                                                                                                                                                                            get_coupons()