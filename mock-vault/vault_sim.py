import asyncio
import json
import websockets
import base64


# --- Professional Documentation ---
# This Mock Vault simulates the external security API.
# It handles "Encrypted" payloads by decoding Base64 data,
# simulating the decryption process that the real Vault would perform.

VAULT_DID = "did:ethr:0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A"

async def get_user_approval(decrypted_data):
    """
    Simulates user interaction.
    In a real scenario, the user would see the decrypted details on their device.
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

    async with websockets.connect(uri) as websocket:
        # Step 1: Protocol Handshake
        handshake = {
            "type": "connection_init",
            "did": VAULT_DID,
            "signature": "mock_handshake_sig"
        }
        await websocket.send(json.dumps(handshake))

        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "connection_ack":
                print("Connection to Bridge established.")

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
                print(f"Response for {req_id} sent.")

if __name__ == "__main__":
    asyncio.run(run_vault())