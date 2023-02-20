import asyncio
import functools

import discord
from discord.ext import commands

from views import search_view

import yt_dlp

yt_dlp.utils.bug_reports_message = lambda: ''

class YTDLError(Exception):
    pass

class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
        'executable': r'C:\Users\IAMMAI\Desktop\githubProject\BadGuyBot\BadGuyBot-master\ffmpeg\bin\ffmpeg.exe'
    }

    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader') or ""
        self.uploader_url = data.get('uploader_url') or ""
        date = data.get('upload_date') or ""
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4] or ""
        self.title = data.get('title') or ""
        self.thumbnail = data.get('thumbnail') or ""
        self.description = data.get('description') or ""
        self.duration = self.parse_duration(int(data.get('duration')) if data.get('duration') else 0)
        self.tags = data.get('tags') or ""
        self.url = data.get('webpage_url') or ""
        self.views = data.get('view_count') or ""
        self.likes = data.get('like_count') or ""
        self.dislikes = data.get('dislike_count') or ""
        self.stream_url = data.get('url') or ""

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_history_loop(cls, ctx: commands.Context):
        return cls(ctx, discord.FFmpegPCMAudio('', **cls.FFMPEG_OPTIONS), data={'title': '##History-loop##'})

    @classmethod
    async def create_spotify(cls, ctx: commands.Context, url: str):
        return cls(ctx, discord.FFmpegPCMAudio(url, **cls.FFMPEG_OPTIONS), data={'title': '##Spotify##', 'webpage_url': url})

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))
        
        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @classmethod
    async def search_source(cls, bot: commands.Bot, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        max_search = 5
        # channel = ctx.channel
        loop = loop or asyncio.get_event_loop()

        cls.search_query = '%s%s:%s' % ('ytsearch', max_search, ''.join(search))

        partial = functools.partial(cls.ytdl.extract_info, cls.search_query, download=False, process=False)
        info = await loop.run_in_executor(None, partial)

        cls.search = {}
        cls.search["title"] = f'Search results for:\n**{search}**'
        cls.search["type"] = 'rich'
        # cls.search["color"] = 7506394
        cls.search["color"] = 65526
        cls.search["author"] = {'name': f'{ctx.author.display_name}', 'url': f'{ctx.author.display_avatar}', 'icon_url': f'{ctx.author.display_avatar}'}
        
        lst = []
        temp = []
        for i, e in enumerate(info['entries']):
            temp.append(e)
            VId = e.get('id')
            VUrl = 'https://www.youtube.com/watch?v=%s' % (VId)
            lst.append(f'`{i + 1}.` [{e.get("title")}]({VUrl})')

        lst.append('\n**Select a number to make a choice, Select `cancel` to exit**')
        cls.search["description"] = "\n".join(lst)

        view = search_view.SearchView(bot, ctx)
        em = discord.Embed.from_dict(cls.search)
        await ctx.send(embed=em, view=view, delete_after=45.0)

        try:
            await view.wait()

        except asyncio.TimeoutError:
            rtrn = 'timeout'

        else:
            if view.value.isdigit() == True:
                sel = int(view.value)
                if 0 < sel <= max_search:
                    VId = temp[sel - 1]['id']
                    VUrl = 'https://www.youtube.com/watch?v=%s' % (VId)
                    partial = functools.partial(cls.ytdl.extract_info, VUrl, download=False)
                    data = await loop.run_in_executor(None, partial)
                    rtrn = cls(ctx, discord.FFmpegPCMAudio(data['url'], **cls.FFMPEG_OPTIONS), data=data)
                else:
                    rtrn = 'sel_invalid'
            elif view.value == 'cancel':
                rtrn = 'cancel'
            elif not ctx.voice_state.exists:
                rtrn = 'not_voice'
            else:
                rtrn = 'sel_invalid'

        # def check(msg):
        #     return msg.content.isdigit() == True and msg.channel == channel or (msg.content == 'cancel' or msg.content == 'Cancel') or not ctx.voice_state.exists
        
        # try:
        #     m = await bot.wait_for('message', check=check, timeout=45.0)

        # except asyncio.TimeoutError:
        #     rtrn = 'timeout'

        # else:
        #     if m.content.isdigit() == True:
        #         sel = int(m.content)
        #         if 0 < sel <= 10:
        #             VId = temp[sel - 1]['id']
        #             VUrl = 'https://www.youtube.com/watch?v=%s' % (VId)
        #             partial = functools.partial(cls.ytdl.extract_info, VUrl, download=False)
        #             data = await loop.run_in_executor(None, partial)
        #             rtrn = cls(ctx, discord.FFmpegPCMAudio(data['url'], **cls.FFMPEG_OPTIONS), data=data)
        #         else:
        #             rtrn = 'sel_invalid'
        #     elif m.content == 'cancel' or m.content == 'Cancel':
        #         rtrn = 'cancel'
        #     elif not ctx.voice_state.exists:
        #         rtrn = 'not_voice'
        #     else:
        #         rtrn = 'sel_invalid'
        
        return rtrn

    @staticmethod
    def parse_duration(duration: int):
        if duration > 0:
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)

            duration = []
            if days > 0:
                duration.append('{}'.format(days))
            if hours > 0:
                duration.append('{}'.format(hours))
            if minutes > 0:
                duration.append('{}'.format(minutes))
            if seconds > 0:
                duration.append('{}'.format(seconds))
            
            value = ':'.join(duration)
        
        elif duration == 0:
            value = "LIVE"
        
        return value
