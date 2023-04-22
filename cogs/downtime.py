import coc
import disnake
import asyncio

from cogs.utils.send_email import SendMail
from datetime import datetime, timedelta
from disnake.ext import commands, tasks
from config import settings

enviro = settings['enviro']

JUNKIES_GUILD_ID = settings['guild']['junkies']
if enviro == "LIVE":
    GUILD_IDS = [JUNKIES_GUILD_ID, settings['guild']['bot_logs']]
else:
    GUILD_IDS = [settings['guild']['bot_logs']]


def to_time(seconds):
    d, r = divmod(seconds, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    if d > 0:
        return f"{d:.0f}d {h:.0f}h"
    elif h > 0:
        return f"{h:.0f}h {m:.0f}m"
    else:
        return f"{m:.0f}m {s:.0f}s"


class Bot:
    def __init__(self, name, bot_id, channel_id, owner, monitor, email=None):
        self.name = name
        self.bot_id = bot_id
        self.channel_id = channel_id
        self.owner = owner
        self.monitor = monitor
        self.email = email

    async def notify_down(self, bot):
        """Notify bot owner that the bot is down"""
        channel = bot.get_channel(self.channel_id)
        msg = await channel.send(f"<@{self.owner}> - It would appear that {self.name} is down.")
        bot.logger.info(f"Bot down: {self.name} - Email: {self.email}")
        # if self.email:
        #     send_email = SendMail(self.email, "Bot Owner", self.name, msg.guild.id, msg.channel.id, msg.id)
        #     send_email.send_mail_down()

    async def notify_follow_up(self, bot, downtime):
        """Notify bot owner that the bot is still down"""
        channel = bot.get_channel(self.channel_id)
        msg = await channel.send(f"<@{self.owner}> - {self.name} has been down for {downtime}")
        # if self.email:
        #     send_email = SendMail(self.email, "Bot Owner", self.name, msg.guild.id, msg.channel.id, msg.id)
        #     send_email.send_mail_followup(downtime)

    async def notify_up(self, bot, downtime):
        """Notify bot owner that the bot is back up again"""
        channel = bot.get_channel(self.channel_id)
        msg = await channel.send(f"<@{self.owner}> - {self.name} is back up.\n"
                                 f"Downtime: {downtime}")
        # if self.email:
        #     send_email = SendMail(self.email, "Bot Owner", self.name, msg.guild.id, msg.channel.id, msg.id)
        #     send_email.send_mail_up(downtime)


class Downtime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bots = []
        self.watchman.start()
        self.bot.coc.add_events(self.maintenance_start, self.maintenance_end)

    def cog_unload(self):
        self.bot.coc.remove_events(self.maintenance_start, self.maintenance_end)
        self.watchman.cancel()

    async def init_bots(self):
        """Initialize self.bots with info from database"""
        self.bots = []  # clear list of any previous entries
        sql = "SELECT bot_id, name, owner_id, channel_id, monitor, email FROM bot_owners ORDER BY name"
        fetch = await self.bot.pool.fetch(sql)
        for row in fetch:
            self.bots.append(Bot(row['name'], row['bot_id'], row['channel_id'], row['owner_id'],
                                 row['monitor'], row['email']))

    @disnake.slash_command(name="bot", description="Command group to manage demo bots", guild_ids=GUILD_IDS)
    @commands.has_role("Admin")
    async def my_bot(self, interaction: disnake.Interaction):
        """ This is just for the slash command group and will never get called on its own, so we can pass. """
        pass

    @my_bot.subcommand(name="test", description="Tests the downtime notification")
    async def my_bot_test(self, interaction: disnake.Interaction, member: disnake.Member):
        """ Tests the downtime notifier for a given bot. """
        self.bot.logger.debug("Starting...")
        sql = "SELECT bot_id, name, owner_id, channel_id, monitor, email FROM bot_owners WHERE bot_id = $1"
        row = await self.bot.pool.fetchrow(sql, member.id)
        if not row:
            await interaction.response.send_message("This bot is not in my DB.", ephemeral=True)
            return
        bot = Bot(row['name'], row['bot_id'], row['channel_id'], row['owner_id'], row['monitor'], row['email'])
        self.bot.logger.debug("About to send notification")
        await bot.notify_down(self.bot)
        await interaction.response.send_message("Test done.", ephemeral=True)

    @my_bot.subcommand(name="add", description="Add a bot to be monitored")
    async def my_bot_add(self, interaction: disnake.Interaction,
                         bot: disnake.User,
                         owner: disnake.User,
                         channel: disnake.TextChannel):
        """ Ads a given bot with a given owner and its demo channel to the database for future monitoring. """
        if not bot.bot:
            return await interaction.response.send_message(f"It would appear that {bot.name} ({bot.id}) is not a "
                                                           f"bot user.")
        if owner.bot:
            return await interaction.response.send_message(f"{owner.name} ({owner.id}) is a bot and cannot be added "
                                                           f"as a bot owner.")

        sql = ("INSERT INTO bot_owners (bot_id, name, owner_id, channel_id) "
               "VALUES ($1, $2, $3, $4)")
        await self.bot.pool.execute(sql, bot.id, bot.name, owner.id, channel.id)
        await interaction.response.send_message(f"Congratulations! You have successfully added {bot.name} to the bot "
                                                f"monitoring system. If there is an outage that lasts more than 60 "
                                                f"seconds, I will ping {owner.display_name} in {channel.mention}.  To "
                                                f"toggle monitoring, please use `/bot monitor <bot tag>.")

    @my_bot.subcommand(name="list")
    async def my_bot_list(self, interaction: disnake.Interaction):
        """List the bots that are being monitored.

        **Example:**
        /bot list"""
        await interaction.response.defer()
        await self.init_bots()
        embeds = []
        for i, bot in enumerate(self.bots):
            if i % 24 == 0:
                embeds.append(disnake.Embed(title="Bots that are configured for monitoring"))
            owner = self.bot.get_user(bot.owner)
            channel = self.bot.get_channel(bot.channel_id)
            embeds[-1].add_field(name=f"{bot.name}",
                                 value=f"Bot ID: {bot.bot_id}\n"
                                       f"Owner: {owner.mention}\n"
                                       f"Channel: {channel.mention}\n"
                                       f"Monitoring: {bot.monitor}",
                                 inline=True)
        if len(embeds) > 1:
            for i, embed in enumerate(embeds):
                embed.title += f" ({i})"
        await interaction.followup.send(embeds=embeds)

    @my_bot.subcommand(name="monitor")
    async def my_bot_monitor(self, interaction: disnake.Interaction, bot: disnake.Member):
        """Toggle monitoring for the specified bot

        **Example:**
        /bot monitor @Ruby
        """
        sql = ("UPDATE bot_owners "
               "SET monitor = NOT monitor "
               "WHERE bot_id = $1 "
               "RETURNING monitor")
        monitor = await self.bot.pool.fetchval(sql, bot.id)
        if monitor:
            new_monitor = "ON"
        else:
            new_monitor = "OFF"
        await interaction.response.send_message(f"Monitoring for {bot.display_name} is now set to {new_monitor}.")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Listen for channel delete and alert admins to remove monitoring if it was a demo channel"""
        if not channel.category_id == 567551986229182474:
            return
        sql = "DELETE FROM bot_owners WHERE channel_id = $1"
        await self.bot.pool.execute(sql, channel.id)
        self.bot.logger.info(f"Bot monitoring has been removed for {channel.name} because someone deleted the channel.")

    @commands.Cog.listener()
    async def on_presence_update(self, before, member):
        """Task for monitoring API bots
        Downtime is stored in the bot_downtime table of postgresql
        """
        # Only monitor updates seen in our Discord server
        if member.guild.id != settings['guild']['junkies']:
            return
        # Is this user a bot?
        if not member.bot:
            return
        # Is this update a status change?
        if before.status == member.status:
            return
        conn = self.bot.pool
        sql = "SELECT bot_id, name, owner_id, channel_id, monitor, email FROM bot_owners WHERE bot_id = $1"
        row = await conn.fetchrow(sql, member.id)
        if not row:
            return
        bot = Bot(row['name'], row['bot_id'], row['channel_id'], row['owner_id'], row['monitor'], row['email'])
        # Are we currently monitoring this bot?
        if not bot.monitor:
            return
        now = datetime.utcnow()
        offline_sql = "SELECT offline_start FROM bot_downtime WHERE online = False AND bot_id = $1"
        reported_sql = ("UPDATE bot_downtime "
                        "SET online = True, reported = True, offline_end = $1 "
                        "WHERE bot_id = $2 AND reported = False")
        insert_sql = ("INSERT INTO bot_downtime (bot_id, online, offline_start, last_notification) "
                      "VALUES ($1, False, $2, $3)")
        offline_start = await conn.fetchval(offline_sql, member.id)
        if offline_start:
            # simply tells us that the bot is marked offline in the database
            if member.status == disnake.Status.online:
                # bot is back online
                downtime = to_time((now - offline_start).total_seconds())
                try:
                    await bot.notify_up(self.bot, downtime)
                    self.bot.logger.info(f"{bot.name} is back online and notification sent. "
                                         f"Downtime: {downtime}")
                except disnake.errors.Forbidden:
                    channel = self.bot.get_channel(settings['channels']['mod-log'])
                    await channel.send(f"API Bot does not have access to <#{bot.channel_id}> ({bot.channel_id})")
                await conn.execute(reported_sql, now, bot.bot_id)
        else:
            if member.status != disnake.Status.online:
                # bot is offline for the first time
                # pause 60 seconds to make sure it's a real outage
                await asyncio.sleep(65)
                check = member.guild.get_member(member.id)
                if check.status == disnake.Status.online:
                    # bot is back online, no need to report anything
                    return
                await conn.execute(insert_sql, bot.bot_id, now, now)
                try:
                    await bot.notify_down(self.bot)
                    self.bot.logger.info(f"{bot.name} is down and notification has been sent.")
                except disnake.errors.Forbidden:
                    channel = self.bot.get_channel(settings['channels']['mod-log'])
                    await channel.send(f"API Bot does not have access to <#{bot.channel_id}> ({bot.channel_id})")

    @tasks.loop(hours=24.0)
    async def watchman(self):
        """Task for monitoring API bots
        Downtime is stored in the bot_downtime table of postgresql
        Bot owner is notified once every 24 hours until the bot comes back online
        """
        conn = self.bot.pool
        now = datetime.utcnow()
        update_sql = "UPDATE bot_downtime SET last_notification = $1 WHERE bot_id = $2 AND online = False"
        sql = "SELECT offline_start, last_notification FROM bot_downtime WHERE bot_id = $1 AND online = False"
        await self.init_bots()
        for bot in self.bots:
            if not bot.monitor:
                continue
            fetch = await conn.fetchrow(sql, bot.bot_id)
            if not fetch:
                continue
            offline_start = fetch['offline_start']
            last_notification = fetch['last_notification']
            if offline_start and last_notification < now - timedelta(hours=23.0):
                downtime = to_time((now - offline_start).total_seconds())
                try:
                    await bot.notify_follow_up(self.bot, downtime)
                except disnake.errors.Forbidden:
                    channel = self.bot.get_channel(settings['channels']['mod-log'])
                    await channel.send(f"API Bot does not have access to <#{bot.channel_id}> ({bot.channel_id})")
                await conn.execute(update_sql, now, bot.bot_id)

    @watchman.before_loop
    async def before_watchman(self):
        await self.bot.wait_until_ready()

    @coc.ClientEvents.maintenance_start()
    async def maintenance_start(self):
        channel = self.bot.get_channel(settings['channels']['general'])
        await channel.send("The Clash API has entered maintenance mode.")

    @coc.ClientEvents.maintenance_completion()
    async def maintenance_end(self, time_started):
        channel = self.bot.get_channel(settings['channels']['general'])
        await channel.send("Maintenance has ended. Get back to work!")


def setup(bot):
    bot.add_cog(Downtime(bot))
