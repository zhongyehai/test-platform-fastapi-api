from fastapi import Request
from fastapi.responses import Response
from prometheus_client import generate_latest


async def metrics(request: Request):
    return Response(generate_latest(), media_type="text/plain")
