from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="The Guardian Mock Service")

# Mock database of authorized Agent DIDs
authorized_agents = {
    "agent-123": {"status": "verified", "trust_level": "high"},
    "trusted-bot-1": {"status": "verified", "trust_level": "medium"}
}

class ReportRequest(BaseModel):
    domain: str
    result: str
    requestId: str

@app.get("/v1/authenticate/agent")
async def auth_agent(did: str):
    """
    Project C logic: Verify if the agent identity (DID) is valid.
    """
    print(f"--- [GUARDIAN] Authenticating Agent DID: {did} ---")
    return authorized_agents.get(did, {"status": "unauthorized", "trust_level": "none"})

@app.post("/v1/report")
async def report_action(report: ReportRequest):
    """
    Step 2: Receiving reports to update reputation algorithms.
    """
    print(f"--- [GUARDIAN] Report Received for {report.domain} ---")
    return {"status": "accepted"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)