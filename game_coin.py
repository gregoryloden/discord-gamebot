import random
import re

from game_common import GameInstanceBase, GameBase, COMMAND_PREFIX

COIN_COMMAND = COMMAND_PREFIX + "coin"
HEADS = "heads"
TAILS = "tails"
HEADS_COMMAND = COMMAND_PREFIX + HEADS
TAILS_COMMAND = COMMAND_PREFIX + TAILS

class GameCoinInstance(GameInstanceBase):
	async def handle_public_message(self, message):
		#wrong command, game is still going
		if message.content != HEADS_COMMAND and message.content != TAILS_COMMAND:
			return True
		await self.conclude(message, message.content == HEADS_COMMAND)
		return False

	@staticmethod
	async def conclude(message, guessed_heads):
		was_heads = random.random() < 0.5
		correct_guess = was_heads == guessed_heads
		await message.channel.send(
			"Result: " + (HEADS if was_heads else TAILS) + ". You " + ("win!" if correct_guess else "lose."))

class GameCoin(GameBase):
	async def start_new_game(self, message):
		if not message.content.startswith(COIN_COMMAND):
			return None

		#the game was started and finished in one command
		contents = re.sub(r"\s+", " ", message.content).split(" ")
		if len(contents) >= 2 and (contents[1] == HEADS or contents[1] == TAILS):
			await GameCoinInstance.conclude(message, contents[1] == HEADS)
			return True

		await message.channel.send("`" + HEADS_COMMAND + "` or `" + TAILS_COMMAND + "`?")
		return GameCoinInstance()
