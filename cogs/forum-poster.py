import re

import aiohttp
import discord

from discord.ext import commands, tasks
from discord.utils import find
from bs4 import BeautifulSoup
from loguru import logger

from config import settings

API_SUBFORUM_URL = "https://forum.supercell.com/forumdisplay.php/123-Clash-of-Clans-API"
FORUM_BASE_URL = "https://forum.supercell.com/"
FORUM_POSTS_CHANNEL_ID = settings['channels']['forum-poster']


class ForumPoster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_post_id = None
        self.session = aiohttp.ClientSession()
        self.forum_post_loop.start()

    def cog_unload(self):
        self.forum_post_loop.cancel()

    @discord.utils.cached_property
    def channel(self):
        return self.bot.get_channel(FORUM_POSTS_CHANNEL_ID)

    @tasks.loop(minutes=15.0)
    async def forum_post_loop(self):
        try:
            await self.bot.wait_until_ready()
            logger.debug("running forum-post loop")

            async with self.session.get(API_SUBFORUM_URL) as resp:
                html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            recent_posts = soup.find(id="threads")
            if not recent_posts:
                logger.warning("couldn't find any posts for the subreddit")
                return

            post = recent_posts.find("li", class_="threadbit")
            post_id = post["id"]
            if self.last_post_id is None:
                self.last_post_id = post_id
                logger.debug(f"running forum-post for the first time, setting last_post_id to {post_id}")
                return
            elif self.last_post_id == post_id:
                logger.debug("forum-post didn't find a new post, returning.")
                return

            # we have ourselves either a new post or a new comment
            number_of_comments = find(lambda x: x.isdigit(), post.li.text)
            title = post.find("h3", class_="threadtitle")
            author = post.find("div", class_="author").span.a
            stats = post.find("ul", class_="threadstats td alt")

            async with self.session.get(FORUM_BASE_URL + title.a['href']) as resp:
                html = await resp.text(encoding="utf-8")

            post_soup = BeautifulSoup(html, "html.parser")

            if number_of_comments == "0":
                content = post_soup.find("div", class_="content").get_text(strip=True)

                embed = discord.Embed(
                    colour=discord.Colour.green(),
                    title=title.get_text(strip=True),
                    url=FORUM_BASE_URL + title.a['href'],
                    description=f"**Comment Author: **[{author.text}]"
                                f"({FORUM_BASE_URL + author['href']})\n\n{content}",
                )

            else:
                comment = post_soup.find_all("div", class_="postdetails")[-1]
                comment_meta, _, author, *_ = comment.parent.find_all("a")
                embed = discord.Embed(
                    colour=discord.Colour.blue(),
                    title=f"**Post Title: **{title.get_text(strip=True)}",
                    url=FORUM_BASE_URL + comment_meta['href'],
                    description=f"**Author: **[{author.text}]"
                                f"({FORUM_BASE_URL + author['href']})\n\n{comment.blockquote.get_text(strip=True)}",
                )

            embed.set_footer(
                text=", ".join(re.sub(r'\s+', '', t) for t in stats.stripped_strings if "Rating" not in t)
            )
            logger.info(f"sending a new post/comment to discord, with info {embed.to_dict()}")
            await self.channel.send(embed=embed)

            logger.debug(f"setting last_post_id to {post_id}")
            self.last_post_id = post_id
        except:
            logger.exception("forum-post loop encountered an exception")


def setup(bot):
    bot.add_cog(ForumPoster(bot))
