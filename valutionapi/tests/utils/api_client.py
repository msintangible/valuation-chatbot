from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


class APIClient:
    def __init__(self, app: FastAPI, base_url: str = "http://testserver"):
        self.base_url = base_url
        self.transport = ASGITransport(app=app)

    async def get(self, endpoint: str, headers: dict | None = None):
        async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
            return await client.get(endpoint, headers=headers or {})

    async def post(self, endpoint: str, json: dict | None = None, headers: dict | None = None):
        async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
            return await client.post(endpoint, json=json or {}, headers=headers or {})
