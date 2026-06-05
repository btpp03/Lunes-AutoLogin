"""Lunes Host 自动登录 - undetected-chromedriver"""
import os, sys, time, requests

LOGIN_URL = "https://betadash.lunes.host/login"

def tg_send(text, token="", chat_id=""):
    token, chat_id = (token or "").strip(), (chat_id or "").strip()
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=15,
        )
    except Exception as e:
        print(f"TG send failed: {e}")

def build_accounts():
    batch = (os.getenv("ACCOUNTS_BATCH") or "").strip()
    if not batch:
        raise RuntimeError("Missing ACCOUNTS_BATCH")
    accounts = []
    for raw in batch.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            accounts.append({
                "email": parts[0], "password": parts[1],
                "tg_token": parts[2] if len(parts) > 2 else "",
                "tg_chat": parts[3] if len(parts) > 3 else "",
            })
    return accounts

def login_one(email, password):
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options, headless=True)
    
    try:
        print(f"Opening login page: {email}")
        driver.get(LOGIN_URL)
        time.sleep(5)
        
        # Wait for form
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#email")))
        
        email_el = driver.find_element(By.CSS_SELECTOR, "#email")
        email_el.clear()
        email_el.send_keys(email)
        
        pass_el = driver.find_element(By.CSS_SELECTOR, "#password")
        pass_el.clear()
        pass_el.send_keys(password)
        
        # Wait for Turnstile
        print("Waiting for Turnstile...")
        for i in range(30):
            time.sleep(2)
            try:
                val = driver.execute_script('return document.querySelector("[name=cf-turnstile-response]")?.value || ""')
                if val:
                    print(f"Turnstile solved! ({i*2}s)")
                    break
            except:
                pass
        else:
            print("Turnstile timeout, trying submit anyway...")
        
        # Submit
        btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        btn.click()
        time.sleep(5)
        
        url = driver.current_url
        if "/login" not in url:
            print(f"Login success: {url}")
            for sid in ["51160", "60685"]:
                try:
                    driver.get(f"https://betadash.lunes.host/servers/{sid}")
                    time.sleep(3)
                    print(f"  Visited server {sid}")
                except Exception as e:
                    print(f"  Server {sid}: {e}")
            return True
        else:
            print(f"Login failed, still on: {url}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()

def main():
    accounts = build_accounts()
    ok, fail = 0, 0
    results = []
    
    for i, acc in enumerate(accounts, 1):
        email = acc["email"]
        print(f"\n{'='*50}")
        print(f"[{i}/{len(accounts)}] {email}")
        print(f"{'='*50}")
        
        success = login_one(email, acc["password"])
        if success:
            ok += 1
            results.append(f"OK {email}")
        else:
            fail += 1
            results.append(f"FAIL {email}")
        
        tg_send(
            f"{'✅' if success else '❌'} Lunes {'登录成功' if success else '登录失败'}\n{email}",
            acc.get("tg_token", ""), acc.get("tg_chat", "")
        )
        if i < len(accounts):
            time.sleep(5)
    
    summary = f"Lunes 续期: {ok}/{len(accounts)} 成功\n" + "\n".join(results)
    print(f"\n{summary}")
    for acc in accounts:
        if acc.get("tg_token") and acc.get("tg_chat"):
            tg_send(summary, acc["tg_token"], acc["tg_chat"])
            break
    
    if fail == len(accounts):
        sys.exit(1)

if __name__ == "__main__":
    main()
