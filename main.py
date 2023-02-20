#!/usr/bin/env python3
import json

import discord
from discord.ext import commands

class MyBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents) -> None:
        super().__init__(
            command_prefix="|",
            description="Playing music 🌠", 
            intents=intents)

    async def setup_hook(self) -> None:
        await self.load_extension("cogs.music")
        await self.load_extension("cogs.voice_member_count")

    async def on_ready(self):
        activity = discord.Game(name='|play <music>')
        # activity = discord.Game(name='maintenance BadGuy')
        await self.change_presence(activity=activity)
        print(f'Logged in as {self.user.name}')

def main():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = MyBot(intents=intents)
    with open('authentication/config.json') as fh:
        bot.config = json.load(fh)
    bot.run(bot.config['token'])


if __name__ == "__main__":
    main()