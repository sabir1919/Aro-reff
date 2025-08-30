import requests
import random
import string
import json
import time

# ---------------- CONFIG ----------------
with open("config.json", "r") as f:
    config = json.load(f)

REFERRAL_CODE = config.get("referral_code", "")
API_KEY = config.get("2captcha_key", "")
DATA_S = config.get("data-s", "")

SIGNUP_URL = "https://preview-api.aro.network/api/user/signUpProd"
CAPTCHA_SITEKEY = "6LcQP5UrAAAAAI-Np2csPGUigYvwUCrnu7eVQRwM"
CAPTCHA_URL = "https://dashboard.aro.network/signup"
# ----------------------------------------


# Random email generator
def random_email():
    prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{prefix}@mail.com"


# Random password generator
def random_password():
    return ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=12))


# Solve captcha using 2Captcha
def solve_captcha():
    print("[*] Sending captcha to 2Captcha... (enterprise=True)")
    try:
        r = requests.post("http://2captcha.com/in.php", data={
            "key": API_KEY,
            "method": "userrecaptcha",
            "googlekey": CAPTCHA_SITEKEY,
            "pageurl": CAPTCHA_URL,
            "enterprise": 1,
            "json": 1
        }).json()

        if r.get("status") != 1:
            print("[!] 2Captcha in.php error:", r)
            return None

        captcha_id = r["request"]

        # Wait for solution
        for _ in range(30):
            time.sleep(5)
            res = requests.get("http://2captcha.com/res.php", params={
                "key": API_KEY,
                "action": "get",
                "id": captcha_id,
                "json": 1
            }).json()

            if res.get("status") == 1:
                print("[+] Captcha solved. Token:\n", res["request"])
                return res["request"]

        print("[!] 2Captcha error: Timeout waiting for captcha")
        return None

    except Exception as e:
        print("[!] Exception while solving captcha:", e)
        return None


# Create referral account
def create_account():
    email = random_email()
    password = random_password()
    captcha_token = solve_captcha()
    if not captcha_token:
        return None, None, "Captcha failed"

    payload = {
        "email": email,
        "password": password,
        "confirmPassword": password,
        "referralCode": REFERRAL_CODE,
        "captcha": captcha_token,
        "data-s": DATA_S
    }

    try:
        r = requests.post(SIGNUP_URL, json=payload)
        return email, password, f"{r.status_code} | {r.text}"
    except Exception as e:
        return email, password, f"Error: {e}"


if __name__ == "__main__":
    limit = 1
    print(f"[+] Referral limit set to {limit}")

    for i in range(limit):
        email, password, result = create_account()
        print(f"[{i+1}] {email}:{password} -> {result}")
