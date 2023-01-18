import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import json
import logging
from discord.ext import commands

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('./logs/spotify.log')
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('[%(asctime)s] %(name)s :: %(levelname)-8s :: %(funcName)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
file_handler.setFormatter(file_format)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_format = logging.Formatter('[%(asctime)s] %(name)-25s :: %(levelname)-8s :: %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_format)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

with open('authentication/config.json') as fh:
    config = json.load(fh)

class Spotify:

    result = None
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=config["spotify"]["cid"],
                                                           client_secret=config["spotify"]["secret"]))
    
    @classmethod
    def verifyUrl(cls, url):
        """
        Verify Url.
        Expect spotify playlist url.
        """

        logger.info(f'Verify Url: {url}')
        try:
            cls.result = cls.sp.playlist_items(url)
        except Exception:
            logger.error(f'Spotify playlist url Invalid (link)')
            raise commands.CommandError("Spotify playlist url Invalid (link)")
        
        return url

    @classmethod
    def fetchPlaylist(cls):
        """
        Fetch spotify playlist.
        Return song url.
        """

        while True:
            try:
                for song in cls.result['items']:
                    temp = f"{song['track']['name']} - {song['track']['album']['artists'][0]['name']}"
                    yield temp
            except StopIteration:
                logger.warning('End of spotify playlist')

    
if __name__ == '__main__':
    data = Spotify.fetchPlaylist("https://open.spotify.com/playlist/37i9dQZF1DWVMjQ4irK5mi?si=86f226d5a8f346b7")
    print(next(data))
    print(next(data))
