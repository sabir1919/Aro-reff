import requests
import random
import string
import sys
import json
import time
from itertools import cycle


def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print("[!] Failed to read config.json:", e)
        sys.exit(1)


def random_email():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + "@mail.com"


def random_password():
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=12))


def solve_captcha(cfg):
    print("[*] Sending captcha to 2Captcha... (enterprise=True)")
    try:
        r = requests.post("http://2captcha.com/in.php", data={
            "key": cfg["captcha_api_key"],
            "method": "userrecaptcha",
            "googlekey": cfg["captcha_sitekey"],
            "enterprise": 1,
            "pageurl": cfg["captcha_url"],
            "json": 1
        })
        rid = r.json().get("request")

        if r.json().get("status") != 1:
            print("[!] 2Captcha error:", r.json())
            return None

        # Poll result
        for _ in range(20):
            time.sleep(5)
            res = requests.get("http://2captcha.com/res.php", params={
                "key": cfg["captcha_api_key"],
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
    cfg = load_config()
    proxies = cfg.get("proxies", [])
    proxy_pool = cycle(proxies) if proxies else cycle([None])

    print(f"[+] Referral limit set to {referral_limit}")
    print(f"[+] Loaded {len(proxies)} proxies")

    data_s = cfg.get("data_s")
    if not data_s:
        print("[!] No data-s in config.json, aborting.")
        return

    for i in range(referral_limit):
        email = random_email()
        password = random_password()
        captcha_token = solve_captcha(cfg)
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
        proxies_dict = None
        if proxy:
            proxies_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}

        try:
            r = requests.post(cfg["api_signup_url"], json=payload, proxies=proxies_dict, timeout=20)
            print(f"[{proxy}] {email}:{password} -> {r.status_code} | {r.text[:200]}")
        except Exception as e:
            print(f"[{proxy}] {email}:{password} -> ERROR | {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    else:
        limit = 1
    main(limit)
