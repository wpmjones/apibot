import nextcord
import asyncio

from nextcord.ext import commands
from config import settings
from datetime import datetime, timezone, timedelta


class Deleted:
    pass


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
        if before.author.bot:
            return
        guild = self.bot.get_guild(settings['guild']['junkies'])
        admin_role = guild.get_role(settings['roles']['admin'])
        if admin_role in before.author.roles:
            return
        embed = nextcord.Embed(title=f"Message edited in #{before.channel.name}", color=nextcord.Color.blue())
        embed.set_author(name=before.author.name, icon_url=before.author.display_avatar.url)
        embed.add_field(name="Before:", value=before.content, inline=False)
        embed.add_field(name="After:", value=after.content, inline=False)
        embed.set_footer(text=f"ID: {after.id} | {after.edited_at}")
        mod_channel = self.bot.get_channel(settings['channels']['mod-log'])
        await mod_channel.send(embed=embed)

    @commands.command(name="atest", hidden=True)
    @commands.is_owner()
    async def test_audit_log(self, ctx):
        """Testing audit log checks"""
        guild = self.bot.get_guild(settings['guild']['junkies'])
        async for entry in guild.audit_logs(action=nextcord.AuditLogAction.message_delete, limit=5):
            await ctx.send(f"{entry.created_at} - {entry.user} preformed {entry.action}")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        """Deal with deleted messages"""
        guild = self.bot.get_guild(settings['guild']['junkies'])
        if not payload.cached_message:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
        else:
            message = payload.cached_message
        if message.guild.id != settings['guild']['junkies']:
            return
        if message.channel.id in [settings['channels']['admin'], settings['channels']['mod-log']]:
            return
        if message.author.bot:
            return
        # Not sure if this is necessary, but I want the audit log to have time to register the delete
        await asyncio.sleep(5.0)
        now_tz = datetime.now().replace(tzinfo=timezone.utc)
        # admin_role = guild.get_role(settings['roles']['admin'])
        # if admin_role in message.author.roles:
        #     return
        deleted_by = "Message author or someone else (still testing)"
        async for entry in guild.audit_logs(action=nextcord.AuditLogAction.message_delete, limit=1):
            self.bot.logger.info(f"Entry date: {entry.created_at} compared to {now_tz}")
            if entry.created_at > now_tz - timedelta(seconds=15):
                deleted_by = entry.user.name
        embed = nextcord.Embed(color=nextcord.Color.red())
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
        embed.add_field(name=f"Message deleted in #{message.channel.name}", value=message.content)
        embed.set_footer(text=f"ID: {message.id} | Deleted by: {deleted_by}")
        mod_channel = self.bot.get_channel(settings['channels']['mod-log'])
        await mod_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(MessagesCog(bot))
