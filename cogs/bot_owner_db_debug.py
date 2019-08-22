import logging
import discord
from discord.ext import commands
from helpers import misc
from helpers.converters import license_duration
from helpers.licence_helper import construct_expiration_date

logger = logging.getLogger(__name__)


class BotOwnerDbDebug(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def force_guild_join(self, ctx, guild_prefix):
        """
        Manually add guild to the database
        :param guild_prefix: Every guild will have it's own prefix

        """
        await self.bot.main_db.setup_new_guild(ctx.guild.id, guild_prefix)
        await ctx.send("Done")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def force_new_licensed_member(self, ctx, member: discord.Member, license: discord.Role,
                                        *, license_duration: license_duration):
        expiration_date = construct_expiration_date(license_duration)
        await self.bot.main_db.add_new_licensed_member(member.id, ctx.guild.id, expiration_date, license.id)
        await ctx.send("Done")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def force_delete_licensed_member(self, ctx, member: discord.Member, licensed_role: discord.Role):
        await self.bot.main_db.delete_licensed_member(member.id, licensed_role.id)
        await ctx.send("Done")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def force_get_guild_license_total_count(self, ctx):
        count = await self.bot.main_db.get_guild_license_total_count(10000, ctx.guild.id)
        await ctx.send(count)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def valid(self, ctx, license):
        """
        Checks if passed license is valid

        """
        if await self.bot.main_db.is_valid_license(license, ctx.guild.id):
            await ctx.send("License is valid")
        else:
            await ctx.send(f"License is not valid.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def force_remove_all_guild_data(self, ctx):
        await self.bot.main_db.remove_all_guild_data(ctx.guild.id)
        await ctx.send("Done")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def db(self, ctx):
        """
        Prints entire database
        For testing purposes

        """
        to_print = []
        cur = await self.bot.main_db.connection.cursor()

        async def print_cursor(cursor):
            results = await cursor.fetchall()
            for row in results:
                for record in range(len(row)):
                    to_print.append(f"{row[record]} ")
                to_print.append("\n")

        await cur.execute("SELECT * FROM GUILDS LIMIT 100")
        to_print.append("\nTable GUILDS:\n")
        await print_cursor(cur)

        await cur.execute("SELECT * FROM LICENSED_MEMBERS LIMIT 1000")
        to_print.append("\nTable LICENSED_MEMBERS:\n")
        await print_cursor(cur)

        await cur.execute("SELECT * FROM GUILD_LICENSES LIMIT 10000")
        to_print.append("\nTable GUILD_LICENSES:\n")
        await print_cursor(cur)

        await cur.close()

        string_output = "".join(to_print)
        logger.info(string_output)
        await ctx.send(misc.maximize_size(string_output))


def setup(bot):
    bot.add_cog(BotOwnerDbDebug(bot))