import asyncio
import json
from aiohttp import ClientSession
from urllib.parse import urlparse, urljoin

# https://stackoverflow.com/questions/45600579/asyncio-event-loop-is-closed-when-getting-loop
import platform
if platform.system()=='Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .crawlee.fingerprint_suite._header_generator import HeaderGenerator

header_gen = HeaderGenerator()

import random

from .screener_expr import parse_screener_expr

class YahooFClient:
    MAX_ITEM = 250

    def __init__(self):
        browser_type = random.choice(['chromium', 'firefox', 'webkit'])
        common_headers = header_gen.get_common_headers()
        ua_header = header_gen.get_user_agent_header(
            browser_type=browser_type
        )
        sec_headers = header_gen.get_sec_ch_ua_headers(
            browser_type=browser_type
        ) 
        self._headers = {
            **common_headers,
            **ua_header,
            **sec_headers,
            #"Origin": "https://finance.yahoo.com",
            #"Referrer Policy": "no-referrer-when-downgrade",
        }
        self._cookie = None
        self._crumb = None

    async def cookie(self, session):
        # TODO: if the session doesn't have the cookie...
        if self._cookie:
            return self._cookie
        async with session.get(
            "https://fc.yahoo.com",
            headers=self._headers,
            allow_redirects=True
        ) as response:
            cookies = response.cookies
            if not cookies:
                raise Exception("Failed to obtain Yahoo auth cookie.")
            self._cookie = list(cookies.values())[0]
            return self._cookie

    async def crumb(self, session):
        if self._crumb:
            return self._crumb
        async with session.get(
            "https://query1.finance.yahoo.com/v1/test/getcrumb",
            headers=self._headers,
            # We don't need this
            cookies={self._cookie.key: self._cookie.value},
            allow_redirects=True
        ) as response:
            crumb = await response.text()
            if crumb is None:
                raise Exception("Failed to retrieve Yahoo crumb.")
            self._crumb = crumb
            return crumb

    # JSON.stringify(o) != json.dumps(d)
    # JSON.stringify(o) == json.dumps(d, ensure_ascii=False)
    def _json_request(self, payload):
        headers = {**self._headers, 'Content-Type': 'application/json'}
        payload = json.dumps(payload, ensure_ascii=False)
        return headers, payload

#    async def screen(self, session, screener_expr, opt={}):
#        await self.cookie(session)
#        crumb = await self.crumb(session)
#
#        url = f"https://query1.finance.yahoo.com/v1/finance/screener?formatted=true&useRecordsResponse=true&lang=en-US&crumb={crumb}"
#
#        query = parse_screener_expr(screener_expr)
#        print(query)
#        default_payload = {
#            "quoteType": "equity",
#            "sortField": "intradaymarketcap",
#            "sortType": "desc",
#            "query": query,
#        }
#
#        n_records = -1
#        n_left = 0
#        offset = 0
#        size = self.MAX_ITEM
#
#        rv = []
#
#        while True:
#            payload = {**default_payload, **opt, "offset": offset, "size": size}
#            headers, data = self._json_request(payload)
#
#            async with session.post(
#                url,
#                headers=headers,
#                data=data
#            ) as resp:
#                resp.raise_for_status()
#                resp_body = await resp.json()
#                error = resp_body.get('finance').get('error')
#                if error:
#                    raise Exception(f'Failed to retrieve data: {error}')
#
#                if n_records < 0:
#                    n_records = resp_body.get('finance').get('result')[0].get('total')
#                    n_left = n_records
#
#                stock_infos = resp_body.get('finance').get('result')[0].get('records')
#                rv.extend(stock_infos)
#
#                count = resp_body.get('finance').get('result')[0].get('count')
#                n_left -= count
#                if n_left <= 0:
#                    break
#                size = min(n_left, self.MAX_ITEM)
#                offset += count
#
#        return rv

    async def screen(self, session, screener_expr, opt={}):
        await self.cookie(session)
        crumb = await self.crumb(session)

        url = f"https://query1.finance.yahoo.com/v1/finance/screener?formatted=true&useRecordsResponse=true&lang=en-US&crumb={crumb}"

        query = parse_screener_expr(screener_expr)
        #print(query)
        default_payload = {
            "quoteType": "equity",
            "sortField": "intradaymarketcap",
            "sortType": "desc",
            "query": query,
        }

        offset = 0
        size = self.MAX_ITEM

        payload = {**default_payload, **opt, "offset": offset, "size": size}
        headers, data = self._json_request(payload)

        rv, n_records = await self._fetch(
            session,
            url,
            headers,
            data,
            total = True
        )

        #print('n_records', n_records)

        count = len(rv)
        n_left = n_records - count
        if n_left <= 0:
            return rv

        offset = count
        size = min(n_left, self.MAX_ITEM)
        while n_left > 0:
            payload = {**default_payload, **opt, "offset": offset, "size": size}
            headers, data = self._json_request(payload)

            stock_infos = await self._fetch(
                session,
                url,
                headers,
                data,
            )
            rv.extend(stock_infos)
            count = len(stock_infos)
            n_left -= count
            offset += count
            size = min(n_left, self.MAX_ITEM)
        return rv

