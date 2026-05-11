import asyncio
import json
import websockets
from eth_account import Account
from eth_account.messages import encode_defunct
from datetime import datetime, timezone

# --- Professional Documentation ---
# Helper function to sign the connection handshake.
# It signs a unique string containing the timestamp using the Private Key.
def sign_handshake(timestamp, p_key):
    message_text = f"vault_auth_{timestamp}"
    ms_encoded = encode_defunct(text=message_text)
    signed_message = Account.sign_message(ms_encoded, private_key=p_key)
    return signed_message.signature.hex()

# Vault Identity - Based on a simulated Ethereum private key
private_key = "0x" + "1" * 64
account = Account.from_key(private_key)
vault_did = f"did:ethr:{account.address}"

async def get_user_approval(amount, currency):
    """
    Waits for manual user input in the terminal without blocking
    the asynchronous WebSocket connection.
    """
    loop = asyncio.get_event_loop()
    choice = await loop.run_in_executor(
        None,
        lambda: input(f"\n[VAULT] Action Required: Authorize payment of {amount} {currency}? (y/n): ")
    )
    return choice.lower() == 'y'

async def run_vault():
    # The Bridge WebSocket endpoint
    uri = "ws://localhost:8081/vault-websocket"
    print(f"--- Mock Vault Started | DID: {vault_did} ---")

    async with websockets.connect(uri) as websocket:
        # --- SECURE HANDSHAKE STEP ---
        # We generate the timestamp and signature RIGHT BEFORE sending
        current_ts = datetime.now(timezone.utc).isoformat()
        handshake_signature = sign_handshake(current_ts, private_key)

        handshake = {
            "type": "connection_init",
            "did": vault_did,
            "timestamp": current_ts,
            "signature": handshake_signature  # Now includes cryptographic proof
        }
        print(f"DEBUG: Sending Handshake -> {json.dumps(handshake, indent=2)}")
        await websocket.send(json.dumps(handshake))
        print(f"Secure handshake sent with signature, waiting for Bridge requests...")

        async for message in websocket:
            data = json.loads(message)

            # --- HEARTBEAT HANDLING ---
            if data.get("type") == "heartbeat":
                continue

            # Bridge acknowledges the connection
            if data.get("type") == "connection_ack":
                print("Bridge acknowledged connection. System is Online.")

            # Handling incoming payment authorization requests
            elif data.get("type") == "payment_request":
                request_id = data.get('request_id')
                amount = data.get('amount')
                currency = data.get('currency')

                print(f"\n--- [VAULT] New Request Received: {amount} {currency} ---")

                # Manual approval logic (untouched)
                is_approved = await get_user_approval(amount, currency)

                if is_approved:
                    response = {
                        "type": "action_approved",
                        "request_id": request_id,
                        # Note: In the future, this signature will also be dynamic (E2EE)
                        "signature": "0x-authorized-by-vault"
                    }
                    print(f"--- [VAULT] Approval sent for ID: {request_id} ---")
                else:
                    response = {
                        "type": "action_rejected",
                        "request_id": request_id,
                        "reason": "User declined the transaction manually"
                    }
                    print(f"--- [VAULT] Rejection sent for ID: {request_id} ---")

                await websocket.send(json.dumps(response))

if __name__ == "__main__":
    try:
        asyncio.run(run_vault())
    except KeyboardInterrupt:
        print("\nVault shutting down...")