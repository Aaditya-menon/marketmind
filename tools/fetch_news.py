import os
import logging
import datetime
import httpx

logger = logging.getLogger("marketmind.tools.fetch_news")

async def fetch_news(ticker: str) -> dict:
    """Fetches the last 10 relevant financial news headlines for a given ticker symbol.

    This tool calls the NewsAPI REST endpoint directly via httpx. It retrieves the article
    title, source name, and publication date for the asset. If the required API key is
    missing or the API call fails, it falls back to generating simulated news articles.

    Args:
        ticker: The stock or cryptocurrency ticker symbol (e.g., GOOG, AAPL, BTC).

    Returns:
        A dictionary containing the ticker, status ("success" or "fallback"), and list of articles.
        Each article contains:
        - title: The headline title
        - source: The name of the publishing source
        - publishedAt: The publication ISO timestamp
    """
    api_key = os.environ.get("NEWS_API_KEY")
    
    if not api_key:
        logger.warning(f"NewsAPI key (NEWS_API_KEY) not found. Falling back to simulated news for {ticker}.")
        return _generate_simulated_news(ticker, "Simulated news (NEWS_API_KEY not configured)")
        
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": ticker,
            "pageSize": 10,
            "apiKey": api_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                articles = []
                for item in data.get("articles", []):
                    source_name = item.get("source", {}).get("name", "Unknown Source")
                    articles.append({
                        "title": item.get("title", "No Title Available"),
                        "source": source_name,
                        "publishedAt": item.get("publishedAt", "")
                    })
                return {
                    "ticker": ticker,
                    "status": "success",
                    "articles": articles
                }
            else:
                logger.error(f"NewsAPI returned error status: {data.get('message')}")
                return _generate_simulated_news(ticker, f"Simulated news (NewsAPI error: {data.get('message')})")
        else:
            logger.error(f"NewsAPI request failed with status code {response.status_code}: {response.text}")
            return _generate_simulated_news(ticker, f"Simulated news (HTTP error code {response.status_code})")
            
    except Exception as e:
        logger.error(f"Exception during NewsAPI call: {e}. Falling back.")
        return _generate_simulated_news(ticker, f"Simulated news (Exception: {str(e)})")

def _generate_simulated_news(ticker: str, message: str) -> dict:
    """Helper function to generate simulated news articles for the last 10 headlines."""
    today = datetime.datetime.now(datetime.timezone.utc)
    articles = []
    
    simulated_titles = [
        f"{ticker} shares rise amid strong quarterly earnings reports.",
        f"Analysts adjust price targets for {ticker} following recent product announcements.",
        f"Market volatility impacts tech sector, including {ticker}.",
        f"New regulatory policies could affect {ticker}'s domestic operations.",
        f"Investors monitor {ticker} closely ahead of next week's board meeting.",
        f"{ticker} announces strategic partnership to expand cloud infrastructure.",
        f"Trade volumes for {ticker} spike following macroeconomic indicator updates.",
        f"{ticker} CEO discusses future growth areas and R&D investments in interview.",
        f"Competitors pressure {ticker}'s market share in key retail segments.",
        f"Overall sentiment on {ticker} remains cautious but optimistic among institutional investors."
    ]
    
    sources = ["Bloomberg", "Reuters", "Financial Times", "MarketWatch", "CNBC", "Wall Street Journal"]
    
    for i, title in enumerate(simulated_titles):
        pub_time = today - datetime.timedelta(hours=i*2, minutes=i*15)
        articles.append({
            "title": title,
            "source": sources[i % len(sources)],
            "publishedAt": pub_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        
    return {
        "ticker": ticker,
        "status": "fallback",
        "message": message,
        "articles": articles
    }
