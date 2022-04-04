import datetime
import json
import pathlib
import time

import httpx
import xmltodict
import yaml

nyaa_url = 'https://nyaa.si'
transmission_rpc_url = "http://localhost:9091/transmission/rpc"
session_field = 'X-Transmission-Session-Id'

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
              'method': 'torrent-add'
            , 'arguments':
                { 'download-dir': str(download_location)
                , 'filename': torrent_url
                }
            })
        response:httpx.Response = self.session.post(url='', headers=self.headers, content=data)
        if response.status_code == 200:
            print(datetime.datetime.now(), download_location)
        elif response.status_code == 409:
            self.restart_session()
            self.torrent_add(torrent_url, download_location, tries - 1)

def ensure_list(thing):
    return thing if type(thing) is list else [thing]

def get_torrent_data_for_show(search_string):
    response = httpx.get(nyaa_url, params={'page': 'rss', 'q': search_string})
    if response.status_code == 200:
        return ensure_list(xmltodict.parse(response.text)['rss']['channel']['item'])

def download_show(search_string, download_location, episode_start=1):
    session = TransmissionApi()
    episodes = get_torrent_data_for_show(search_string)[episode_start - 1:]
    for episode in episodes:
        filepath = download_location / episode['title']
        partpath = filepath.with_suffix('.part')
        if filepath.exists() or partpath.exists():
            continue
        session.torrent_add(episode['link'], download_location)
        time.sleep(1)

def download_all_shows(config):
    root = pathlib.Path(config['root'])
    for show in config['shows']:
        search_string, folder, *start = show
        start = 1 if start == [] else start[0]
        folder = root / folder
        download_show(search_string, folder, start)

if __name__ == '__main__':
    with open('shows.yml', 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.Loader)
    download_all_shows(config)
