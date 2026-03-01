import argparse
import base64
import itertools
import json
import logging
import pathlib
import time

import httpx
import lxml
import yaml
from bs4 import BeautifulSoup

nyaa_url = 'https://nyaa.si'
transmission_rpc_url = "http://localhost:9091/transmission/rpc"
session_field = 'x-transmission-session-id'

logging.basicConfig(
    format='[%(asctime)s][%(levelname)s] %(message)s',
    level=logging.INFO
)

logging.getLogger('httpx').setLevel(logging.WARNING)

class TransmissionApi():
    def __init__(self):
        self.restart_session()

    def restart_session(self):
        self.session = httpx.Client(base_url=transmission_rpc_url)
        response = self.session.post(url='', data=json.dumps({
            'jsonrpc': '2.0',
            'method': 'session_get',
        }))
        self.session.headers = { session_field: response.headers[session_field] }

    def torrent_add(self, torrent_data, download_location, tries=2):
        if tries == 0:
            raise Exception('Error contacting Transmission server.')
        response:httpx.Response = self.session.post(url='', content=json.dumps({
            'jsonrpc': '2.0',
            'method': 'torrent_add',
            'params': {
                'download_dir': str(download_location),
                'metainfo': torrent_data,
            },
            'id': self.session.headers[session_field],
        }))
        if response.status_code != 200:
            self.restart_session()
            self.torrent_add(torrent_data, download_location, tries - 1)

class NyaaApi():
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def get_torrent_search_info(self, search_string):
        response = self.client.get(nyaa_url, params={'page': 'rss', 'q': search_string})
        if response.status_code == 200:
            data = BeautifulSoup(response.text, 'lxml-xml').select('rss channel item')
            data.reverse()
            return data
        else:
            logging.error(f'Could not get torrent info for: {search_string}')
            return []

    def get_torrent_file_name(self, torrent_page):
        response = self.client.get(torrent_page)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml').select_one('.torrent-file-list li').children
            return next(itertools.islice(soup, 1, None)).text.strip()
        else:
            logging.error(f'Could not get file name for torrent: {torrent_page} {response}')
            return ""

    def get_torrent_file(self, torrent_file_page):
        response = self.client.get(torrent_file_page)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode()
        else:
            logging.error(f'Could not get torrent data: {torrent_file_page}')
            return ""

transmission = TransmissionApi()
nyaa = NyaaApi()

def download_file_exists(path):
    return path.exists() or path.with_suffix(path.suffix + '.part').exists()

def download_show(search_string, download_location, episode_start=1):
    episodes = nyaa.get_torrent_search_info(search_string)[episode_start - 1:]
    for episode in episodes:
        if (download_file_exists(download_location / episode.title.text) or
            download_file_exists(download_location / nyaa.get_torrent_file_name(episode.guid.text))):
            continue
        torrent_data = nyaa.get_torrent_file(episode.link.text)
        transmission.torrent_add(torrent_data, download_location)
        logging.info(episode.title.text)
        time.sleep(1)

def download_all_shows(config):
    root = pathlib.Path(config['root'])
    for show in config['shows']:
        search_string, folder, *start = show
        start = 1 if start == [] else start[0]
        folder = root / folder
        download_show(search_string, folder, start)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='shows.yml')
    parser.add_argument('--periodic', action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()
    while True:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = yaml.load(f, Loader=yaml.Loader)
        download_all_shows(config)
        if args.periodic:
            time.sleep(60 * 60 * 24)
        else:
            break

if __name__ == '__main__':
    main()
