import discord
from discord.ext import commands

BUTTON_CLR = discord.ButtonStyle.gray

class SearchView(discord.ui.View):
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        super().__init__(timeout=45.0)
        self.bot = bot
        self.ctx = ctx
        self.value = None
    
    # 1
    @discord.ui.button(label="1", style=BUTTON_CLR)
    async def _song_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "1"
        self.stop()

    # 2
    @discord.ui.button(label="2", style=BUTTON_CLR)
    async def _song_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "2"
        self.stop()

    # 3
    @discord.ui.button(label="3", style=BUTTON_CLR)
    async def _song_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "3"
        self.stop()

    # 4
    @discord.ui.button(label="4", style=BUTTON_CLR)
    async def _song_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "4"
        self.stop()

    # 5
    @discord.ui.button(label="5", style=BUTTON_CLR)
    async def _song_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "5"
        self.stop()

    # # 6
    # @discord.ui.button(label="6", style=discord.ButtonStyle.blurple)
    # async def _song_6(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     self.value = "6"
    #     self.stop()

    # # 7
    # @discord.ui.button(label="7", style=discord.ButtonStyle.blurple)
    # async def _song_7(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     self.value = "7"
    #     self.stop()
    
    # # 8
    # @discord.ui.button(label="8", style=discord.ButtonStyle.blurple)
    # async def _song_8(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     self.value = "8"
    #     self.stop()

    # # 9
    # @discord.ui.button(label="9", style=discord.ButtonStyle.blurple)
    # async def _song_9(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     self.value = "9"
    #     self.stop()

    # # 10
    # @discord.ui.button(label="10", style=discord.ButtonStyle.blurple)
    # async def _song_10(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     self.value = "10"
    #     self.stop()

    # Cancel
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def _cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = 'cancel'
        self.stop()

    