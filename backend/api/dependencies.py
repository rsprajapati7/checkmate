from fastapi import Header, HTTPException
async def verify_api_key(x_api_key: str = Header(...)):
    if not x_api_key:
        raise HTTPException(status_code=403, detail="API Key missing")
