import asyncio
import itertools
import random
import re
import time
import logging
from async_timeout import timeout
import httpx
from bs4 import BeautifulSoup

import discord
from discord.ext import commands

from controllers import ytdl
from cogs import voice_member_count
from views import audio_player

PLAYER_TIMEOUT = 600 # 10 min

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('./logs/voice.log')
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('[%(asctime)s] %(funcName)-20s :: %(levelname)-8s :: %(message)s', datefmt='%d-%b-%y %H:%M:%S')
file_handler.setFormatter(file_format)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.NOTSET)
console_format = logging.Formatter('[%(asctime)s] %(name)-25s :: %(levelname)-8s :: %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_format)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

class VoiceError(Exception):
    pass


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: ytdl.YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now playing', description='```css\n{0.source.title}\n```'.format(self), color=discord.Color.blurple())
                .add_field(name='Duration', value=self.source.duration)
                .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                .set_thumbnail(url=self.source.thumbnail)
                .set_author(name=self.requester.display_name, icon_url=self.requester.display_avatar)
                )
        return embed

    def create_embed_spf(self):
        embed = (discord.Embed(title='🌿   Now playing', description='```css\n{0.source.title}\n```'.format(self), color=discord.Color.green())
                .set_thumbnail(url=self.source.thumbnail))
        return embed

    def create_embed_history_loop(self):
        embed = (discord.Embed(title='🍂   Repeat from history', color=discord.Color.magenta())
                .add_field(name='Now playing', value='```css\n{0.source.title}\n```'.format(self))
                .add_field(name='Requested by', value=self.requester.mention)
                .set_thumbnail(url=self.source.thumbnail))
        return embed

