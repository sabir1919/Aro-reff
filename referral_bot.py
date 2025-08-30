import requests
import random
import string
import time
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle

REFERRAL_CODE = "GJMDVK"
REGISTER_URL = "https://api.aro.network/api/auth/register"
OUTPUT_FILE = "referrals.csv"
THREADS = 10        # number of parallel workers
MAX_RETRIES = 3     # retries before switching proxy
TIMEOUT = 25        # request timeout
DEFAULT_LIMIT = 50  # fallback if no argument given

# -----------------------------
# Utility Functions
# -----------------------------
def load_proxies(path="proxies.txt"):
    with open(path) as f:
        proxies = [line.strip() for line in f if line.strip()]
    return proxies, cycle(proxies)

def random_email():
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{user}@mail.com"

def random_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def random_wallet():
    return "0x" + ''.join(random.choices("abcdef" + string.digits, k=40))

def check_proxy(proxy):
    try:
        test = requests.get(
            "https://api.aro.network/",
            proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
            timeout=5
        )
        return test.status_code < 500
    except:
        return False

def get_session(proxy=None):
    session = requests.Session()
    if proxy:
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
        session.proxies.update(proxies)
    return session

# -----------------------------
# Core Referral Function
# -----------------------------
def create_referral(proxy_pool):
    for attempt in range(1, MAX_RETRIES + 1):
        proxy = next(proxy_pool)
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

            save_to_csv([email, password, wallet, proxy, status, response[:200]])
            return proxy, email, password, status, response[:80]

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue
            else:
                save_to_csv([email, password, wallet, proxy, None, f"Failed after {MAX_RETRIES} retries: {e}"])
                return proxy, email, password, None, str(e)

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
    # Read referral limit from CLI or use default
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        REFERRAL_LIMIT = int(sys.argv[1])
    else:
        REFERRAL_LIMIT = DEFAULT_LIMIT

    print(f"[+] Referral limit set to {REFERRAL_LIMIT}")

    proxies, proxy_pool = load_proxies()
    print(f"[+] Loaded {len(proxies)} proxies")

    working_proxies = [p for p in proxies if check_proxy(p)]
    if working_proxies:
        print(f"[+] {len(working_proxies)} working proxies found")
        proxy_pool = cycle(working_proxies)
    else:
        print("[!] No working proxies found, falling back to direct connection")
        proxy_pool = cycle([None])

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = [executor.submit(create_referral, proxy_pool) for _ in range(REFERRAL_LIMIT)]

        for future in as_completed(futures):
            proxy, email, password, status, response = future.result()
            print(f"[{proxy}] {email}:{password} -> {status} | {response}")
