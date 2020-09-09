import discord

from datetime import datetime, timedelta
from discord.ext import commands, tasks
from config import settings


def to_time(seconds):
    d, r = divmod(seconds, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    if d > 0:
        return f"{d:.0f}d {h:.0f}h"
    elif h > 0:
        return f"{h:.0f}h {m:.0f}m"
    else:
        return f"{m:.0f}m"


class Bot:
    def __init__(self, name, bot_id, channel_id, owner):
        self.name = name
        self.bot_id = bot_id
        self.channel_id = channel_id
        self.owner = owner

    async def notify_down(self, bot):
        """Notify bot owner that the bot is down"""
        channel = bot.get_channel(self.channel_id)
        await channel.send(f"<@{self.owner}> - It would appear that {self.name} is down.")

    async def notify_follow_up(self, bot, downtime):
        """Notify bot owner that the bot is still down"""
        channel = bot.get_channel(self.channel_id)
        await channel.send(f"<@{self.owner}> - {self.name} has been down for {downtime}")

    async def notify_up(self, bot, downtime):
        """Notify bot owner that the bot is back up again"""
        channel = bot.get_channel(self.channel_id)
        await channel.send(f"<@{self.owner}> - {self.name} is back up.\n"
                           f"Downtime: {downtime}")


class Downtime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watchman.start()

    def cog_unload(self):
        self.watchman.cancel()

    bots = [
        Bot("RCS Bot", settings['bots']['rcs'], 568167391662440448, 251150854571163648),
        Bot("The Arborist", settings['bots']['oak'], settings['channels']['mod-log'], 251150854571163648),
        Bot("Clash Recruiter", settings['bots']['cr'], 662284520329969677, 581442925611712513),
        Bot("Donation Tracker", settings['bots']['dt'], 594280479881035776, 230214242618441728),
        Bot("Bat", settings['bots']['bat'], 647839792066723840, 304690705996054528),
        Bot("Karen", settings['bots']['karen'], 647839792066723840, 304690705996054528),
        Bot("Maniacs Bot", settings['bots']['maniacs'], 568511927597400074, 325493699478028290),
        Bot("Minion Bot", settings['bots']['minion'], 567551819451072541, 267057699856842753),
        Bot("Wiz Bot", settings['bots']['wiz'], 568162367385501722, 243934463615041536),
        Bot("WarMatch", settings['bots']['wm'], 567551904071155732, 126084695824924673),
        Bot("ClashCord", settings['bots']['clashcord'], 608672949968437258, 239810643581075457),
        Bot("Sidekick", settings['bots']['sk'], 567550343748124682, 134153092378656769),
        Bot("ClashPerk", settings['bots']['clashperk'], 691885320035237940, 444432489818357760),
        Bot("Ivory", settings['bots']['ivory'], 636222832430284821, 294035020236980224),
        Bot("Ruby", settings['bots']['ruby'], 636222832430284821, 294035020236980224),
        Bot("Alph4", settings['bots']['alph4'], 715903895741661194, 434693228189712385),
        Bot("ScatterBot", settings['bots']['scatter'], 695448751741075488, 246286410946969610),
    ]

    @tasks.loop(minutes=5.0)
    async def watchman(self):
        """Task for monitoring API bots
        Downtime is stored in the bot_downtime table of postgresql
        """
        conn = self.bot.pool
        now = datetime.utcnow()
        guild = self.bot.get_guild(566451504332931073)
        offline_sql = "SELECT offline_start FROM bot_downtime WHERE online = False AND bot_id = $1"
        update_sql = "UPDATE bot_downtime SET last_notification = $1 WHERE bot_id = $2 AND online = False"
        reported_sql = ("UPDATE bot_downtime "
                        "SET online = True, reported = True, offline_end = $1 "
                        "WHERE bot_id = $2 AND reported = False")
        insert_sql = ("INSERT INTO bot_downtime (bot_id, online, offline_start, last_notification) "
                      "VALUES ($1, False, $2, $3)")
        for bot in self.bots:
            status = guild.get_member(bot.bot_id).status
            offline_start = await conn.fetchval(offline_sql, bot.bot_id)
            if offline_start:
                # bot was offline last time we checked
                downtime = to_time((now - offline_start).total_seconds())
                if status == discord.Status.online:
                    # bot is now back online
                    try:
                        await bot.notify_up(self.bot, downtime)
                    except discord.errors.Forbidden:
                        channel = self.bot.get_channel(settings['channels']['mod-log'])
                        await channel.send(f"API Bot does not have access to <#{bot.channel_id}> ({bot.channel_id})")
                    await conn.execute(reported_sql, now, bot.bot_id)
                    continue
                else:
                    # bot is still offline
                    sql = "SELECT last_notification FROM bot_downtime WHERE bot_id = $1 AND online = False"
                    last_notification = await conn.fetchval(sql, bot.bot_id)
                    if last_notification < now - timedelta(days=1.0):
                        try:
                            await bot.notify_follow_up(self.bot, downtime)
                        except discord.errors.Forbidden:
                            channel = self.bot.get_channel(settings['channels']['mod-log'])
                            await channel.send(f"API Bot does not have access to <#{bot.channel_id}> "
                                               f"({bot.channel_id})")
                        await conn.execute(update_sql, now, bot.bot_id)
                    continue
            elif status != discord.Status.online:
                # bot is offline for the first time
                await conn.execute(insert_sql, bot.bot_id, now, now)
                try:
                    await bot.notify_down(self.bot)
                except discord.errors.Forbidden:
                    channel = self.bot.get_channel(settings['channels']['mod-log'])
                    await channel.send(f"API Bot does not have access to <#{bot.channel_id}> ({bot.channel_id})")

    @watchman.before_loop
    async def before_watchman(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Downtime(bot))
