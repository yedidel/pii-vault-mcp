import asyncio
import json
import websockets
from eth_account import Account
from datetime import datetime, timezone

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
    # input() is a blocking function, so we run it in an executor thread
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
        # Step 1: Secure Handshake to identify this Vault to the Bridge
        handshake = {
            "type": "connection_init",
            "did": vault_did,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send(json.dumps(handshake))
        print("Handshake sent, waiting for Bridge requests...")

        async for message in websocket:
            data = json.loads(message)

            # Bridge acknowledges the connection
            if data.get("type") == "connection_ack":
                print("Bridge acknowledged connection. System is Online.")

            # Handling incoming payment authorization requests from Claude/Bridge
            elif data.get("type") == "payment_request":
                request_id = data.get('request_id')
                amount = data.get('amount')
                currency = data.get('currency')

                print(f"\n--- [VAULT] New Request Received: {amount} {currency} ---")

                # --- OPTION A: MANUAL APPROVAL (Default) ---
                # This will wait for you to type 'y' or 'n' in this terminal
                is_approved = await get_user_approval(amount, currency)

                # --- OPTION B: AUTO-APPROVAL (Uncomment for testing) ---
                # is_approved = True

                if is_approved:
                    response = {
                        "type": "action_approved",
                        "request_id": request_id,
                        "signature": "0x-digital-sig-of-vault-authorized"
                    }
                    print(f"--- [VAULT] Approval sent for ID: {request_id} ---")
                else:
                    response = {
                        "type": "action_rejected",
                        "request_id": request_id,
                        "reason": "User declined the transaction manually"
                    }
                    print(f"--- [VAULT] Rejection sent for ID: {request_id} ---")

                # Send the final decision back to the Bridge
                await websocket.send(json.dumps(response))

if __name__ == "__main__":
    try:
        asyncio.run(run_vault())
    except KeyboardInterrupt:
        print("\nVault shutting down...")