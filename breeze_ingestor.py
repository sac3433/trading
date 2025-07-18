import io
import logging
import os
import time
import zipfile
import traceback
from datetime import datetime, timedelta
import pytz
import requests
import requests.adapters
import pandas as pd
from breeze_connect import BreezeConnect
from dotenv import load_dotenv

# Load environment variables from the .env file in the current directory
load_dotenv()

# --- Configuration ---
# Set up logging to both console and a file
LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIR, "ingestor.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler() # To also log to console
    ]
)

# Load credentials and the Convex URL from environment variables
API_KEY = os.getenv("BREEZE_API_KEY")
SECRET_KEY = os.getenv("BREEZE_SECRET_KEY")
CONVEX_URL = os.getenv("CONVEX_URL")

# Token file path (shared volume)
TOKEN_FILE_PATH = "/app/config/session_token.txt"

def get_session_token():
    """
    Get session token from file first, fallback to environment variable.
    """
    try:
        if os.path.exists(TOKEN_FILE_PATH):
            with open(TOKEN_FILE_PATH, 'r') as f:
                token = f.read().strip()
                if token:
                    logging.info("Using session token from config file.")
                    return token
    except Exception as e:
        logging.warning(f"Could not read token from file: {e}")
    
    # Fallback to environment variable
    env_token = os.getenv("BREEZE_SESSION_TOKEN")
    if env_token:
        logging.info("Using session token from environment variable.")
        return env_token
    
    return None

# Get session token
SESSION_TOKEN = get_session_token()

# Check for missing environment variables and exit if they aren't set
if not all([API_KEY, SECRET_KEY, SESSION_TOKEN, CONVEX_URL]):
    logging.error(
        "FATAL: Missing one or more required environment variables: BREEZE_API_KEY, BREEZE_SECRET_KEY, BREEZE_SESSION_TOKEN, CONVEX_URL"
    )
    exit(1)

# A set of market holidays from environment variable (comma-separated YYYY-MM-DD).
holidays_str = os.getenv("MARKET_HOLIDAYS", "")
HOLIDAYS = set(holidays_str.split(',')) if holidays_str else set()

# The new endpoint for OHLCV data
INGEST_URL = f"{CONVEX_URL}/ingestOhlcv"

# Configure session with optimized connection pool
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})
adapter = requests.adapters.HTTPAdapter(
    pool_connections=20,
    pool_maxsize=100,
    max_retries=1,
    pool_block=False
)
session.mount('http://', adapter)
session.mount('https://', adapter)

