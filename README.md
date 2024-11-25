# yscreener
**yscreener** is a Yahoo finance screener Python client.

## Installation
Sorry, Not yet published.

```powershell
$ pip install yscreener
```

## Usage
...

```python
import asyncio
import aiohttp
from yscreener import YahooFClient

async def main():
    client = YahooFClient()
    query = 'region=="kr" && intradaymarketcap > 600B && sector=="Healthcare"'
    async with aiohttp.ClientSession() as session:
        rv = await client.screen(session, query)
        pprint(rv)
        print(len(rv))

asyncio.run(main())
```
## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Contact
For any questions or support, please reach out to me via [GitHub Issues](https://github.com/th-yoo/yscreener/issues).
