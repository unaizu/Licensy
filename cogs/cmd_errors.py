import traceback
import math
import discord
from discord.ext import commands
from discord.errors import Forbidden
from helpers.errors import RoleNotFound, DefaultGuildRoleNotSet


class CmdErrors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # if command has local error handler, return
        if hasattr(ctx.command, "on_error"):
            return

        # get the original exception
        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.BotMissingPermissions):
            """
            Note that this is only for checks of the command , specifically for bot_has_permissions 
            example @commands.bot_has_permissions(administrator=True)
            It will not work for example if in command role.edit is called but bot doesn't have manage role permission.
            In that case a simple "Forbidden" will be raised.
            """
            missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            _message = f"I need the **{fmt}** permission(s) to run this command."
            await ctx.send(_message)
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send("This command has been disabled.")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown, please retry in {math.ceil(error.retry_after)}s.")
            return

        if isinstance(error, commands.MissingPermissions):
            """
            Note that this is only for checks of the command , example @commands.has_permissions(administrator=True)
            MissingPermissions is raised if check for permissions of the member who invoked the command has failed.
            """
            missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            _message = f"You need the **{fmt}** permission(s) to use this command."
            await ctx.send(_message)
            return

        if isinstance(error, commands.UserInputError):
            await ctx.send("Invalid command input.")
            return

        if isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send("This command cannot be used in direct messages.")
            except discord.Forbidden:
                pass
            return

        if isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission to use this command.")
            return

        if isinstance(error, Forbidden):
            await ctx.send("I don't have the required permissions to do this. Check role hierarchy.")
            return

        if isinstance(error, RoleNotFound):
            await ctx.send(error.message)
            return

        if isinstance(error, DefaultGuildRoleNotSet):
            await ctx.send(f"Trying to use default guild license but: {error.message}")
            return

        error_type = type(error)
        exception_message = f"Ignoring {error_type} exception in command '{ctx.command}':{error}"
        print(f"{exception_message} \n,traceback:")
        traceback.print_exception(error_type, error, error.__traceback__)
        # TODO Send msg in log channel
        await ctx.send(f"Uncaught exception **{error.__class__.__name__}** happened while processing **{ctx.command}**")


def setup(bot):
    bot.add_cog(CmdErrors(bot))