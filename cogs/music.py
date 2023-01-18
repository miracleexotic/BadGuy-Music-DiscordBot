import math

import discord
from discord.ext import commands

from controllers import (
    ytdl, 
    voice, 
    spotify
)

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        """Returns or creates voice.VoiceState for the guild defined in the passed ctx"""
        state = self.voice_states.get(ctx.guild.id)
        if not state or not state.exists:
            state = voice.VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        """Unloads the music cog"""
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.stop())
            except:
                pass

    def cog_check(self, ctx: commands.Context):
        """Prevent calling commands in DM's"""
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        """Set voice state for every command"""
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.bot.user.id:
            print(f"{message.guild}/{message.channel}/{message.author.name}>{message.content}")
            if message.embeds:
                print(message.embeds[0].to_dict())

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""
        try:
            destination = ctx.author.voice.channel
            if ctx.voice_state.voice:
                await ctx.voice_state.voice.move_to(destination)
                return

            ctx.voice_state.voice = await destination.connect()
        except:
            pass

    @commands.command(name='summon')
    # @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """
        Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise voice.VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    # @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume')
    @commands.is_owner()
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))

    @commands.command(name='now', aliases=['current', 'playing', 'np', 'nowplaying'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')
        embed = ctx.voice_state.current_embed
        await ctx.send(embed=embed)

    @commands.command(name='pause', aliases=['pa'])
    # @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume', aliases=['re', 'res'])
    # @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop')
    # @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if ctx.voice_state.autoplay:
            ctx.voice_state.autoplay = False
            await ctx.send('Autoplay is now turned off')

        if ctx.voice_state.spotify:
            ctx.voice_state.spotify = False
            await ctx.send('Spotify playlist is now turned off')

        if ctx.voice_state.history_loop:
            ctx.voice_state.history_loop = False
            await ctx.send('History loop is now turned off')
            
        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')


    @commands.command(name='skip', aliases=['s'])
    async def _skip(self, ctx: commands.Context):
        """
        Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.command(name='queue')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """
        Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='history')
    async def _history(self, ctx: commands.Context, *, page: int = 1):
        """
        Shows the player's history.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.song_history) == 0:
            return await ctx.send('Empty history.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.song_history) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.song_history[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.song_history), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """
        Loops the currently playing song.
        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')
        await ctx.send('Looping a song is now turned ' + ('on' if ctx.voice_state.loop else 'off') )

    @commands.command(name='autoplay')
    async def _autoplay(self, ctx: commands.Context):
        """
        Automatically queue a new song that is related to the song at the end of the queue.
        Invoke this command again to toggle autoplay the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.autoplay = not ctx.voice_state.autoplay
        await ctx.message.add_reaction('✅')
        await ctx.send('Autoplay after end of queue is now ' + ('on' if ctx.voice_state.autoplay else 'off') )

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str):
        """
        Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        async with ctx.typing():
            try:
                source = await ytdl.YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except ytdl.YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                if not ctx.voice_state.voice:
                    await ctx.invoke(self._join)

                song = voice.Song(source)
                await ctx.voice_state.songs.put(song)
                await ctx.send('Enqueued {}'.format(str(source)))

    @commands.command(name='search', aliases=['ps'])
    async def _search(self, ctx: commands.Context, *, search: str):
        """
        Searches youtube.
        It returns an imbed of the first 10 results collected from youtube.
        Then the user can choose one of the titles by typing a number
        in chat or they can cancel by typing "cancel" in chat.
        Each title in the list can be clicked as a link.
        """

        async with ctx.typing():
            try:
                source = await ytdl.YTDLSource.search_source(self.bot, ctx, search, loop=self.bot.loop)
            except ytdl.YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                if source == 'sel_invalid':
                    await ctx.send('Invalid selection')
                elif source == 'cancel':
                    await ctx.send(':white_check_mark:')
                elif source == 'timeout':
                    await ctx.send(':alarm_clock: **Time\'s up bud**')
                elif source == 'not_voice':
                    await ctx.send("Stop searching... try again")
                else:
                    if not ctx.voice_state.voice:
                        await ctx.invoke(self._join)

                    song = voice.Song(source)
                    await ctx.voice_state.songs.put(song)
                    await ctx.send('Enqueued {}'.format(str(source)))

    @commands.command(name='spotify', aliases=['spf'])
    async def _spotify(self, ctx: commands.Context, *, link: str):
        """List music from spotify."""

        ctx.voice_state._url = spotify.Spotify.verifyUrl(link)
        ctx.voice_state.spotify = False
        try:
            ctx.voice_state.playlist = spotify.Spotify.fetchPlaylist()
        except Exception:
            ctx.voice_state.spotify = False
            return await ctx.send('Spotify playlist only.')

        async with ctx.typing():
            try:
                source = await ytdl.YTDLSource.create_spotify(ctx, link)
            except ytdl.YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                if not ctx.voice_state.voice:
                    await ctx.invoke(self._join)

                song = voice.Song(source)
                await ctx.voice_state.songs.put(song)

            await ctx.message.add_reaction('✅')
            await ctx.send('Spotify playlist is now on')

    @commands.command(name='spotify-on', aliases=['spf-on'])
    async def _spotify_on(self, ctx: commands.Context):
        """Turn Spotify playlist is on"""

        await ctx.message.add_reaction('✅')
        if not ctx.voice_state.spotify and ctx.voice_state.playlist:
            ctx.voice_state.spotify = True 

            try:
                source = await ytdl.YTDLSource.create_spotify(ctx, ctx.voice_state._url)
            except ytdl.YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                if not ctx.voice_state.voice and ctx.voice_state.spotify:
                    await ctx.invoke(self._join)

                song = voice.Song(source)
                await ctx.voice_state.songs.put(song)

        elif ctx.voice_state.spotify and ctx.voice_state.playlist:
            return await ctx.send('Spotify playlist is now on')
        elif not ctx.voice_state.spotify and not ctx.voice_state.playlist:
            return await ctx.send('Please set playlist first.\n> |spf <spotify-playlist-link>')

    @commands.command(name='spotify-off', aliases=['spf-off'])
    async def _spotify_off(self, ctx: commands.Context):
        """Turn Spotify playlist is off"""

        await ctx.message.add_reaction('✅')
        if not ctx.voice_state.spotify and not ctx.voice_state.playlist:
            return await ctx.send('Nothing being played from spotify.')
        elif ctx.voice_state.spotify and ctx.voice_state.playlist:
            ctx.voice_state.spotify = False
            return await ctx.send('Spotify playlist after end of queue is now off')

    @commands.command(name='history-loop', aliases=['hl'])
    async def _history_loop(self, ctx: commands.Context):
        """
        Repeat song from history.
        Invoke this command again to unloop the song.
        """

        if len(ctx.voice_state.song_history) == 0:
            return await ctx.send('History is empty.')

        if ctx.voice_state.history_loop:
            ctx.voice_state.history_loop = False
            await ctx.send('History loop is now off')
        else:
            async with ctx.typing():
                try:
                    source = await ytdl.YTDLSource.create_history_loop(ctx)
                except ytdl.YTDLError as e:
                    await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
                else:
                    if not ctx.voice_state.voice:
                        await ctx.invoke(self._join)

                    song = voice.Song(source)
                    await ctx.voice_state.songs.put(song)
            await ctx.send('History loop is now on')

        await ctx.message.add_reaction('✅')

            
    @_join.before_invoke
    @_play.before_invoke
    @_search.before_invoke
    @_spotify.before_invoke
    @_spotify_on.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client and ctx.author.voice:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))