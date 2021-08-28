import discord
import json
import os
import sys
from discord.ext.commands import command, Bot, Cog
from asyncio import sleep
from discord.ext import commands

CONFIG_PATH = "config.json"
default_config = {
        "token": "[ add bot token here ]",
        "developers": [],
        "replacements": {},
        "prefix": "^",
        "mod_role": 0,
        "blacklist": [],
        "server": 0,
        "mail_channel": 0,
        "from_field": 1,
}

class ModmailBot(Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.last_user = None

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Your Questions"))
        print(F"Signed in as {self.bot.user} ({self.bot.user.id})")

    @Cog.listener("on_message")
    async def on_message(self, message):
        if not isinstance(message.channel, discord.DMChannel) or message.author.id == self.bot.user.id:
            # not a DM, or it's just the bot itself
            return

        channel = self.bot.get_channel(self.config["mail_channel"])
        if not channel:
            print("Mail channel not found! Reconfigure bot!")

        main_guild = self.bot.get_guild(self.config["server"])
        if not main_guild:
            print("Main Server ID is incorrect!  Reconfigure bot!")
            author = message.author
        else:
            author = main_guild.get_member(message.author.id)
            if not author:
                author = message.author

        content = message.clean_content

        embed = discord.Embed()
        embed.set_author(name="{} ({}#{})".format(author.display_name, author.name, author.discriminator),
                         icon_url=author.avatar_url)
        embed.timestamp = message.created_at
        embed.set_footer(text='User ID: {}'.format(author.id))
        embed.color = author.color

        embed.add_field(name="Message", value=content[:1000] or "blank")
        if len(content[1000:]) > 0:
            embed.add_field(name="(Continued)", value=content[1000:])

        await channel.send(content=f"{message.author.id}", embed=embed)

        try:
            await message.add_reaction('📬')
        except discord.ext.commands.errors.CommandInvokeError:
            await message.channel.send('📬')

        self.last_user = author

    async def _shutdown(self):
        await self.bot.logout()
        await self.bot.close()
        self.bot.loop.stop()
    
    @command()
    async def dm(self, ctx, user : discord.User, *, msg):
        if ctx.channel.id != self.config["mail_channel"]:
            return

        main_guild = self.bot.get_guild(self.config["server"])
        if not main_guild:
            print("Main Server ID is incorrect!  Reconfigure bot!")
            return ctx.send('Main Server Unavailable')
        else:
            if str(ctx.message.author.id) in config['replacements']:
                author = main_guild.get_member(config['replacements'][str(ctx.message.author.id)])
                if not author:
                    author = self.bot.user

                try:
                    await ctx.message.add_reaction('🔄')
                except:
                    await ctx.send('🔄')
            else:
                author = main_guild.get_member(ctx.message.author.id)
                if not author:
                    author = self.bot.user

        embed = discord.Embed()

        if self.config["from_field"]:
            embed.set_author(name="Moderator Response".format(author.display_name, author.name, author.discriminator),
                             icon_url=author.avatar_url)
        else:
            embed.set_author(name="Message", icon_url=ctx.channel.guild.icon)

        embed.timestamp = ctx.message.created_at
        embed.color = author.color

        embed.add_field(name="Moderator Response", value=msg[:1000] or "blank", inline=False)
        if len(msg) > 1000:
            embed.add_field(name="(Continued)", value=msg[1000:], inline=False)

        if ctx.message.attachments:
            embed.add_field(name="Attachments", value=", ".join([i.url for i in ctx.message.attachments]))

        await user.send(embed=embed)

        try:
            await ctx.message.add_reaction('📬')
        except:
            await ctx.send('📬')

        self.last_user = user

    @command(aliases=['r'])
    async def reply(self, ctx, *, msg):
        if self.last_user is None:
            await ctx.send("No user to reply to!")
            return
        await self.dm.callback(self, ctx, user=self.last_user, msg=msg)

    @command()
    async def reee(self, ctx, user : discord.User, times : int, *, msg):
        if ctx.author.id not in config["developers"]:
            return
        with ctx.typing():
            for i in range(times):
                if self.config["from_field"]:
                    await user.send(f"From {ctx.author.display_name}: {msg}")
                else:
                    await user.send(msg)
                await sleep(1.25)
            await ctx.message.add_reaction('📬')

    @command()
    async def shutdown(self, ctx):
        if ctx.author.id not in config["developers"]:
            return

        await ctx.send('Shutting down...')
        await self._shutdown()

    @command()
    async def restart(self, ctx):
        if ctx.author.id not in config["developers"]:
            return

        await ctx.send('Restarting...')
        await ctx.message.delete()
        await self._shutdown()
        script = sys.argv[0]
        if script.startswith(os.getcwd()):
            script = script[len(os.getcwd()):].lstrip(os.sep)

        if script.endswith('__main__.py'):
            args = [sys.executable, '-m', script[:-len('__main__.py')].rstrip(os.sep).replace(os.sep, '.')]
        else:
            args = [sys.executable, script]
        os.execv(sys.executable, args + sys.argv[1:])


def write_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent="\t")


def read_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


if not os.path.exists(CONFIG_PATH):
    write_config(default_config)
    print("No config detected; a new one has been written! Please edit config.json then run the bot again.")
    sys.exit(1)

config = read_config()
bot = Bot(config["prefix"], description="A ModMail Bot.")
bot.add_cog(ModmailBot(bot, config))

@bot.command()
async def clean(ctx, limit: int):
  if ctx.author.id not in config["developers"]:
    return
  await ctx.channel.purge(limit=limit+1)
  await ctx.send('Cleared by {}'.format(ctx.author.mention), delete_after=2)

bot.remove_command('help')

@bot.command()
async def help(ctx):
  if ctx.author.id not in config["developers"]:
    return
  embed=discord.Embed(title="ModMail Developer Commands", url="", 
  description="DM - DM's The User \n \nRestart - Rsetarts The Bot \n \nShutdown - Shutsdown The Bot \n \nClean - Cleans A Certain Amount Of Messages", 
  color=discord.Color.blue())
  await ctx.message.delete()
  await ctx.channel.send(embed=embed)

@bot.event
async def on_message(ctx, reason=None):
    prefixes = ["!","@","#","$","%","^","&","*","/","~"]  
    if ctx.content.startswith("modmail"):
      await ctx.channel.send("PM Me For Reports/Concerns :)")
    for prefix in prefixes:
        if ctx.content.startswith(prefix + "modmail"):
            await ctx.channel.send("PM Me For Reports/Concerns :)")
    if ctx.content.startswith("Modmail"):
      await ctx.channel.send("PM Me For Reports/Concerns :)")
    for prefix in prefixes:
        if ctx.content.startswith(prefix + "Modmail"):
            await ctx.channel.send("PM Me For Reports/Concerns :)")
    if ctx.content.startswith("ModMail"):
      await ctx.channel.send("PM Me For Reports/Concerns :)")
    for prefix in prefixes:
        if ctx.content.startswith(prefix + "ModMail"):
            await ctx.channel.send("PM Me For Reports/Concerns :)")
    await bot.process_commands(ctx)

bot.run('')
