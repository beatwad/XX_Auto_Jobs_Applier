import asyncio

import aiohttp
import yaml

# Прокси-сервер (замените на ваш прокси)
with open("data_folder/secrets/secrets.yaml", "r") as file:
    proxy = yaml.safe_load(file)["llm_proxy"][0]

# Тестируемый URL
url = "http://httpbin.org/ip"


async def test_proxy(session):
    try:
        async with session.get(url, proxy=proxy, timeout=5) as response:
            return await response.json()
    except Exception as e:
        return f"Error: {e}"


async def test_concurrent_connections():
    async with aiohttp.ClientSession() as session:
        tasks = [test_proxy(session) for _ in range(500)]
        return await asyncio.gather(*tasks)


if __name__ == "__main__":
    results = asyncio.run(test_concurrent_connections())
    for i, result in enumerate(results):
        print(f"Connection {i + 1}: {result}")
