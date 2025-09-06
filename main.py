import discord
from discord.ext import commands
import json
import asyncio


intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def copy(ctx):
    guild = ctx.guild
    server_data = {}

    for category in guild.categories:
        category_data = {
            "channels": []
        }

        for channel in category.channels:
            channel_type = channel.type.name

            category_data["channels"].append({
                "name": channel.name,
                "type": channel_type
            })

        server_data[category.name] = category_data

    with open("server_structure.json", "w", encoding='utf-8') as f:
        json.dump(server_data, f, indent=4, ensure_ascii=False)

    await ctx.send("✅ Server structure copied to `server_structure.json`!")


@bot.command()
async def paste(ctx):
    with open("server_structure.json", "r", encoding='utf-8') as f:
        server_data = json.load(f)

    await ctx.send("⚠️ This will delete all channels except this one and recreate the server layout. Type `yes` to confirm.")

    def check_confirm(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        confirm_msg = await bot.wait_for('message', check=check_confirm, timeout=30.0)
    except asyncio.TimeoutError:
        await ctx.send("❌ Timed out. Aborting paste.")
        return

    if confirm_msg.content.lower() != "yes":
        await ctx.send("❌ Paste cancelled.")
        return

    await ctx.send("🧹 Deleting all other channels and categories...")

    command_channel = ctx.channel
    for channel in ctx.guild.channels:
        if channel != command_channel:
            try:
                await channel.delete()
            except Exception as e:
                print(f"Failed to delete {channel.name}: {e}")

    await ctx.send("✅ Cleared old channels. Starting paste process...")

    for category_name, category_info in server_data.items():
        await ctx.send(f"🔐 What role should have access to **{category_name}**? (Mention role or type `N/A`)")

        def check_role(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await bot.wait_for('message', check=check_role, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Timed out. Skipping this category.")
            continue

        allowed_role = None
        if msg.content.upper() != "N/A":
            if len(msg.role_mentions) > 0:
                allowed_role = msg.role_mentions[0]
            else:
                await ctx.send("⚠️ Invalid role mention. Skipping this category.")
                continue

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }

        if allowed_role:
            overwrites[allowed_role] = discord.PermissionOverwrite(read_messages=True)

        category = await ctx.guild.create_category(name=category_name, overwrites=overwrites)
        await ctx.send(f"📂 Created category: `{category_name}`")

        for channel_info in category_info["channels"]:
            ch_name = channel_info["name"]
            ch_type = channel_info["type"]

            try:
                if ch_type == "text":
                    await ctx.guild.create_text_channel(name=ch_name, category=category)
                elif ch_type == "voice":
                    await ctx.guild.create_voice_channel(name=ch_name, category=category)
                else:
                    await ctx.send(f"⚠️ Unsupported channel type `{ch_type}` for `{ch_name}`. Skipping.")
            except Exception as e:
                await ctx.send(f"❌ Failed to create channel `{ch_name}`: {e}")

    await ctx.send("🎉 Paste complete! Server structure restored.")

bot.run("YOUR TOKEN HERE")
