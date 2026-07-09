import asyncio
import json
import websockets
import base64

# --- Professional Documentation ---
# This Mock Vault simulates the external security API.
# It handles "Encrypted" payloads by decoding Base64 data,
# simulating the decryption process that the real Vault would perform.

# This is the permanent decentralized identity (DID) representing this mock vault instance.
VAULT_DID = "did:ethr:0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A"

async def get_user_approval(decrypted_data):
    """
    Simulates user interaction on a mobile/external device.
    In a real scenario, the user would see the decrypted details on their screen.
    """
    loop = asyncio.get_event_loop()
    print(f"\n[MOCK-DECRYPTED-DATA]: {decrypted_data}")
    choice = await loop.run_in_executor(
        None,
        lambda: input("Authorize this transaction? (y/n): ")
    )
    return choice.lower() == 'y'

async def run_vault():
    uri = "ws://localhost:8081/vault-websocket"
    print(f"--- Mock Vault Online | DID: {VAULT_DID} ---")

    # Simulate scanning the QR code or deep link action in development
    print("\n[DEVELOPMENT PAIRING SIMULATION]")
    print("If you just got a QR code from the agent, extract the token from the link and paste it below.")
    print("Example Link Format: vaultapp://pair?token=YOUR_UUID_TOKEN")
    pairing_token = input("Enter pairing token (or press Enter if already paired): ").strip()

    async with websockets.connect(uri) as websocket:
        # Step 1: Protocol Handshake (Enhanced with optional pairing token)
        handshake = {
            "type": "connection_init",
            "did": VAULT_DID,
            "signature": "mock_handshake_sig"
        }

        # If the user provided a token from the QR, inject it into the connection initiation event
        if pairing_token:
            handshake["pairing_token"] = pairing_token
            print(f"Sending handshake with pairing token: {pairing_token}")
        else:
            print("Sending standard handshake (assuming already paired)...")

        await websocket.send(json.dumps(handshake))

        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "connection_ack":
                print("--- [MOCK-VAULT] Connection and authentication with Bridge established. ---")

            elif data.get("type") == "connection_error":
                print(f"--- [MOCK-VAULT ERROR] Connection rejected by Bridge: {data.get('message')} ---")
                return

            elif data.get("type") == "payment_request":
                # --- SIMULATED DECRYPTION ---
                # We treat the 'data' field as an encrypted blob.
                encrypted_blob = data.get("data")
                decrypted_bytes = base64.b64decode(encrypted_blob)
                decrypted_text = decrypted_bytes.decode('utf-8')

                req_id = data.get('request_id')
                approved = await get_user_approval(decrypted_text)

                # Step 2: Response with status logic
                response = {
                    "type": "action_approved" if approved else "action_rejected",
                    "request_id": req_id,
                    "status": "SUCCESS" if approved else "USER_DECLINED"
                }
                await websocket.send(json.dumps(response))
                print(f"Response for request {req_id} successfully dispatched back to Bridge.")

if __name__ == "__main__":
    asyncio.run(run_vault())