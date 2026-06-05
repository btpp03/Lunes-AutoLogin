"""Lunes Host auto login - curl + cookie keepalive"""
import os, sys, time, requests

UA = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.114 Mobile Safari/537.36"

def tg_send(text, token="", chat_id=""):
    token, chat_id = (token or "").strip(), (chat_id or "").strip()
    if not token or not chat_id: return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, timeout=15)
    except Exception as e: print(f"TG send failed: {e}")

def build_accounts():
    batch = (os.getenv("ACCOUNTS_BATCH") or "").strip()
    if not batch: raise RuntimeError("Missing ACCOUNTS_BATCH")
    accounts = []
    for raw in batch.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"): continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            accounts.append({
                "email": parts[0],
                "cf_clearance": parts[1],
                "session": parts[2],
                "tg_token": parts[3] if len(parts) > 3 else "",
                "tg_chat": parts[4] if len(parts) > 4 else "",
            })
    return accounts

def keepalive(email, cf_clearance, session):
    cookies = f"cf_clearance={cf_clearance}; session={session}"
    headers = {"Cookie": cookies, "User-Agent": UA}
    results = []
    
    # 1. Visit dashboard
    try:
        r = requests.get("https://betadash.lunes.host/", headers=headers, timeout=30)
        if "profile-header" in r.text or "servers online" in r.text:
            results.append("dashboard OK")
            print(f"  Dashboard OK")
        elif "login" in r.text.lower() or r.status_code == 401:
            results.append("cookie expired")
            print(f"  Cookie EXPIRED")
            return False, results
        else:
            results.append(f"dashboard unknown ({r.status_code})")
            print(f"  Dashboard: status={r.status_code}")
    except Exception as e:
        results.append(f"dashboard error: {e}")
        print(f"  Dashboard error: {e}")
    
    # 2. Visit server pages
    for sid in ["51160", "60685"]:
        try:
            r = requests.get(f"https://betadash.lunes.host/servers/{sid}", headers=headers, timeout=30)
            if r.status_code == 200 and "Server" in r.text:
                results.append(f"server {sid} OK")
                print(f"  Server {sid} OK")
            elif r.status_code == 404:
                # Not this account's server, that's fine
                results.append(f"server {sid} skip (404)")
                print(f"  Server {sid}: not owned")
            else:
                results.append(f"server {sid} status={r.status_code}")
                print(f"  Server {sid}: status={r.status_code}")
        except Exception as e:
            results.append(f"server {sid} error: {e}")
            print(f"  Server {sid} error: {e}")
    
    return "cookie expired" not in results, results

def main():
    accounts = build_accounts()
    ok, fail = 0, 0
    results = []
    for i, acc in enumerate(accounts, 1):
        email = acc["email"]
        print(f"\n{'='*50}\n[{i}/{len(accounts)}] {email}\n{'='*50}")
        success, detail = keepalive(email, acc["cf_clearance"], acc["session"])
        if success:
            ok += 1
            results.append(f"OK {email}: {', '.join(detail)}")
        else:
            fail += 1
            results.append(f"FAIL {email}: {', '.join(detail)}")
        tg_send(f"{'✅' if success else '❌'} Lunes {'保活成功' if success else 'Cookie过期'}\n{email}\n{', '.join(detail)}",
            acc.get("tg_token",""), acc.get("tg_chat",""))
        if i < len(accounts): time.sleep(3)
    
    summary = f"Lunes 续期: {ok}/{len(accounts)} 成功\n" + "\n".join(results)
    print(f"\n{summary}")
    for acc in accounts:
        if acc.get("tg_token") and acc.get("tg_chat"):
            tg_send(summary, acc["tg_token"], acc["tg_chat"]); break
    if fail == len(accounts): sys.exit(1)

if __name__ == "__main__":
    main()