#
# parallel version but rate limit may cause failure
# https://www.reddit.com/r/learnpython/comments/121oq0c/yahoo_fin_request_limit/
#
#    async def screen_parallel(self, session, screener_expr, opt={}):
#        await self.cookie(session)
#        crumb = await self.crumb(session)
#
#        url = f"https://query1.finance.yahoo.com/v1/finance/screener?formatted=true&useRecordsResponse=true&lang=en-US&crumb={crumb}"
#
#        query = parse_screener_expr(screener_expr)
#        print(query)
#        default_payload = {
#            "quoteType": "equity",
#            "sortField": "intradaymarketcap",
#            "sortType": "desc",
#            "query": query,
#        }
#
#        n_records = -1
#        n_left = 0
#        offset = 0
#        size = self.MAX_ITEM
#
#        #rv = []
#
#        payload = {**default_payload, **opt, "offset": offset, "size": size}
#        headers, data = self._json_request(payload)
#        rv, n_records = await self._fetch(
#            session,
#            url,
#            headers,
#            data,
#            total=True
#        )
#
#        #print('n_records', n_records)
#
#        offset = len(rv)
#        n_left = n_records - offset
#        if not n_left:
#            return rv
#
#        tasks = []
#        rounds = int((n_left+self.MAX_ITEM-1)/self.MAX_ITEM)
#        #print('rounds', rounds)
#
#        #size = min(self.MAX_ITEM, n_left)
#        for i in range(rounds):
#            #print('offset', offset, 'size', size)
#            payload = {**default_payload, **opt, "offset": offset, "size": size}
#            headers, data = self._json_request(payload)
#            tasks.append(self._fetch(session, url, headers, data))
#
#            offset += self.MAX_ITEM
#
#        results = await asyncio.gather(*tasks)
#        for r in results:
#            rv.extend(r)
#        return rv

    async def _fetch(self, session, url, headers, data, total=False):
        async with session.post(
            url,
            headers=headers,
            data=data
        ) as resp:
            resp.raise_for_status()
            resp_body = await resp.json()
            error = resp_body.get('finance').get('error')
            if error:
                raise Exception(f'Failed to retrieve data: {error}')

            stock_infos = resp_body.get('finance').get('result')[0].get('records')
            #rv.extend(stock_infos)
            #count = resp_body.get('finance').get('result')[0].get('count')

            if total:
                n_records = resp_body.get('finance').get('result')[0].get('total')
                return stock_infos, n_records

            return stock_infos


if __name__ == '__main__':
    from pprint import pprint

    async def main():
        client = YahooFClient()
        #query = 'region=="kr" && sector=="Healthcare" && industry=="Drug Manufacturers—General"'
        query = 'region=="kr" && industry=="Drug Manufacturers—General"'
        #query = 'region=="kr" && sector=="Healthcare"'
        #query = 'region=="kr" && intradaymarketcap > 600B'
        #query = 'region=="kr" && intradaymarketcap > 300B'
        async with ClientSession() as session:
            rv = await client.screen(session, query)
            pprint(rv)
            print(len(rv))

    asyncio.run(main())

