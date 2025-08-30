import requests
import random
import string
import sys
import json
import time
from itertools import cycle

# ================== CONFIG ==================
API_SIGNUP_URL = "https://preview-api.aro.network/api/user/signUpProd"
HAR_FILE = "dashboard.aro.network.har"

CAPTCHA_SITEKEY = "6LcQP5UrAAAAAI-Np2csPGUigYvwUCrnu7eVQRwM"
CAPTCHA_URL = "https://dashboard.aro.network"
CAPTCHA_API_KEY = "YOUR_2CAPTCHA_API_KEY"
# ============================================


def extract_data_s(har_file=HAR_FILE):
    """Extract the latest data-s token from HAR export"""
    try:
        with open(har_file, "r", encoding="utf-8") as f:
            har = json.load(f)

        for entry in har["log"]["entries"]:
            req = entry["request"]
            if "postData" in req and "text" in req["postData"]:
                text = req["postData"]["text"]
                if "data-s=" in text:
                    for part in text.split("&"):
                        if part.startswith("data-s="):
                            token = part.split("=", 1)[1]
                            print(f"[+] Extracted data-s: {token[:60]}...")
                            return token
        print("[!] No data-s found in HAR")
        return None
    except Exception as e:
        print(f"[!] Failed to read HAR: {e}")
        return None


def random_email():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@mail.com"


def random_password():
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=12))


def solve_captcha():
    print("[*] Sending captcha to 2Captcha... (enterprise=True)")
    try:
        r = requests.post("http://2captcha.com/in.php", data={
            "key": CAPTCHA_API_KEY,
            "method": "userrecaptcha",
            "googlekey": CAPTCHA_SITEKEY,
            "enterprise": 1,
            "pageurl": CAPTCHA_URL,
            "json": 1
        })
        rid = r.json().get("request")

        if r.json().get("status") != 1:
            print("[!] 2Captcha error:", r.json())
            return None

        # Wait for solution
        for _ in range(20):
            time.sleep(5)
            res = requests.get("http://2captcha.com/res.php", params={
                "key": CAPTCHA_API_KEY,
                "action": "get",
                "id": rid,
                "json": 1
            }).json()
            if res.get("status") == 1:
                print("[+] Captcha solved. Token:", res["request"][:80], "...")
                return res["request"]
        print("[!] Captcha solving timeout")
        return None
    except Exception as e:
        print("[!] 2Captcha error:", e)
        return None


def main(referral_limit):
    proxies = ["156.253.171.251:3129"]  # Example proxy
    proxy_pool = cycle(proxies)

    print(f"[+] Referral limit set to {referral_limit}")
    print(f"[+] Loaded {len(proxies)} proxies")

    data_s = extract_data_s()
    if not data_s:
        print("[!] No data-s available, aborting.")
        return

    for i in range(referral_limit):
        email = random_email()
        password = random_password()
        captcha_token = solve_captcha()
        if not captcha_token:
            print(f"[{i}] Captcha failed")
            continue

        payload = {
            "email": email,
            "password": password,
            "confirmPassword": password,
            "captcha": captcha_token,
            "data-s": data_s
        }

        proxy = next(proxy_pool)
        proxies_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}

        try:
            r = requests.post(API_SIGNUP_URL, json=payload, proxies=proxies_dict, timeout=20)
            print(f"[{proxy}] {email}:{password} -> {r.status_code} | {r.text[:200]}")
        except Exception as e:
            print(f"[{proxy}] {email}:{password} -> ERROR | {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    else:
        limit = 1
    main(limit)
