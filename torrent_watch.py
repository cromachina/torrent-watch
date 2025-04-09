import argparse
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
session_field = 'X-Transmission-Session-Id'

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
        response = self.session.post(url='', data={'method': 'session-get'})
        self.headers = {session_field: response.headers[session_field]}

    def torrent_add(self, torrent_url, download_location, tries=2):
        if tries == 0:
            raise Exception('Error contacting Transmission server.')
        data = json.dumps({
            'method': 'torrent-add',
            'arguments': {
                'download-dir': str(download_location),
                'filename': torrent_url
            }
        })
        response:httpx.Response = self.session.post(url='', headers=self.headers, content=data)
        if response.status_code != 200:
            self.restart_session()
            self.torrent_add(torrent_url, download_location, tries - 1)

class NyaaApi():
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def get_torrent_data_for_show(self, search_string):
        response = self.client.get(nyaa_url, params={'page': 'rss', 'q': search_string})
        if response.status_code == 200:
            data = BeautifulSoup(response.text, 'lxml-xml').select('rss channel item')
            data.reverse()
            return data

    def get_file_name_for_torrent(self, torrent_page):
        response = self.client.get(torrent_page)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml').select_one('.torrent-file-list li').children
            return next(itertools.islice(soup, 1, None)).text.strip()

transmission = TransmissionApi()
nyaa = NyaaApi()

def download_file_exists(path):
    return path.exists() or path.with_suffix(path.suffix + '.part').exists()

def download_show(search_string, download_location, episode_start=1):
    episodes = nyaa.get_torrent_data_for_show(search_string)[episode_start - 1:]
    for episode in episodes:
        if (download_file_exists(download_location / episode.title.text) or
            download_file_exists(download_location / nyaa.get_file_name_for_torrent(episode.guid.text))):
            continue
        transmission.torrent_add(episode.link.text, download_location)
        logging.info(episode.title.text)
        time.sleep(1)

def download_all_shows(config):
    root = pathlib.Path(config['root'])
    for show in config['shows']:
        search_string, folder, *start = show
        start = 1 if start == [] else start[0]
        folder = root / folder
        download_show(search_string, folder, start)

if __name__ == '__main__':
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
