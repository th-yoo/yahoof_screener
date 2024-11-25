import os
import asyncio
import hashlib

import aiohttp
from urllib.parse import urlparse, urljoin
#from lxml import html

# https://stackoverflow.com/questions/45600579/asyncio-event-loop-is-closed-when-getting-loop
import platform
if platform.system()=='Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# TODO(?): aiofiles

files_updated = (
    '_consts.py',
    '_header_generator.py'
)

dir_to_download = os.path.join('.', 'crawlee')

async def calculate_checksum(data):
    """Calculate the SHA256 checksum of the given data."""
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()

async def download_file(session, url):
    """Download a file from the URL and return its content."""
    async with session.get(url) as response:
        response.raise_for_status()  # Raise an error for bad responses
        return await response.read()

# Define the string containing your class definition
file_docs = """def docs_group(group_name):
    def decorator(cls):
        # This decorator does nothing, just returns the class
        return cls
    return decorator
"""

file__types = """class HttpHeaders(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
"""

file_typing = """TYPE_CHECKING=False"""

# crawlee
# ├── _types.py
# └── fingerprint_suite
#     ├── _consts.py
#     ├── _header_generator.py
#     └── typing.py

async def main():
    #base_url = 'https://raw.githubusercontent.com/apify/crawlee-python/refs/heads/master/src/crawlee/'
    #base_url = 'https://raw.githubusercontent.com/apify/crawlee-python/refs/heads/master/src/'
    base_url = 'https://raw.githubusercontent.com/apify/crawlee-python/refs/heads/master/src/crawlee/fingerprint_suite/'
    
#    response_text = await fetch_data(url)
#    tree = html.fromstring(response_text)
#    
#    # Locate the table
#    table = tree.xpath('//table[starts-with(@summary, "업종별")]')[0]
#    rows = table.xpath('.//tr')
#
#    origin = get_origin(url)
#    sectors = await asyncio.gather(*(fetch_row_data(row, origin) for row in rows))
#    sectors = [sector for sector in sectors if sector is not None]
#
##    for s in sectors:
##        print(s)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for file_name in files_updated:
            url = urljoin(base_url+'/', file_name)
            #print(url)
            tasks.append(download_file(session, url))

        file_contents = await asyncio.gather(*tasks)

        # docs
        _utils_dir = os.path.join(dir_to_download, '_utils')
        os.makedirs(_utils_dir, exist_ok=True)
        docs_path = os.path.join(_utils_dir, 'docs.py')
        if not os.path.exists(docs_path):
            with open(docs_path, 'w') as file:
                file.write(file_docs)

        dir_path = os.path.join(dir_to_download, 'fingerprint_suite')
        os.makedirs(dir_path, exist_ok=True)

        _types_path = os.path.join(dir_to_download, '_types.py')
        if not os.path.exists(_types_path):
            with open(_types_path, 'w') as file:
                file.write(file__types)

        typing_path = os.path.join(dir_path, 'typing.py')
        if not os.path.exists(_types_path):
            with open(_types_path, 'w') as file:
                file.write(file_typing)

        for file_name, new_content in zip(files_updated, file_contents):
            new_checksum = await calculate_checksum(new_content)
            old_checksum = None

            old_file_path = os.path.join(dir_path, file_name)
            if os.path.exists(old_file_path):
                with open(old_file_path, 'rb') as f:
                    old_content = f.read()
                    old_checksum = await calculate_checksum(old_content)

                    if old_checksum == new_checksum:
                        print(f'{file_name} is up to date.')
                        continue
            with open(old_file_path, 'wb') as f:
                f.write(new_content)
                print(f'{file_name} has been updated.')

if __name__ == '__main__':
    asyncio.run(main())
