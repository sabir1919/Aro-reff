import requests
import random
import string
import sys
import time
import json
import os

# -----------------------------
# CONFIG
# -----------------------------
CONFIG_FILE = "config.json"

if not os.path.exists(CONFIG_FILE):
    print("[!] config.json not found. Please create it with your settings.")
    sys.exit(1)

with open(CONFIG_FILE, "r") as f:
    cfg = json.load(f)

API_KEY = cfg.get("API_KEY", "")
SITE_KEY = cfg.get("SITE_KEY", "")
PAGE_URL = cfg.get("PAGE_URL", "https://dashboard.aro.network/auth/signup")
REGISTER_URL = cfg.get("REGISTER_URL", "https://preview-api.aro.network/api/user/signUpProd")
REFERRAL_CODE = cfg.get("REFERRAL_CODE", "")
DATA_S = cfg.get("DATA_S", "")

PROXIES_FILE = "proxies.txt"

# -----------------------------
# HELPERS
# -----------------------------
def random_email():
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{name}@mail.com"

def random_password():
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=12))

def load_proxies():
    try:
        with open(PROXIES_FILE, "r") as f:
            proxies = [p.strip() for p in f if p.strip()]
        print(f"[+] Loaded {len(proxies)} proxies")
        return proxies
    except FileNotFoundError:
        print("[!] No proxies.txt found, using direct connection only")
        return []

def solve_captcha(api_key, site_key, url, enterprise=True):
    print(f"[*] Sending captcha to 2Captcha... (enterprise={enterprise})")
    s = requests.Session()
    params = {
        "key": api_key,
        "method": "userrecaptcha",
        "googlekey": site_key,
        "pageurl": url
    }
    if enterprise:
        params["enterprise"] = 1
        params["data-s"] = DATA_S

    resp = s.get("http://2captcha.com/in.php", params=params)
    if "OK|" not in resp.text:
        print("[!] 2Captcha in.php error:", resp.text)
        return None
    captcha_id = resp.text.split("|")[1]

    # poll for result
    for _ in range(20):
        time.sleep(5)
        r = s.get("http://2captcha.com/res.php", params={"key": api_key, "action": "get", "id": captcha_id})
        if r.text.startswith("OK|"):
            token = r.text.split("|")[1]
            print("[+] Captcha solved. Token:")
            print(token)  # log full token
            return token
        elif r.text != "CAPCHA_NOT_READY":
            print("[!] 2Captcha error:", r.text)
            return None
    print("[!] Captcha timeout")
    return None

def try_register(session, proxy=None):
    email = random_email()
    password = random_password()

    token = solve_captcha(API_KEY, SITE_KEY, PAGE_URL, enterprise=True)
    if not token:
        return None, None, "Captcha failed"

    payload = {
        "email": email,
        "password": password,
        "confirmPassword": password,
        "inviteCode": REFERRAL_CODE,
        "recaptchaToken": token
    }

    headers = {
        "Content-Type": "application/json",
        "Origin": "https://dashboard.aro.network",
        "Referer": "https://dashboard.aro.network/auth/signup",
        "User-Agent": "Mozilla/5.0"
    }

    proxies = None
    if proxy:
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}

    try:
        r = session.post(REGISTER_URL, json=payload, headers=headers, proxies=proxies, timeout=20)
        return email, password, f"{r.status_code} | {r.text[:300]}"
    except Exception as e:
        return email, password, f"Error: {e}"

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"[+] Referral limit set to {limit}")

    proxies = load_proxies()
    session = requests.Session()

    for i in range(limit):
        proxy = proxies[i % len(proxies)] if proxies else None
        email, password, result = try_register(session, proxy)
        print(f"[{proxy}] {email}:{password} -> {result}")
