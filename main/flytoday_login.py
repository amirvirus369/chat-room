#!/usr/bin/env python3

import requests
import json
import sys


def get_encrypted_phone(phone_number):
    url = "https://www.flytoday.ir/api/collect"
    
    phone_formatted = phone_number.strip()
    if phone_formatted.startswith("0"):
        phone_formatted = "+98" + phone_formatted[1:]
    elif not phone_formatted.startswith("+98"):
        phone_formatted = "+98" + phone_formatted
    
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://www.flytoday.ir",
        "referer": "https://www.flytoday.ir/sign-in",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    cookies = {
        "i18n": json.dumps({"lang": "fa", "currency": "IRR", "region": "ir"}),
        "ft_viewport_tier": "mobile"
    }
    
    payload = {"plaintext": phone_formatted}
    
    try:
        response = requests.post(url, headers=headers, cookies=cookies, json=payload, timeout=10)
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, str):
                    return data
                if "encrypted" in data:
                    return data["encrypted"]
            except json.JSONDecodeError:
                return response.text.strip().strip('"')
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def send_login_request(encrypted_phone):
    url = "https://www.flytoday.ir/api/gateway/V4/User/Login"
    
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://www.flytoday.ir",
        "referer": "https://www.flytoday.ir/sign-in",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-app": "www.flytoday.ir",
        "x-currency": "IRR",
        "x-origin": "https://www.flytoday.ir",
        "x-path": "https://www.flytoday.ir/sign-in",
    }
    
    cookies = {
        "i18n": json.dumps({"lang": "fa", "currency": "IRR", "region": "ir"}),
        "ft_viewport_tier": "mobile"
    }
    
    payload = {
        "username": encrypted_phone,
        "phoneCountryCode": "IR",
        "notificationTypes": ["Sms"]
    }
    
    try:
        response = requests.post(url, headers=headers, cookies=cookies, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "ticket" in data:
                return {
                    "success": True,
                    "ticket": data["ticket"],
                    "masked_mobile": data.get("maskedMobile", ""),
                    "expire": data.get("expireDuration", "2 minutes")
                }
        return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_otp(ticket, code):
    url = "https://www.flytoday.ir/api/gateway/V4/User/VerifyOtp"
    
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://www.flytoday.ir",
        "referer": "https://www.flytoday.ir/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-app": "www.flytoday.ir",
        "x-currency": "IRR",
        "x-origin": "https://www.flytoday.ir",
        "x-path": "https://www.flytoday.ir/",
    }
    
    cookies = {
        "i18n": json.dumps({"lang": "fa", "currency": "IRR", "region": "ir"}),
        "ft_viewport_tier": "mobile"
    }
    
    payload = {"ticket": ticket, "code": code}
    
    try:
        response = requests.post(url, headers=headers, cookies=cookies, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "token": data.get("token"), "data": data}
        elif response.status_code == 400:
            try:
                data = response.json()
                return {"success": False, "error": data.get("message", "Invalid code")}
            except:
                return {"success": False, "error": "Invalid code"}
        return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    print("=" * 60)
    print("Flytoday Login - SMS Verification")
    print("=" * 60)
    print()
    
    phone_number = sys.argv[1] if len(sys.argv) > 1 else input("Enter phone number (e.g. 09123456789): ").strip()
    
    if not phone_number:
        print("Error: Phone number cannot be empty")
        sys.exit(1)
    
    print(f"Requesting code for: {phone_number}\n")
    
    print("Step 1: Encrypting phone number...")
    encrypted_phone = get_encrypted_phone(phone_number)
    
    if not encrypted_phone:
        print("Error: Failed to encrypt phone number")
        sys.exit(1)
    
    print(f"Done: {encrypted_phone}\n")
    
    print("Step 2: Sending login request...")
    result = send_login_request(encrypted_phone)
    
    if not result["success"] or "ticket" not in result:
        print(f"Error: {result.get('error', 'No ticket received')}")
        sys.exit(1)
    
    ticket = result["ticket"]
    print(f"Done: Code sent to {result['masked_mobile']}")
    print(f"Valid for: {result['expire']}\n")
    
    print("=" * 60)
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        verification_code = input(f"Enter verification code (attempt {attempt}/{max_attempts}): ").strip()
        
        if not verification_code:
            print("Error: Code cannot be empty\n")
            continue
        
        print("Verifying...")
        verify_result = verify_otp(ticket, verification_code)
        
        if verify_result["success"]:
            print("\n" + "=" * 60)
            print("SUCCESS! Code is correct")
            if verify_result.get("token"):
                print(f"Token: {verify_result['token']}")
            print("=" * 60)
            sys.exit(0)
        else:
            print(f"FAILED: {verify_result['error']}")
            if attempt < max_attempts:
                print("Please try again\n")
            else:
                print("\n" + "=" * 60)
                print("Maximum attempts reached")
                print("=" * 60)
                sys.exit(1)


if __name__ == "__main__":
    main()