def get_nse_cash_stock_tokens():
    """
    Downloads the NSE Equities master zip file, extracts NSEScripMaster.txt,
    parses it, and returns a list of stock tokens for all cash equities (series 'EQ').
    """
    # Correct URL for the zip file containing NSE equity master data, updated daily.
    DEFAULT_MASTER_URL = "https://directlink.icicidirect.com/NewSecurityMaster/SecurityMaster.zip"
    NSE_MASTER_ZIP_URL = os.getenv("BREEZE_MASTER_URL", DEFAULT_MASTER_URL)
    MASTER_FILE_NAME = "NSEScripMaster.txt"
    CACHE_DIR = "./cache"
    CACHE_FILE_PATH = os.path.join(CACHE_DIR, MASTER_FILE_NAME)
    os.makedirs(CACHE_DIR, exist_ok=True)

    # Check if a recent cached version exists
    try:
        cache_lifetime_hours = int(os.getenv("CACHE_LIFETIME_HOURS", 23))
        file_mod_time = os.path.getmtime(CACHE_FILE_PATH)
        if time.time() - file_mod_time < cache_lifetime_hours * 60 * 60:
            logging.info(f"Using cached master file: {CACHE_FILE_PATH}")
            df = pd.read_csv(CACHE_FILE_PATH, skipinitialspace=True)
            df.columns = df.columns.str.strip().str.strip('"').str.strip()
        else:
            raise FileNotFoundError # File is too old, download a new one
    except (FileNotFoundError, OSError):
        logging.info(f"Downloading new master file from {NSE_MASTER_ZIP_URL}...")
        try:
            response = requests.get(NSE_MASTER_ZIP_URL, timeout=60)
            response.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(response.content)) as thezip:
                if MASTER_FILE_NAME not in thezip.namelist():
                    logging.error(f"'{MASTER_FILE_NAME}' not found in the downloaded zip file.")
                    return []
                # Save the extracted file to cache
                with thezip.open(MASTER_FILE_NAME) as source, open(CACHE_FILE_PATH, "wb") as target:
                    target.write(source.read())

            df = pd.read_csv(CACHE_FILE_PATH, skipinitialspace=True)
            df.columns = df.columns.str.strip().str.strip('"').str.strip()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to download NSE master zip file: {e}")
            return []
        except Exception as e:
            logging.error(f"Failed to process new master file: {e}")
            return []
            
    try:
        # Filter for cash equities (Series == 'EQ') and where Token is not null
        cash_stocks = df[df['Series'] == 'EQ'].copy()
        
        # Convert 'Token' column to numeric, coercing any non-numeric values to NaN.
        cash_stocks['Token'] = pd.to_numeric(cash_stocks['Token'], errors='coerce')
        
        # Only filter out invalid tokens (0, NaN, or negative values)
        valid_stocks = cash_stocks[
            (cash_stocks['Token'].notna()) & 
            (cash_stocks['Token'] > 0)
        ].copy()
        
        # Remove the stock limiting logic completely
        # Extract all valid tokens without any limit
        tokens = valid_stocks['Token'].astype(int).tolist()
        logging.info(f"Found {len(tokens)} valid cash stocks in the master file.")
        return tokens
    except KeyError as e:
        logging.error(f"Master file {CACHE_FILE_PATH} seems to be corrupted or has wrong format (missing column: {e}).")
        logging.error(f"Columns found: {list(df.columns)}")
        if os.path.exists(CACHE_FILE_PATH):
            os.remove(CACHE_FILE_PATH)
        return []

def is_market_session_time():
    """
    Checks if it's time to start the trading session (connect and subscribe).
    Starts 15 minutes before market open for preparation.
    """
    try:
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)

        # Check if it's a holiday
        if now.strftime('%Y-%m-%d') in HOLIDAYS:
            return False

        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() > 4:
            return False

        # Start session at 9:00 AM (15 minutes before market open for subscriptions)
        session_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        # End session at 3:40 PM (10 minutes after market close to capture final bars)
        session_end = now.replace(hour=15, minute=40, second=0, microsecond=0)

        return session_start <= now <= session_end
    except Exception as e:
        logging.warning(f"Could not determine session status due to an error: {e}. Assuming session is closed.")
        return False

def is_market_open():
    """
    Checks if the market is actually open for trading (9:15 AM to 3:30 PM IST).
    Used to control when tick processing starts.
    """
    try:
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)

        # Check if it's a holiday
        if now.strftime('%Y-%m-%d') in HOLIDAYS:
            return False

        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() > 4:
            return False

        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

        return market_open <= now <= market_close
    except Exception as e:
        logging.warning(f"Could not determine market status due to an error: {e}. Assuming market is closed.")
        return False

def get_next_market_opening():
    """
    Calculate the next market opening time (9:15 AM IST on the next trading day).
    Accounts for weekends and holidays.
    """
    try:
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        
        # First check if today still has a session ahead
        if now.weekday() <= 4:  # Monday to Friday
            if now.strftime('%Y-%m-%d') not in HOLIDAYS:
                # Check if today's session hasn't started yet (before 9:00 AM)
                today_session_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if now < today_session_start:
                    # Market opens later today
                    return now.replace(hour=9, minute=15, second=0, microsecond=0)
        
        # If today's session is over or it's weekend/holiday, check from tomorrow
        next_day = now + timedelta(days=1)
        
        while True:
            # Check if it's a weekday (Monday=0, Sunday=6)
            if next_day.weekday() <= 4:  # Monday to Friday
                # Check if it's not a holiday
                if next_day.strftime('%Y-%m-%d') not in HOLIDAYS:
                    # This is a valid trading day
                    market_open_time = next_day.replace(hour=9, minute=15, second=0, microsecond=0)
                    return market_open_time
            
            # Move to next day if weekend or holiday
            next_day += timedelta(days=1)
            
    except Exception as e:
        logging.warning(f"Could not calculate next market opening: {e}. Defaulting to 5-minute check.")
        return None

