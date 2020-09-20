
import discord

from discord.ext import commands, tasks
from bs4 import BeautifulSoup

API_SUBFORUM_URL = "https://forum.supercell.com/forumdisplay.php/123-Clash-of-Clans-API"
FORUM_BASE_URL = "https://forum.supercell.com/"


class ForumPoster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_post_id = None

    @tasks.loop(minutes=1.0)
    async def forum_post_loop(self):
        async with self.bot.session.get(API_SUBFORUM_URL) as resp:
            html = await resp.text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            recent_posts = soup.find_all(id="threads")
            if not recent_posts:
                return

            post = recent_posts[0]
            if self.last_post_id is None:
                self.last_post_id = post.get("threadbit").get("id")
                return

            embed = discord.Embed()




def setup(bot):
    bot.add_cog(ForumPoster(bot))
