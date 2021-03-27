import discord
import pandas as pd
import math
import matplotlib.pyplot as plt
import requests
import time

from datetime import datetime
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
from config import settings


class Response(commands.Cog):
    """Cog to check coc.py response time and report if things are slow"""

    def __init__(self, bot):
        self.bot = bot
        self.clan_tag = "CVCJR89"
        self.player_tag = "PJU928JR"
        self.war_tag = "UGJPVJR"  # Not an actual war tag, just a clan we will use to search for wars
        self.response_check.start()

    def cog_unload(self):
        self.response_check.cancel()

    async def fetch_as_dataframe(self, sql):
        fetch = await self.bot.pool.fetch(sql)
        columns = [key for key in fetch[0].keys()]
        return pd.DataFrame(fetch, columns=columns)

    async def get_response_times(self):
        api_url = "https://api.clashofclans.com/v1/"
        clan_url = api_url + "clans/%23" + self.clan_tag
        player_url = api_url + "players/%23" + self.player_tag
        war_url = api_url + "clans/%23" + self.war_tag + "/currentwar"
        api_token = settings['supercell']['home_token']
        headers = {'Accept': 'application/json', 'Authorization': 'Bearer ' + api_token}
        # clan endpoint
        start = time.perf_counter()
        requests.get(clan_url, headers=headers)
        clan_elapsed_time = (time.perf_counter() - start) * 1000
        # player endpoint
        start = time.perf_counter()
        requests.get(player_url, headers=headers)
        player_elapsed_time = (time.perf_counter() - start) * 1000
        # current war endpoint
        start = time.perf_counter()
        requests.get(war_url, headers=headers)
        war_elapsed_time = (time.perf_counter() - start) * 1000
        return clan_elapsed_time, player_elapsed_time, war_elapsed_time

    @commands.command(name="response")
    async def response_info(self, ctx):
        """Report information on api response times (last 24 hours)"""

        def align(alignment, text, font, color, position):
            if not isinstance(text, str):
                text = str(text)
            text_width, text_height = draw.textsize(text, font)
            if alignment == "center":
                x = position[0] - (text_width / 2)
            elif alignment == "right":
                x = position[0] - text_width
            else:
                x = position[0]
            y = position[1] - (text_height / 2)
            draw.text((x, y), text, fill=color, font=font)

        def round_half_up(n, decimals=0):
            multiplier = 10 ** decimals
            return math.floor(n * multiplier + 0.5) / multiplier

        async with ctx.typing():
            # Get current response times
            clan, player, war = await self.get_response_times()
            # Get historical data from database
            sql = ("SELECT check_time, clan_response, player_response, war_response FROM bot_responses "
                   "WHERE check_time > NOW() - interval  '24 hours'"
                   "ORDER BY check_time DESC")
            # fetch = await self.bot.pool.fetch(sql)
            df = await self.fetch_as_dataframe(sql)
            col1 = df['clan_response']
            col2 = df['player_response']
            col3 = df['war_response']
            # deal with outliers (greater than 250)
            max_clan_index = max_player_index = max_war_index = 0
            max_clan = max_player = max_war = 250
            if col1.max() > 250:
                max_clan_index = col1.idxmax()   # Get index of max value
                max_clan = col1.max()            # store max value
            if col2.max() > 250:
                max_player_index = df.idxmax()[1]
                max_player = col2.max()
            if col3.max() > 250:
                max_war_index = df.idxmax()[2]
                max_war = col3.max()
            # calculate average of all three columns
            avg_response = (df.sum()[0] + df.sum()[1] + df.sum()[2]) / (len(df) * 3)
            max_value = avg_response * 2
            if max_value > 250:
                y_axis_max = math.ceil(max_value/100) * 100
            else:
                y_axis_max = 250
            fig, ax = plt.subplots(figsize=(18, 9))
            ax.set_ylim([0, y_axis_max])
            ax.plot(df['check_time'], df['clan_response'])
            ax.plot(df['check_time'], df['player_response'])
            ax.plot(df['check_time'], df['war_response'])
            if max_clan > y_axis_max:                                     # if max value is higher than
                ax.text(df['check_time'][max_clan_index],                 # the max of y axis add a label for
                        y_axis_max - 25,                                  # the category (outlier)
                        f"{round_half_up(max_clan, decimals=2)}ms",
                        horizontalalignment="center",
                        fontsize="x-large")
            if max_player > y_axis_max:
                ax.text(df['check_time'][max_player_index],
                        y_axis_max - 25,
                        f"{round_half_up(max_player, decimals=2)}ms",
                        horizontalalignment="center")
            if max_war > y_axis_max:
                ax.text(df['check_time'][max_war_index],
                        y_axis_max - 25,
                        f"{round_half_up(max_war, decimals=2)}ms",
                        horizontalalignment="center")
            ax.set(xlabel="Last 24 hours", ylabel="Response Time (ms)")
            ax.legend(["Clan Endpoint", "Player Endpoint", "War Endpoint"])
            ax.grid()
            ax.set_xticklabels([])
            fig.savefig("plot.png")
            # prep data for display
            large_font = ImageFont.truetype("fonts/Aileron-Bold.otf", 54)
            small_font = ImageFont.truetype("fonts/Aileron-Regular.otf", 24)
            img = Image.new("RGB", (1920, 1080), "white")
            draw = ImageDraw.Draw(img)
            plot_img = Image.open("plot.png")
            img.paste(plot_img, (60, 175))
            status_color = (15, 100, 15)  # Green
            status_text = "All is well"
            if clan > 1000 or player > 1000 or war > 1000:
                status_color = (215, 180, 0)
                status_text = "Minor Slowdown"
            if clan > 2000 or player > 2000 or war > 2000:
                status_color = (100, 15, 15)
                status_text = "There is a problem!"
            draw.rectangle([50, 50, 1870, 150], fill=status_color)
            align("center", status_text, large_font, (240, 240, 240), (960, 95))
            align("left", f"Clan Endpoint: {round_half_up(clan, decimals=2)}ms", small_font, (15, 15, 15), (60, 175))
            align("center",
                  f"Player Endpoint: {round_half_up(player, decimals=2)}ms",
                  small_font,
                  (15, 15, 15),
                  (960, 175)
                  )
            align("right", f"War Endpoint: {round_half_up(war, decimals=2)}ms", small_font, (15, 15, 15), (1860, 175))
            img.save("status.png")
            await ctx.send(file=discord.File('status.png'))

    @tasks.loop(minutes=15.0)
    async def response_check(self):
        """Task for monitoring coc.py and coc API response times"""
        clan_list = []
        player_list = []
        war_list = []
        for i in range(4):
            c, p, w = await self.get_response_times()
            clan_list.append(c)
            player_list.append(p)
            war_list.append(w)
        clan = sum(clan_list) / len(clan_list)
        player = sum(player_list) / len(player_list)
        war = sum(war_list) / len(war_list)
        sql = ("INSERT INTO bot_responses (check_time, clan_response, player_response, war_response) "
               "VALUES ($1, $2, $3, $4)")
        await self.bot.pool.execute(sql, datetime.utcnow(), clan, player, war)


def setup(bot):
    bot.add_cog(Response(bot))
