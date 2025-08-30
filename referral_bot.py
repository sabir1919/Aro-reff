import requests
import random
import string
import time
import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle

REFERRAL_CODE = "GJMDVK"
REGISTER_URL = "https://preview-api.aro.network/api/user/register"
OUTPUT_FILE = "referrals.csv"
THREADS = 10        # number of parallel workers
MAX_RETRIES = 3     # retries before switching proxy
TIMEOUT = 25        # request timeout

# -----------------------------
# Utility Functions
# -----------------------------
def load_proxies(path="proxies.txt"):
    with open(path) as f:
        proxies = [line.strip() for line in f if line.strip()]
    return proxies, cycle(proxies)  # cycle = infinite rotation

def random_email():
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{user}@mail.com"

def random_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def random_wallet():
    return "0x" + ''.join(random.choices("abcdef" + string.digits, k=40))

def get_session(proxy):
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }
    session = requests.Session()
    session.proxies.update(proxies)
    return session

# -----------------------------
# Core Referral Function
# -----------------------------
def create_referral(proxy_pool):
    for attempt in range(1, MAX_RETRIES + 1):
        proxy = next(proxy_pool)  # pick next proxy in rotation
        email = random_email()
        password = random_password()
        wallet = random_wallet()

        payload = {
            "email": email,
            "password": password,
            "walletAddress": wallet,
            "inviteCode": REFERRAL_CODE
        }

        headers = {
            "Content-Type": "application/json",
            "Origin": "https://dashboard.aro.network",
            "Referer": "https://dashboard.aro.network/",
            "User-Agent": "Mozilla/5.0"
        }

        try:
            session = get_session(proxy)
            r = session.post(REGISTER_URL, headers=headers, json=payload, timeout=TIMEOUT)
            status, response = r.status_code, r.text

            # Save successful or error response
            save_to_csv([email, password, wallet, proxy, status, response[:100]])
            return proxy, email, password, status, response[:80]

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(2)  # backoff before retry
                continue
            else:
                # log failure and rotate proxy automatically
                save_to_csv([email, password, wallet, proxy, None, f"Failed after {MAX_RETRIES} retries: {e}"])
                proxy = next(proxy_pool)  # switch proxy
                continue  # retry with new proxy

    return None, email, password, None, "All retries failed"

# -----------------------------
# Save to CSV
# -----------------------------
def save_to_csv(data):
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["email", "password", "wallet", "proxy", "status", "response"])
        writer.writerow(data)

# -----------------------------
# Main Runner
# -----------------------------
if __name__ == "__main__":
    proxies, proxy_pool = load_proxies()
    print(f"[+] Loaded {len(proxies)} proxies")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = [executor.submit(create_referral, proxy_pool) for _ in range(len(proxies))]

        for future in as_completed(futures):
            proxy, email, password, status, response = future.result()
            print(f"[{proxy}] {email}:{password} -> {status} | {response}")
