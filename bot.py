import sys
import logging
import asyncio
import traceback

import discord
from discord.ext import commands

from helpers.misc import maximize_size
from database_handler import DatabaseHandler
from helpers import logger_handlers, embed_handler
from helpers.licence_helper import get_current_time

from webserver import keep_alive
import json
import os
from dotenv import load_dotenv

load_dotenv()

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(logger_handlers.get_console_handler())
root_logger.addHandler(logger_handlers.get_file_handler())
logger = logging.getLogger("discord")
logger.setLevel(logging.WARNING)

startup_extensions = [
    "licenses",
    "bot_owner_commands",
    "guild",
    "bot_information",
    "help",
    "cmd_errors",
    # Removed because a lot of users are asking about the token when they don't even need this cog.
    # If you need it then re-enable it.
    # "top_gg_api",
]


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        # convert the developers string to json
        developers = json.loads(os.getenv('DEVELOPERS'))
        myconfig = {
            "bot_description": os.getenv('DISCORD_BOT_DESCRIPTION'),
            "default_prefix": "!",
            "developer_log_channel_id": int(os.getenv('DEV_LOG_CHANNEL_ID')),
            "developers": developers,
            "maximum_unused_guild_licences": 100,
            "support_channel_invite": os.getenv('DISCORD_SUPPORT_CHANNEL_INVITE'),
            "token": os.getenv('DISCORD_BOT_SECRET'),
            "top_gg_api_key": os.getenv('TOG_GG_API_KEY')
        }
        self.config = myconfig
        self.main_db = asyncio.get_event_loop().run_until_complete(DatabaseHandler.create_instance())
        self.up_time_start_time = get_current_time()
        super(Bot, self).__init__(
            command_prefix=self.prefix_callable,
            help_command=None,
            description=self.config["bot_description"],
            case_insensitive=True,
            intents=discord.Intents(guilds=True, members=True, messages=True, reactions=True),
            **kwargs
        )

    async def prefix_callable(self, bot_client, message):
        try:
            # TODO: Store this in list or something so we don't waste calls to db for each message
            return await bot_client.main_db.get_guild_prefix(message.guild.id)
        except Exception as err:
            """
            If fetching prefix from database errors just use the default prefix.
            This is also used in DMs where the guild is None
            """
            default_prefix = self.config["default_prefix"]
            if message.guild is not None:
                # Don't spam the log if it's DMs
                # We only want to log it in case guild prefix is missing
                root_logger.error(f"Can't get guild {message.guild} prefix. Error:{err}. "
                                  f"Using '{default_prefix}' as prefix.")
            return default_prefix

    async def on_ready(self):
        root_logger.info(
            f"Logged in as: {self.user.name} - {self.user.id}"
            f"\tDiscordPy version: {discord.__version__}"
        )
        root_logger.info("Successfully logged in and booted...!")

    @staticmethod
    async def on_connect():
        root_logger.info("Connection to Discord established")

    @staticmethod
    async def on_guild_remove(guild):
        root_logger.info(f"Left guild {guild.name}")

    @staticmethod
    async def on_disconnect():
        root_logger.warning("Connection lost")

    async def on_error(self, event: str, *args, **kwargs):
        """
        Called when an EVENT raises an uncaught exception

        This doesn't use the same event system as the rest of events despite being documented as such.
        Can only have one and it's gotta be in main file.
        """
        exc_info = sys.exc_info()
        exc_type = exc_info[0].__name__ if exc_info[0] is not None else "<no exception>"
        exc_what = str(exc_info[1]) if exc_info[1] is not None else ""
        log_message = f"Uncaught {exc_type} in '{event}': {exc_what}\n{traceback.format_exc()}"
        await self.send_to_log_channel(log_message, title="on_error exception!")

    async def send_to_log_channel(self, message: str, *, title: str, ctx=None):
        """
        Logs passed message to logger as critical and sends the said message to bot log channel, if one is found.
        :param message: Message with error/traceback
        :param title: Title for message
        :param ctx: optional, if passed will be used to add additional info to message embed footer
        """
        root_logger.critical(f"{title}\n{message}")
        if self.is_ready():
            log_channel = self.get_channel(self.config["developer_log_channel_id"])
            embed = embed_handler.simple_embed(maximize_size(message), title, discord.Colour.red())
            if ctx is not None:
                guild_id = "DM" if ctx.guild is None else ctx.guild.id
                footer = f"Guild: {guild_id}    Author: {ctx.author}    Channel: {ctx.channel.id}"
                embed.set_footer(text=footer)
            if log_channel is not None:
                await log_channel.send(embed=embed)


if __name__ == "__main__":
    bot = Bot()
    root_logger.info("Loaded extensions:")
    for extension in startup_extensions:
        cog_path = f"cogs.{extension}"
        try:
            bot.load_extension(cog_path)
            root_logger.info(f"\t{cog_path}")
        except Exception as e:
            exc = f"{type(e).__name__}: {e}"
            root_logger.error(f"{exc} Failed to load extension {cog_path}")
            traceback_msg = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            root_logger.warning(traceback_msg)
    TOKEN = os.getenv('DISCORD_BOT_SECRET')
    keep_alive()
    bot.run(TOKEN)