class SongQueue(asyncio.Queue):    
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.completed = asyncio.Event()
        self.songs = SongQueue()
        self.song_history = []
        self.exists = True
        self.current_embed = None

        self._loop = False
        self._autoplay = False
        self._volume = 0.5
        self.skip_votes = set()

        # Audio player
        self.audio_player = bot.loop.create_task(self.audio_player_task())

        # Spotify
        self._spotify = False
        self._url = None
        self.playlist = None
        
        # History-loop
        self._history_loop = False
        self.history_generator = self.fetchHistory()

        # voice member count
        self.voice_member_count = 0

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def autoplay(self):
        return self._autoplay

    @autoplay.setter
    def autoplay(self, value: bool):
        self._autoplay = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    @property
    def spotify(self):
        return self._spotify

    @spotify.setter
    def spotify(self, value: bool):
        self._spotify = value

    @property
    def history_loop(self):
        return self._history_loop

    @history_loop.setter
    def history_loop(self, value: bool):
        self._history_loop = value

    async def showError(self, e):
        """Show error and Stop audio player task."""

        logger.error(str(e), exc_info=True)
        await self._ctx.send('An error occurred while processing this request: {}'.format(str(e)))
        self.bot.loop.create_task(self.stop())
        self.exists = False

    async def getCurrentSong(self):
        """
        Get current song from queue.
        Tag:
            :class:`##Spotify##` : play from spotify playlist
            :class:`##History-loop##` : play from history
        """

        logger.debug(f'Waiting for getting song...')
        self.current = await self.songs.get()
        # print(f'Song: {self.current.source.title} @ {self.voice.channel.id}')
        logger.info(f'Song: {str(self.current.source.title).encode("utf-8")} @ {str(self.voice.channel.id)}')
        if self.current.source.title == "##Spotify##":
            self.spotify = True
            self.play_next_song()
            return False
        elif self.current.source.title == "##History-loop##":
            self.history_loop = True
            self.play_next_song()
            return False
        return True

    async def playCurrentSong(self):
        """Play current song."""

        view = audio_player.AudioPlayerView(self.bot, self._ctx)

        logger.info('Start')
        self.song_history.insert(0, self.current)
        self.current.source.volume = self._volume    # -- adjust volume from source.
        await self.current.source.channel.send(embed=self.current_embed, view=view)
        logger.debug(f'Playing song...')
        self.voice.play(self.current.source, after=self.play_next_song)
        if not self.voice.is_playing():
            self.voice.play(self.current.source, after=lambda e: print(f'Player error: {e}') if e else None)
        self.completed.set()
    
    async def play_source(self):
        """Play song in queue."""

        try:
            async with timeout(PLAYER_TIMEOUT): 
                logger.debug(f'empty:{self.songs.empty()} && autoplay:{self.autoplay} && spotify:{self._spotify} && history:{self.history_loop}')
                
                ok = await self.getCurrentSong()
                if not ok:
                    return False
                
                self.current_embed = self.current.create_embed()
                
        except asyncio.TimeoutError:
            logger.error('Timeout')
            raise TimeoutError

        await self.playCurrentSong()
        return True

    async def play_autoplay(self):
        """Can't use at moment."""

        print(f'[{self.autoplay and self.current}]')
        print(f"autoplay:{self.autoplay} &&\ncurrent:{self.current}")
        try:
            async with timeout(3): 
                self.current = await self.songs.get()
        except asyncio.TimeoutError:
            print("timeout error")
            song_url = self.current.source.url
            print(song_url)

            # Get the page
            async with httpx.AsyncClient() as client:
                global soup
                response = await client.get(song_url)
                soup = BeautifulSoup(response.text, 'html.parser')
            data = set(re.findall(r'"videoId":"(.*?)"', response.text))
            print(data)

            # Parse all the recommended videos out of the response and store them in a list
            recommended_urls = [f"https://www.youtube.com/watch?v={VId}" for VId in data]

            # Chose the next song so that it wasnt played recently
            print("recommended_urls : ", recommended_urls)
            next_song = recommended_urls[0]

            for recommended_url in recommended_urls:
                not_in_history = True
                for song in self.song_history[:15]:
                    if recommended_url == song.source.url:
                        not_in_history = False
                        break
                
                if not_in_history:
                    next_song = recommended_url
                    break

            async with self._ctx.typing():
                try:
                    source = await ytdl.YTDLSource.create_source(self._ctx, next_song, loop=self.bot.loop)
                except ytdl.YTDLError as e:
                    await self.showError(e)
                    return
                else:
                    song = Song(source)
                    self.current = song
                    await self._ctx.send('Autoplaying {}'.format(str(source)))

        await self.playCurrentSong()

    async def play_spotify(self):
        """Play song from spotify playlist."""

        try:
            async with timeout(PLAYER_TIMEOUT): 
                logger.debug(f'empty:{self.songs.empty()} && autoplay:{self.autoplay} && spotify:{self._spotify} && history:{self.history_loop}')
                time.sleep(5)  # wait for next music in spotify playlist1
                async with self._ctx.typing():
                    try:
                        source = await ytdl.YTDLSource.create_source(self._ctx, str(next(self.playlist)), loop=self.bot.loop)
                    except ytdl.YTDLError as e:
                        await self.showError(e)
                        return False
                    else:
                        song = Song(source)
                        await self.songs.put(song)
                        await self._ctx.send('Searching from Spotify Playlist \n> {}'.format(self._url))
                    
                ok = await self.getCurrentSong()
                if not ok:
                    return False

                self.current_embed = self.current.create_embed_spf()

        except asyncio.TimeoutError:
            logger.error('Timeout')
            raise TimeoutError

        logger.info('Start')
        self.current.source.volume = self._volume
        await self.current.source.channel.send(embed=self.current_embed)
        logger.debug('Playing song...')
        self.voice.play(self.current.source, after=self.play_next_song)
        if not self.voice.is_playing():
            self.voice.play(self.current.source, after=lambda e: print(f'Player error: {e}') if e else None)
        self.completed.set()
        return True

    def fetchHistory(self):
        """Fetch songs in history."""

        while True:
            try:
                for song in self.song_history[-1::-1]:
                    yield song
            except StopIteration:
                logger.warning('End of history list')

    async def play_from_history(self):
        """Play song from history."""

        try:
            async with timeout(PLAYER_TIMEOUT): 
                logger.debug(f'empty:{self.songs.empty()} && autoplay:{self.autoplay} && spotify:{self._spotify} && history:{self.history_loop}')
                time.sleep(5)  # wait for next music in history
                async with self._ctx.typing():
                    try:
                        source = await ytdl.YTDLSource.create_source(self._ctx, str(next(self.history_generator).source.url), loop=self.bot.loop)
                    except ytdl.YTDLError as e:
                        await self.showError(e)
                        return False
                    else:
                        song = Song(source)
                        await self.songs.put(song)

                ok = await self.getCurrentSong()
                if not ok:
                    return False
                
                self.current_embed = self.current.create_embed_history_loop()
                
        except asyncio.TimeoutError:
            logger.error('Timeout')
            raise TimeoutError

        logger.info('Start')
        await self.current.source.channel.send(embed=self.current_embed)
        logger.debug('Playing song...')
        self.voice.play(self.current.source, after=self.play_next_song)
        if not self.voice.is_playing():
            self.voice.play(self.current.source, after=lambda e: print(f'Player error: {e}') if e else None)
        self.completed.set()
        return True

    async def audio_player_task(self):
        """Audio player."""

        while True:
            logger.debug('--- Start player ---')

            # clear now source
            self.next.clear()
            self.completed.clear()
            self.now = None
            logger.debug(f'number of songs in queue: {self.songs}')

            # exists
            if not self.exists:
                return

            try:
                # loop current source
                if self.loop:
                    logger.debug('**LOOP**')
                    self.current = self.song_history[0]
                    self.now = discord.FFmpegPCMAudio(self.current.source.stream_url, **ytdl.YTDLSource.FFMPEG_OPTIONS)
                    self.voice.play(self.now, after=self.play_next_song)

                # autoplay
                elif self.autoplay:
                    logger.debug('**AUTOPLAY**')
                    ok = await self.play_autoplay()
                    if not ok:
                        continue

                # spotify
                elif self._spotify and self.songs.empty():
                    logger.debug('**SPOTIFY**')
                    ok = await self.play_spotify()
                    if not ok:
                        continue

                # history-loop
                elif self.history_loop and self.songs.empty():
                    logger.debug('**HISTORY-LOOP**')
                    ok = await self.play_from_history()
                    if not ok:
                        continue

                # other
                else:
                    logger.debug('**SOURCE**')
                    ok = await self.play_source()
                    if not ok:
                        continue

            except TimeoutError:
                self.bot.loop.create_task(self.stop())
                self.exists = False
                return

            # check member in voice channel
            await self.voiceMemberCount(self.voice.channel.id)
            logger.info(f'Member( Count={self.voice_member_count} )')
            if self.voice_member_count == 1:
                self.bot.loop.create_task(self.stop())
                self.exists = False
                return

            await self.next.wait()

    def play_next_song(self, error=None):
        """
        Play next song for continue loop in Audio player.
        use after play song complete.
        """
        self.completed.wait()

        logger.info('Next song')
        if error:
            print(error)
            logger.error(str(error), exc_info=True)
            raise VoiceError(str(error))

        self.current = None
        
        self.next.set()

    def skip(self):
        """
        Skip song.
        Song will stop and after this call :func:`self.play_next_song`.
        """

        logger.info('Skip song')
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def voiceMemberCount(self, channel_id):
        """voice member count."""

        self.voice_member_count = await voice_member_count.getVoiceMemberCount(channel_id)

    async def stop(self):
        """Disconnect from voice channel"""

        logger.warning(f'Stop playing song')
        self.songs.clear()
        self._spotify = False
        self.exists = False

        if self.voice:
            await self._ctx.send('I enjoyed seeing you again. 👋')
            await self.voice.disconnect()
            self.voice = None
