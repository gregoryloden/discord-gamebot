import discord
import time
import re

from secrets import DISCORD_TOKEN, GUILD_WHITELISTS
from game_common import ActiveGame, BotUser, COMMAND_PREFIX
from game_coin import GameCoin
from game_cthulhu import GameCthulhu

ENDGAME_COMMAND = COMMAND_PREFIX + "endgame"
BOTTEST_COMMAND = COMMAND_PREFIX + "bottest"
BOTSAY_COMMAND = COMMAND_PREFIX + "botsay"

class GameClient(discord.Client):
	def __init__(self, games):
		super().__init__()
		self.available_games = games
		self.active_games = {}
		self.bot_user_map = {}

	async def on_ready(self):
		print("\n================================")
		print(time.strftime("%Y-%m-%d %H:%M:%S"))
		print(str(self.user) + " connected to servers:")
		for guild in self.guilds:
			print("    - " + guild.name + " " + str(guild.id))
			for channel in guild.channels:
				if isinstance(channel, discord.TextChannel):
					print("        #" + channel.name + " " + str(channel.id))
		print("----------------")

	async def on_message(self, message):
		if message.author.id == self.user.id:
			return
		if isinstance(message.channel, discord.DMChannel):
			await self.handle_private_message(message)
		else:
			await self.handle_public_message(message)

	async def handle_public_message(self, message):
		if not message.content.startswith(COMMAND_PREFIX):
			return
		guild_whitelist = GUILD_WHITELISTS.get(message.channel.guild.id, None)
		if guild_whitelist and message.channel.id not in guild_whitelist:
			return

		message.content = re.sub(r"\s+", " ", message.content)
		space_i = message.content.find(" ")
		base_command = message.content if space_i == -1 else message.content[:space_i]

		active_game = self.active_games.get(message.channel.id)
		if active_game:
			if (message.content == ENDGAME_COMMAND
					or not await active_game.handle_public_message(base_command, message)):
				await message.channel.send("🎲 Game concluded.")
				del self.active_games[message.channel.id]
			#speak the message as a bot user
			elif base_command == BOTSAY_COMMAND:
				contents = message.content.split(" ")
				if len(contents) < 3:
					await message.channel.send("Please specify a bot name followed by a command")
					return
				bot_name = contents[1]
				bot_user = self.bot_user_map.get(bot_name)
				if not bot_user:
					await message.channel.send("\"" + bot_name + "\" is not a bot player")
					return
				message.author = bot_user
				message.mentions = []
				new_contents = contents[2:]
				for word in new_contents:
					if not word.startswith("@"):
						continue
					bot_user = self.bot_user_map.get(word[1:])
					if bot_user:
						message.mentions.append(bot_user)
				message.content = " ".join(new_contents)
				await self.handle_public_message(message)
			return

		for available_game in self.available_games:
			game_instance = await available_game.start_new_game(base_command, message)
			if game_instance:
				if isinstance(game_instance, ActiveGame):
					self.active_games[message.channel.id] = game_instance
					await message.add_reaction("🎲")
				return

		#retry the command with bot users
		if base_command == BOTTEST_COMMAND:
			contents = message.content.split(" ")
			if len(contents) < 3 or not contents[1].isdigit():
				await message.channel.send("Please specify a bot count followed by a command")
				return
			bot_users = [BotUser(chr(ord("A") + bot_num)) for bot_num in range(0, int(contents[1]))]
			self.bot_user_map = {bot_user.name: bot_user for bot_user in bot_users}
			message.mentions = bot_users
			message.content = " ".join(contents[2:])
			await self.handle_public_message(message)

	async def handle_private_message(self, message):
		print(f"Private message from {message.author.mention} {message.author}: {message.content}")

client = GameClient(games = [
	GameCthulhu(),
	GameCoin()
])
client.run(DISCORD_TOKEN)
