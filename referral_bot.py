import requests
import random
import string
import sys
import time

# -----------------------------
# CONFIG
# -----------------------------
API_KEY = "YOUR_2CAPTCHA_API_KEY"   # <-- put your 2Captcha key here
SITE_KEY = "6LcQP5UrAAAAAI-Np2csPGUigYvwUCrnu7eVQRwM"  # from signup form
PAGE_URL = "https://dashboard.aro.network/"
REGISTER_URL = "https://preview-api.aro.network/api/user/signUpProd"
REFERRAL_CODE = "GJMDVK"
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

def solve_captcha(api_key, site_key, url, enterprise=False):
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
        params["version"] = "v3"

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
            print("[+] Captcha solved")
            return r.text.split("|")[1]
        elif r.text != "CAPCHA_NOT_READY":
            print("[!] 2Captcha error:", r.text)
            return None
    print("[!] Captcha timeout")
    return None

def try_register(session, proxy=None, enterprise=False):
    email = random_email()
    password = random_password()

    token = solve_captcha(API_KEY, SITE_KEY, PAGE_URL, enterprise=enterprise)
    if not token:
        return None, None, "Captcha failed"

    payload = {
        "email": email,
        "password": password,
        "confirmPassword": password,
        "inviteCode": REFERRAL_CODE,
        "recaptchaToken": token   # <-- must match HAR
    }

    headers = {
        "Content-Type": "application/json",
        "Origin": "https://dashboard.aro.network",
        "Referer": "https://dashboard.aro.network/",
        "User-Agent": "Mozilla/5.0"
    }

    proxies = None
    if proxy:
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}

    try:
        r = session.post(REGISTER_URL, json=payload, headers=headers, proxies=proxies, timeout=20)
        return email, password, f"{r.status_code} | {r.text[:200]}"
    except Exception as e:
        return email, password, f"Error: {e}"

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    enterprise = "--enterprise" in sys.argv
    print(f"[+] Referral limit set to {limit} (enterprise={enterprise})")

    proxies = load_proxies()
    session = requests.Session()

    for i in range(limit):
        proxy = proxies[i % len(proxies)] if proxies else None
        email, password, result = try_register(session, proxy, enterprise=enterprise)
        print(f"[{proxy}] {email}:{password} -> {result}")
