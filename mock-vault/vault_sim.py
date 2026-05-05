import asyncio
import json
import websockets
from eth_account import Account
from datetime import datetime,timezone

# 1. יצירת זהות לכספת (מפתח פרטי וכתובת DID)
# בייצור אמיתי זה נשמר בכספת, כאן אנחנו מייצרים "על המקום" לצורך הבדיקה
private_key = "0x" + "1" * 64 # מפתח דמה
account = Account.from_key(private_key)
vault_did = f"did:ethr:{account.address}"

async def run_vault():
    # כתובת ה-Bridge שלך (וודאי שה-Port תואם למה שהגדרת בקוטילין)
    uri = "ws://localhost:8080/vault-websocket" 
    
    print(f"--- Starting Mock Vault ({vault_did}) ---")
    
    async with websockets.connect(uri) as websocket:
        # 2. הכנת הודעת Handshake (לפי המדריך של הכספת)
        handshake = {
            "type": "connection_init",
            "did": vault_did,
            "vault_public_key": "0x04abc123456789...", # מפתח ציבורי דמה
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        
        # חתימה על ההודעה (דימוי של הוכחת זהות)
        msg_to_sign = json.dumps(handshake)
        # כאן בדרך כלל מבצעים חתימה אמיתית, כרגע נשלח סימן חתימה דמה
        handshake["signature"] = "0x-mock-signature" 

        print(f"Sending handshake to Bridge...")
        await websocket.send(json.dumps(handshake))

        # 3. לולאת האזנה לבקשות מה-Bridge
        print("Waiting for ActionRequests from Bridge...")
        async for message in websocket:
            data = json.loads(message)
            print(f"\nReceived request: {data['type']}")
            
            if data['type'] == 'payment':
                print(f"Details: {data['payment_details']['amount']} {data['payment_details']['currency']} to {data['payment_details']['merchant_name']}")
                
                # 4. שליחת תגובה (ActionResponse)
                response = {
                    "request_id": data["request_id"],
                    "status": "approved",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "vault_did": vault_did
                }
                await websocket.send(json.dumps(response))
                print(f"Sent approval for request {data['request_id']}")

if __name__ == "__main__":
    asyncio.run(run_vault())