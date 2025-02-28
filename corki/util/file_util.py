import traceback

import requests
from loguru import logger
from tqdm import tqdm


def download_file(file_path, url):
    try:
        with requests.get(url=url, stream=True) as img_response:
            file_size = int(img_response.headers.get('Content-Length', 0))
            with open(file_path, 'wb') as fp, tqdm(total=file_size, unit='B', unit_scale=True, desc=file_path) as pbar:
                for chunk in img_response.iter_content(chunk_size=1024):
                    if chunk:
                        fp.write(chunk)
                        pbar.update(len(chunk))
    except Exception:
        logger.error(traceback.format_exc())
        return False, 'url for download error: {}'.format(url)
    return True, file_path
