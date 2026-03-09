from fastapi import FastAPI
import main
import models

app=FastAPI()
@app.get("/")
async def root():
    return {"message": "Adapter server running"}
@app.post("/action/")
async def send_action(action:models.ActionRequestModel):
    response= main.send_action(action)
    return {
        "requestId": response.request_id,
        "status": response.status,
        "description": response.description
    }

@app.get("/status/{request_id}")
async def getStatus(request_id: str):
    response= main.get_status(request_id)
    return {
        "requestId": response.request_id,
        "status": response.status,
        "resultData": response.result_data
    }
