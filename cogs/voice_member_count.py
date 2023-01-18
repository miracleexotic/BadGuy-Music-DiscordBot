import time
import json
import aiofiles
import logging

from discord.ext import commands

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_format = logging.Formatter('[%(asctime)s] %(name)-25s :: %(levelname)-8s :: %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_format)

logger.addHandler(console_handler)

FILE_PATH_VOICE_MEMBER = './databases/voice_member_count.json'

async def getVoiceMemberCount(channel_id):
    async with aiofiles.open(FILE_PATH_VOICE_MEMBER, 'r') as f:
        contents = await f.read()
    voice_member_data = json.loads(contents)
    return len(voice_member_data[str(channel_id)])

class VoiceMemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def update(self, voice_member_data):
        with open(FILE_PATH_VOICE_MEMBER, 'w') as update_voice_member_data:
            json.dump(voice_member_data, update_voice_member_data, indent=4)
            time.sleep(1)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        member_id = str(member.id)
        logger.info(f'{member} {member_id} from {before.channel} {before.channel.id if before.channel else None} to {after.channel} {after.channel.id if after.channel else None}')

        with open(FILE_PATH_VOICE_MEMBER, 'r') as file:
            try:
                voice_member_data = json.load(file)
            except json.decoder.JSONDecodeError:
                voice_member_data = {}
                self.update(voice_member_data)
                
            if before.channel and after.channel:
                if str(before.channel.id) == str(after.channel.id):
                    return

            if before.channel:
                bf_ch_id = str(before.channel.id)
                if bf_ch_id not in list(voice_member_data.keys()):
                    voice_member_data[bf_ch_id] = []
                if member_id in voice_member_data[bf_ch_id]:
                    voice_member_data[bf_ch_id].remove(member_id)
                    self.update(voice_member_data)

            if after.channel:
                af_ch_id = str(after.channel.id)
                if af_ch_id not in list(voice_member_data.keys()):
                    voice_member_data[af_ch_id] = []
                if member_id not in voice_member_data[af_ch_id]:
                    voice_member_data[af_ch_id].append(member_id)
                    self.update(voice_member_data)

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceMemberCount(bot))

