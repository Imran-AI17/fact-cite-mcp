cat > server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import re
from collections import Counter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ApiInput(BaseModel):
    url: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)

async def fetch_and_parse_html(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) a_s client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "lxml")
        return soup

    except Exception as e:
        print(f"!!! DETAILED ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Data stream analysis failed. The website may be blocking access. Error: {e}")

def get_professional_summary_text(soup):
    """
    An intelligent engine to find and extract the official lead section of an article
    for a high-quality, professional summary.
    """
    content_area = soup.select_one('#mw-content-text .mw-parser-output') or soup.select_one('article') or soup.select_one('main')

    if not content_area:
        return ""

    summary_paragraphs = []
    for element in content_area.find_all(['p', 'h2', 'div'], recursive=False):
        if element.name == 'h2' or (element.name == 'div' and 'toc' in element.get('id', '')):
            break
        
        if element.name == 'p':
            for sup in element.select('sup.reference'):
                sup.decompose()
            
            clean_text = element.get_text(strip=True)
            if clean_text:
                summary_paragraphs.append(clean_text)

    return ' '.join(summary_paragraphs)

@app.post("/summarize_url")
async def summarize_url(data: ApiInput):
    soup = await fetch_and_parse_html(data.url)
    summary_text = get_professional_summary_text(soup)
    
    if not summary_text:
        raise HTTPException(status_code=400, detail="Could not extract a professional summary. The page may not have a standard introductory section.")

    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', summary_text)
    main_points = [s.strip() for s in sentences if s.strip() and len(s.split()) > 3]

    if not main_points:
        raise HTTPException(status_code=400, detail="The main content was too short to be summarized into key points.")

    return {"source_url": data.url, "bullets": [{"claim": point} for point in main_points]}

@app.post("/keywords")
async def get_keywords(data: ApiInput):
    soup = await fetch_and_parse_html(data.url)
    text = get_professional_summary_text(soup).lower()

    if not text:
        raise HTTPException(status_code=400, detail="Could not find any main content to extract keywords from.")

    words = re.findall(r'\b\w{4,15}\b', text)
    stop_words = set(["the", "and", "a", "to", "in", "is", "it", "of", "that", "for", "on", "with", "as", "this", "was", "are", "from", "by", "an", "at", "be", "have", "not", "or", "which", "also", "its", "were", "but", "what", "when", "where", "who", "why", "he", "his", "she", "her", "they", "them", "their", "has", "had", "been", "will", "can", "would", "could"])
    meaningful_words = [word for word in words if word not in stop_words]
    top_keywords = [item[0] for item in Counter(meaningful_words).most_common(12)]

    if not top_keywords:
        raise HTTPException(status_code=400, detail="Could not extract keywords from the page content.")

    return {"source_url": data.url, "keywords": top_keywords}
EOF
      
