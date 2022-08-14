import nextcord

from nextcord.ext import commands
from config import settings


class MessagesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Deal with edited messages"""
        if before.guild.id != settings['guild']['junkies']:
            return
        if before.channel.id in [settings['channels']['admin'], settings['channels']['mod-log']]:
            return
        embed = nextcord.Embed(title=f"Message edited in #{before.channel.name}", color=nextcord.Color.blue())
        embed.set_author(name=before.author.name, icon_url=before.author.display_avatar.url)
        embed.add_field(name="Before:", value=before.content, inline=False)
        embed.add_field(name="After:", value=after.content, inline=False)
        embed.set_footer(text=f"ID: {after.id} | {after.edited_at}")
        mod_channel = self.bot.get_channel(settings['channels']['mod-log'])
        await mod_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Deal with deleted messages"""
        if message.guild.id != settings['guild']['junkies']:
            return
        if message.channel.id in [settings['channels']['admin'], settings['channels']['mod-log']]:
            return
        embed = nextcord.Embed(color=nextcord.Color.red())
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
        embed.add_field(name=f"Message deleted in #{message.channel.name}", value=message.content)
        embed.set_footer(text=f"ID: {message.id} | {message.edited_at}")
        mod_channel = self.bot.get_channel(settings['channels']['mod-log'])
        await mod_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(MessagesCog(bot))
