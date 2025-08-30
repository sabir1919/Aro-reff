import requests
import time
import random
import string
import csv
import os
import sys
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed

# -----------------------------
# CONFIG
# -----------------------------
API_KEY = "YOUR_2CAPTCHA_API_KEY"  # <-- put your 2Captcha key here
SITE_KEY = "6LdsmFYUAAAAACkQ2e6vGJMdVkp_xxxxxxxxxx"  # <-- from HAR
PAGE_URL = "https://dashboard.aro.network/"
REGISTER_URL = "https://preview-api.aro.network/api/auth/register"
REFERRAL_CODE = "GJMDVK"

THREADS = 5
TIMEOUT = 30
OUTPUT_FILE = "referrals.csv"

# -----------------------------
# Captcha Solver
# -----------------------------
def solve_captcha(api_key, site_key, url):
    s = requests.Session()

    # 1. Submit captcha task
    print("[*] Sending captcha to 2Captcha...")
    resp = s.post("http://2captcha.com/in.php", {
        "key": api_key,
        "method": "userrecaptcha",
        "googlekey": site_key,
        "pageurl": url,
        "json": 1
    }).json()

    if resp["status"] != 1:
        raise Exception(f"2Captcha error: {resp}")

    captcha_id = resp["request"]

    # 2. Poll until solved
    for _ in range(24):  # wait up to 2 minutes
        time.sleep(5)
        check = s.get("http://2captcha.com/res.php", params={
            "key": api_key,
            "action": "get",
            "id": captcha_id,
            "json": 1
        }).json()
        if check["status"] == 1:
            print("[+] Captcha solved")
            return check["request"]
        elif check["request"] != "CAPCHA_NOT_READY":
            raise Exception(f"2Captcha failed: {check}")
    raise Exception("Captcha solving timeout")

# -----------------------------
# Helpers
# -----------------------------
def random_email():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@mail.com"

def random_password():
    return ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=12))

def load_proxies(path="proxies.txt"):
    try:
        with open(path) as f:
            proxies = [line.strip() for line in f if line.strip()]
        return proxies
    except FileNotFoundError:
        return []

def save_to_csv(data):
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["email", "password", "proxy", "status", "response"])
        writer.writerow(data)

# -----------------------------
# Referral Creator
# -----------------------------
def create_referral(proxy=None):
    email = random_email()
    password = random_password()

    try:
        # Solve captcha
        token = solve_captcha(API_KEY, SITE_KEY, PAGE_URL)

        payload = {
            "email": email,
            "password": password,
            "confirmPassword": password,
            "inviteCode": REFERRAL_CODE,
            "g-recaptcha-response": token
        }

        proxies = {"http": proxy, "https": proxy} if proxy else None
        r = requests.post(REGISTER_URL, json=payload, timeout=TIMEOUT, proxies=proxies)

        save_to_csv([email, password, proxy, r.status_code, r.text])
        return proxy, email, password, r.status_code, r.text

    except Exception as e:
        save_to_csv([email, password, proxy, None, str(e)])
        return proxy, email, password, None, str(e)

# -----------------------------
# Main Runner
# -----------------------------
if __name__ == "__main__":
    # Referral limit from command line
    if len(sys.argv) > 1:
        try:
            REFERRAL_LIMIT = int(sys.argv[1])
        except:
            print("Usage: python referral_bot.py <referral_limit>")
            sys.exit(1)
    else:
        REFERRAL_LIMIT = 10

    print(f"[+] Referral limit set to {REFERRAL_LIMIT}")

    # Load proxies
    proxies = load_proxies()
    print(f"[+] Loaded {len(proxies)} proxies")
    proxy_pool = cycle(proxies) if proxies else cycle([None])

    # Run referrals
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = [executor.submit(create_referral, next(proxy_pool)) for _ in range(REFERRAL_LIMIT)]
        for future in as_completed(futures):
            proxy, email, password, status, response = future.result()
            print(f"[{proxy}] {email}:{password} -> {status} | {response[:200]}")