class Ingestor:
    def __init__(self):
        self.breeze = BreezeConnect(api_key=API_KEY)
        self.last_seen_timestamps = {}  # Track last seen timestamp per stock
        self.subscriptions_complete = False  # Flag to control tick processing

    def on_ticks(self, ticks):
        """
        This function is the callback that gets executed for every OHLCV bar
        received from the Breeze WebSocket. It handles both single tick (dict)
        and multiple ticks (list of dicts).
        """
        # Don't process ticks until all subscriptions are complete AND market is actually open
        if not self.subscriptions_complete:
            logging.debug("Subscriptions still in progress, holding back tick processing...")
            return
            
        if not is_market_open():
            logging.debug("Market not yet open, holding back tick processing...")
            return
            
        if not ticks:
            return
            
        # Ensure ticks is a list for consistent processing, as the API can send
        # either a single dictionary or a list of dictionaries.
        if isinstance(ticks, dict):
            ticks_to_process = [ticks]
        elif isinstance(ticks, list):
            ticks_to_process = ticks
        else:
            logging.warning(f"Received tick data in unexpected format: {type(ticks)}. Data: {ticks}")
            return
            
        logging.info(f"Received {len(ticks_to_process)} tick(s)")

        for tick in ticks_to_process:
            # We only care about valid OHLCV ticks that have both 'close' and 'datetime' keys.
            # This filters out other message types like simple quotes or confirmations.
            if isinstance(tick, dict) and tick.get("close") and tick.get("datetime"):
                try:
                    # Convert the datetime string from Breeze to a Unix timestamp
                    # Assume Breeze sends IST time and convert properly
                    dt_obj = datetime.strptime(tick['datetime'], '%Y-%m-%d %H:%M:%S')
                    ist_tz = pytz.timezone('Asia/Kolkata')
                    dt_obj_ist = ist_tz.localize(dt_obj)  # Mark as IST
                    timestamp = int(dt_obj_ist.timestamp())  # Convert to UTC timestamp
                    
                    stock_code = tick["stock_code"]
                    
                    # Check for duplicate timestamps to avoid unnecessary updates
                    if stock_code in self.last_seen_timestamps:
                        if timestamp <= self.last_seen_timestamps[stock_code]:
                            logging.debug(f"Duplicate/old timestamp for {stock_code}: {timestamp}")
                            continue
                    
                    self.last_seen_timestamps[stock_code] = timestamp
                    
                    # Prepare the data payload in the format our Convex backend expects
                    payload = {
                        "stock_code": stock_code,
                        "open": float(tick["open"]),
                        "high": float(tick["high"]),
                        "low": float(tick["low"]),
                        "close": float(tick["close"]),
                        "volume": int(tick["volume"]),
                        "interval": tick["interval"],
                        "timestamp": timestamp,
                    }

                    # Send the data to the Convex HTTP endpoint via a POST request
                    response = session.post(
                        INGEST_URL,
                        json=payload,
                        timeout=3,  # Reduced timeout
                    )
                    
                    if response.status_code == 200:
                        logging.info(f"Successfully ingested {payload['interval']} bar for {payload['stock_code']} at {timestamp} ({tick['datetime']})")
                    else:
                        logging.warning(f"Failed to ingest bar for {payload['stock_code']}. Status: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logging.warning(f"HTTP request failed for {tick.get('stock_code')}: {e}")
                except Exception:
                    logging.error(f"An unexpected error in on_ticks for {tick.get('stock_code')}:\n{traceback.format_exc()}")
            else:
                logging.debug(f"Skipping invalid item in tick data: {tick}")

    def run(self):
        while True:
            if is_market_session_time():
                logging.info("Trading session time. Starting ingestor process...")
                try:
                    # Re-read token at start of each session (in case it was updated)
                    current_token = get_session_token()
                    if not current_token:
                        logging.error("No session token available. Retrying in 60 seconds.")
                        time.sleep(60)
                        continue
                    
                    # The logical order: Generate session first, then connect to WebSocket
                    self.breeze.generate_session(api_secret=SECRET_KEY, session_token=current_token)
                    logging.info("Successfully generated Breeze API session.")

                    self.breeze.ws_connect()
                    logging.info("WebSocket connected successfully.")
                    self.breeze.on_ticks = self.on_ticks
                    
                    # Reset the flag at the start of each session
                    self.subscriptions_complete = False
                    
                    all_tokens = get_nse_cash_stock_tokens()
                    if not all_tokens:
                        logging.error("No stock tokens found. Retrying in 60 seconds.")
                        time.sleep(60)
                        continue

                    subscription_interval = os.getenv("BREEZE_INTERVAL", "1minute")
                    subscription_template = "4.1!"
                    
                    # Subscribe in batches to avoid overwhelming the API
                    batch_size = int(os.getenv("BATCH_SIZE", "25"))
                    subscription_delay = float(os.getenv("SUBSCRIPTION_DELAY", "0.1"))
                    
                    if not is_market_open():
                        logging.info("🌅 PRE-MARKET: Starting subscriptions before market opens at 9:15 AM...")
                    
                    logging.info(f"Subscribing to {len(all_tokens)} stocks in batches of {batch_size}...")
                    logging.info("📵 Tick processing is PAUSED until subscriptions complete AND market opens...")
                    
                    successful_subscriptions = 0
                    
                    for i, token in enumerate(all_tokens):
                        try:
                            stock_token = f"{subscription_template}{token}"
                            self.breeze.subscribe_feeds(stock_token=stock_token, interval=subscription_interval)
                            successful_subscriptions += 1
                            logging.info(f"({i+1}/{len(all_tokens)}) ✓ Subscribed to {stock_token} for {subscription_interval} OHLCV.")
                        except Exception as e:
                            logging.error(f"✗ Failed to subscribe to {subscription_template}{token}: {e}")
                        
                        # Add delay between subscriptions to be respectful to the API
                        time.sleep(subscription_delay)
                        
                        # Every batch, check if we're still connected
                        if (i + 1) % batch_size == 0:
                            logging.info(f"Completed batch {(i + 1) // batch_size}. Pausing briefly...")
                            time.sleep(2)  # Brief pause between batches

                    # All subscriptions complete
                    self.subscriptions_complete = True
                    logging.info(f"🎯 All subscriptions complete! Successfully subscribed to {successful_subscriptions}/{len(all_tokens)} stocks.")
                    
                    # Wait for market to actually open if we're early
                    while is_market_session_time() and not is_market_open():
                        tz = pytz.timezone('Asia/Kolkata')
                        now = datetime.now(tz)
                        market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
                        wait_seconds = (market_open_time - now).total_seconds()
                        if wait_seconds > 0:
                            logging.info(f"⏰ Subscriptions ready! Waiting {wait_seconds:.0f} seconds for market to open at 9:15 AM...")
                            time.sleep(min(60, wait_seconds))  # Check every minute or until market opens
                        else:
                            break
                    
                    if is_market_open():
                        logging.info("📡 Market is OPEN! Tick processing is now ENABLED - data will be ingested and stored.")

                    logging.info("Running until session ends...")
                    while is_market_session_time():
                        time.sleep(60) # Keep the script alive, checking every minute.

                    logging.info("Trading session ended. Disconnecting WebSocket.")
                    self.breeze.ws_disconnect()
                except Exception as e:
                    logging.error(f"A critical error occurred during session: {e}. Retrying in 30s.")
                    traceback.print_exc()
                    time.sleep(30)
            else:
                # Calculate when next session starts (9:00 AM next trading day)
                next_opening = get_next_market_opening()
                if next_opening:
                    # Adjust to start session 15 minutes earlier
                    next_session_start = next_opening.replace(hour=9, minute=0)
                    tz = pytz.timezone('Asia/Kolkata')
                    now = datetime.now(tz)
                    sleep_seconds = (next_session_start - now).total_seconds()
                    
                    if sleep_seconds > 0:
                        logging.info(f"Trading session closed. Next session starts: {next_session_start.strftime('%Y-%m-%d %H:%M:%S IST')}")
                        logging.info(f"Sleeping for {sleep_seconds/3600:.1f} hours until next session...")
                        time.sleep(sleep_seconds)
                    else:
                        time.sleep(60)
                else:
                    logging.info("Trading session closed. Checking again in 5 minutes.")
                    time.sleep(300)

# --- Main Execution Block ---
if __name__ == "__main__":
    ingestor = Ingestor()
    ingestor.run()


