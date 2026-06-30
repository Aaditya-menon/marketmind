import os
import logging
import datetime
import httpx

logger = logging.getLogger("marketmind.tools.fetch_price_data")

async def fetch_price_data(ticker: str) -> dict:
    """Fetches Daily Adjusted OHLCV price data for the last 30 days for a given ticker symbol.

    This tool calls the Alpha Vantage REST API directly via httpx. It retrieves daily historical
    price timeseries, which is essential for technical indicators and trend analysis.
    If the required API key is missing or the API call fails, it falls back to generating simulated
    market data.

    Args:
        ticker: The stock or cryptocurrency ticker symbol (e.g., MSFT, AAPL, BTC).

    Returns:
        A dictionary containing the daily price data (open, high, low, close, volume) for the last 30 days.
    """
    api_key = os.environ.get("ALPHA_VANTAGE_KEY")
    
    if not api_key:
        logger.warning(f"Alpha Vantage API key (ALPHA_VANTAGE_KEY) not found. Falling back to simulated price data for {ticker}.")
        return _generate_simulated_prices(ticker, "Simulated price data (Alpha Vantage API key not configured)")

    try:
        url = "https://www.alphavantage.co/query"
        known_cryptos = {"BTC", "ETH", "SOL", "USDT", "USDC", "BNB", "XRP", "ADA", "DOGE", "LINK", "AVAX", "DOT", "MATIC", "SHIB", "LTC"}
        is_crypto = ticker.upper() in known_cryptos
        
        if is_crypto:
            params = {
                "function": "DIGITAL_CURRENCY_DAILY",
                "symbol": ticker,
                "market": "USD",
                "apikey": api_key
            }
            time_series_key = "Time Series (Digital Currency Daily)"
        else:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "apikey": api_key,
                "outputsize": "compact"
            }
            time_series_key = "Time Series (Daily)"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            
        if response.status_code == 200:
            data = response.json()
            
            # Check for error messages returned as JSON (e.g. invalid API key or rate limits)
            if "Error Message" in data:
                err_msg = data["Error Message"]
                logger.error(f"Alpha Vantage API returned error: {err_msg}")
                return _generate_simulated_prices(ticker, f"Simulated price data (Alpha Vantage error: {err_msg})")
            
            if "Note" in data:
                note_msg = data["Note"]
                logger.warning(f"Alpha Vantage API rate limit or usage note: {note_msg}")
            
            if time_series_key in data:
                time_series = data[time_series_key]
                sorted_dates = sorted(time_series.keys(), reverse=True)
                last_30_dates = sorted_dates[:30]
                
                filtered_series = {}
                for date in last_30_dates:
                    val = time_series[date]
                    if is_crypto:
                        filtered_series[date] = {
                            "1. open": val.get("1a. open (USD)", val.get("1. open")),
                            "2. high": val.get("2a. high (USD)", val.get("2. high")),
                            "3. low": val.get("3a. low (USD)", val.get("3. low")),
                            "4. close": val.get("4a. close (USD)", val.get("4. close")),
                            "5. volume": val.get("5. volume", val.get("volume", "0"))
                        }
                    else:
                        filtered_series[date] = {
                            "1. open": val.get("1. open"),
                            "2. high": val.get("2. high"),
                            "3. low": val.get("3. low"),
                            "4. close": val.get("4. close"),
                            "5. volume": val.get("5. volume")
                        }
                
                return {
                    "ticker": ticker,
                    "status": "success",
                    "meta_data": data.get("Meta Data", {}),
                    "time_series_30_days": filtered_series
                }
            else:
                msg = data.get("Note") or f"{time_series_key} not found in response"
                logger.error(f"Alpha Vantage daily price series not found in response. Message: {msg}")
                return _generate_simulated_prices(ticker, f"Simulated price data (Alpha Vantage response error: {msg})")
        else:
            logger.error(f"Alpha Vantage request failed with status code {response.status_code}: {response.text}")
            return _generate_simulated_prices(ticker, f"Simulated price data (HTTP error code {response.status_code})")
            
    except Exception as e:
        logger.error(f"Exception during Alpha Vantage API call: {e}. Falling back.")
        return _generate_simulated_prices(ticker, f"Simulated price data (Exception: {str(e)})")

def _generate_simulated_prices(ticker: str, message: str) -> dict:
    """Helper function to generate simulated stock price data for the last 30 days."""
    time_series = {}
    base_price = 150.0
    
    # Simple deterministic hash for base price if ticker differs
    if ticker:
        base_price += float(sum(ord(c) for c in ticker) % 100)
        
    current_date = datetime.date.today()
    
    # Generate 30 days of trading data (skipping weekends)
    days_generated = 0
    while days_generated < 30:
        if current_date.weekday() < 5:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Simulated walk
            day_offset = (days_generated * 0.13) % 4 - 2
            open_p = base_price + day_offset
            close_p = open_p + ((days_generated * 0.47) % 3 - 1.5)
            high_p = max(open_p, close_p) + ((days_generated * 0.25) % 2)
            low_p = min(open_p, close_p) - ((days_generated * 0.29) % 2)
            volume = 1000000 + (days_generated * 10543) % 500000
            
            time_series[date_str] = {
                "1. open": f"{open_p:.4f}",
                "2. high": f"{high_p:.4f}",
                "3. low": f"{low_p:.4f}",
                "4. close": f"{close_p:.4f}",
                "5. volume": f"{int(volume)}"
            }
            days_generated += 1
            
        current_date -= datetime.timedelta(days=1)
        
    return {
        "ticker": ticker,
        "status": "fallback",
        "message": message,
        "meta_data": {
            "1. Information": "Daily Prices (open, high, low, close, volume) Daily Time Series (Simulated)",
            "2. Symbol": ticker,
            "3. Last Refreshed": datetime.date.today().strftime("%Y-%m-%d")
        },
        "time_series_30_days": time_series
    }
