import discord
from discord.ext import commands

from controllers import ytdl, voice


class SongReqModal(discord.ui.Modal):

    name = discord.ui.TextInput(
        label="Song name?",
        placeholder="Song name here...",
    )

    def __init__(
        self,
        *,
        title: str = "Music Request",
        bot: commands.Bot,
        ctx: commands.Context,
        view: discord.ui.View
    ) -> None:
        super().__init__(title=title, timeout=None)
        self.bot = bot
        self.ctx = ctx
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=self.view)
        async with self.ctx.typing():
            try:
                source = await ytdl.YTDLSource.create_source(
                    self.ctx, self.name.value, loop=self.bot.loop
                )
            except ytdl.YTDLError as e:
                await self.ctx.send(
                    "An error occurred while processing this request: {}".format(str(e))
                )
            else:
                if not self.ctx.voice_state.voice:
                    await self.ctx.invoke(self._join)

                song = voice.Song(source)
                await self.ctx.voice_state.songs.put(song)
                await self.ctx.send("Enqueued {}".format(str(source)))

    # async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
    #     await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)


class AudioPlayerView(discord.ui.View):
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        super().__init__(timeout=None)
        self.bot = bot
        self.ctx = ctx
        self.start = True
        self.loop = False
        self.song_req_modal = SongReqModal(bot=bot, ctx=ctx, view=self)

    # Play
    @discord.ui.button(label="Pause", style=discord.ButtonStyle.red)
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.start:
            if (
                self.ctx.voice_state.is_playing
                and self.ctx.voice_state.voice.is_playing()
            ):
                self.ctx.voice_state.voice.pause()
            button.label = "Play"
            button.style = discord.ButtonStyle.green
        else:
            if (
                self.ctx.voice_state.is_playing
                and self.ctx.voice_state.voice.is_paused()
            ):
                self.ctx.voice_state.voice.resume()
            button.label = "Pause"
            button.style = discord.ButtonStyle.red
        self.start = not self.start
        await interaction.response.edit_message(view=self)

    # Next
    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next_song(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        voter = self.ctx.message.author
        if voter == self.ctx.voice_state.current.requester:
            await self.ctx.message.add_reaction("⏭")
            self.ctx.voice_state.skip()

        elif voter.id not in self.ctx.voice_state.skip_votes:
            self.ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(self.ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await self.ctx.message.add_reaction("⏭")
                self.ctx.voice_state.skip()
            else:
                await self.ctx.send(
                    "Skip vote added, currently at **{}/3**".format(total_votes)
                )

        else:
            await self.ctx.send("You have already voted to skip this song.")
        await interaction.response.edit_message(view=self)

    # Loop
    @discord.ui.button(label="Loop: Off", style=discord.ButtonStyle.grey)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.loop:
            button.label = "Loop: Off"
        else:
            button.label = "Loop: On"
        self.loop = not self.loop
        self.ctx.voice_state.loop = not self.ctx.voice_state.loop
        await interaction.response.edit_message(view=self)

    # Add
    @discord.ui.button(label="+ Add", style=discord.ButtonStyle.grey)
    async def songreq(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(self.song_req_modal)
