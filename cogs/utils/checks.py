from nextcord.ext import commands


async def check_guild_permissions(ctx, perms, check=all):
    if await ctx.bot.is_owner(ctx.author):
        return True

    if ctx.guild is None:
        raise commands.CheckFailure('You must be in a guild to run this command!')

    resolved = ctx.author.guild_permissions
    return check(getattr(resolved, name, None) == value for name, value in perms.items())


def manage_messages():
    async def pred(ctx):
        perms = await check_guild_permissions(ctx, {'manage_messages': True})
        if not perms:
            raise commands.CheckFailure('You must have `Manage Messages` permissions to use this command!')
        return True
    return commands.check(pred)
