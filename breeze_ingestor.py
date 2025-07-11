import io
import logging
import os
import time
import zipfile
import traceback
from datetime import datetime

import pytz
import requests
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
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler() # To also log to console
    ]
)

# Load credentials and the Convex URL from environment variables
API_KEY = os.getenv("BREEZE_API_KEY")
SECRET_KEY = os.getenv("BREEZE_SECRET_KEY")
SESSION_TOKEN = os.getenv("BREEZE_SESSION_TOKEN")
CONVEX_URL = os.getenv("CONVEX_URL")

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

# Create a global session object to reuse TCP connections for performance
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})


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
        # This prevents errors if the column contains unexpected string values.
        cash_stocks['Token'] = pd.to_numeric(cash_stocks['Token'], errors='coerce')
        
        # Drop rows where 'Token' is NaN (i.e., was not a valid number) and convert to int.
        tokens = cash_stocks.dropna(subset=['Token'])['Token'].astype(int).tolist()

        logging.info(f"Found {len(tokens)} cash stocks in the master file.")
        return tokens
    except KeyError:
        logging.error(f"Master file {CACHE_FILE_PATH} seems to be corrupted or has wrong format (missing 'Series' or 'Token' columns).")
        logging.error(f"Columns found: {list(df.columns)}")
        if os.path.exists(CACHE_FILE_PATH):
            os.remove(CACHE_FILE_PATH)
        return []


def batch_list(data, batch_size):
    """Yield successive n-sized chunks from a list."""
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]


def is_market_open():
    """
    Checks if the Indian stock market is open.
    (Monday-Friday, 9:15 AM to 3:30 PM IST, excluding holidays)
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
        return False # Default to closed on any error

class Ingestor:
    def __init__(self):
        self.breeze = BreezeConnect(api_key=API_KEY)

    def on_ticks(self, ticks):
        """
        This function is the callback that gets executed for every OHLCV bar
        received from the Breeze WebSocket. It handles both single tick (dict)
        and multiple ticks (list of dicts).
        """
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
                    dt_obj = datetime.strptime(tick['datetime'], '%Y-%m-%d %H:%M:%S')
                    timestamp = int(dt_obj.timestamp())

                    # Prepare the data payload in the format our Convex backend expects
                    payload = {
                        "stock_code": tick["stock_code"],
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
                        timeout=5,  # Add a timeout to prevent the script from hanging
                    )

                    if response.status_code == 200:
                        logging.info(
                            f"Successfully ingested {payload['interval']} bar for {payload['stock_code']}"
                        )
                    else:
                        logging.error(
                            f"Failed to ingest bar for {payload['stock_code']}. Status: {response.status_code}, Response: {response.text}"
                        )

                except requests.exceptions.RequestException as e:
                    logging.error(f"HTTP request failed for {tick.get('stock_code')}: {e}")
                except Exception:
                    logging.error(f"An unexpected error in on_ticks for {tick.get('stock_code')}:\n{traceback.format_exc()}")
            else:
                logging.warning(f"Skipping invalid item in tick data: {tick}")

    def run(self):
        while True:
            if is_market_open():
                logging.info("Market is open. Starting ingestor process...")
                try:
                    self.breeze.generate_session(api_secret=SECRET_KEY, session_token=SESSION_TOKEN)
                    logging.info("Successfully generated Breeze API session.")

                    all_tokens = get_nse_cash_stock_tokens()
                    if not all_tokens:
                        logging.error("No stock tokens found. Retrying in 60 seconds.")
                        time.sleep(60)
                        continue

                    self.breeze.ws_connect()
                    logging.info("WebSocket connected successfully.")
                    self.breeze.on_ticks = self.on_ticks

                    subscription_interval = os.getenv("BREEZE_INTERVAL", "5minute")
                    # Set the interval on the breeze object, mimicking the successful legacy implementation.
                    # This should use the existing WebSocket connection for the OHLCV stream.
                    self.breeze.interval = subscription_interval

                    subscription_template = os.getenv("BREEZE_SUBSCRIPTION_TEMPLATE", "4.1!") # Default to NSE Quote Data
                    # Use a batch size and delay inspired by the old, working implementation.
                    batch_size = int(os.getenv("BREEZE_BATCH_SIZE", 1000))
                    batch_delay_s = float(os.getenv("BREEZE_BATCH_DELAY_S", 0.2))

                    token_batches = list(batch_list(all_tokens, batch_size))
                    total_batches = len(token_batches)
                    logging.info(f"Subscribing to {len(all_tokens)} stocks in {total_batches} batches of {batch_size}...")
                    for i, batch in enumerate(token_batches):
                        stock_tokens = [f"{subscription_template}{token}" for token in batch]
                        self.breeze.subscribe_feeds(stock_token=stock_tokens)
                        logging.info(f"Subscribed to batch {i+1}/{total_batches} for {subscription_interval} OHLCV.")
                        time.sleep(batch_delay_s)

                    logging.info("All subscriptions complete. Running until market close...")
                    while is_market_open():
                        time.sleep(60) # Keep the script alive, checking every minute.
                    
                    logging.info("Market has closed. Disconnecting WebSocket.")
                    self.breeze.ws_disconnect()

                except Exception as e:
                    logging.error(f"A critical error occurred during market hours: {e}. Retrying in 30s.")
                    time.sleep(30)
            else:
                logging.info("Market is closed. Checking again in 5 minutes.")
                time.sleep(300)

# --- Main Execution Block ---
if __name__ == "__main__":
    ingestor = Ingestor()
    ingestor.run()