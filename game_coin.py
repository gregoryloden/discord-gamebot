import random

from game_common import ActiveGame, AvailableGame, COMMAND_PREFIX

COIN_COMMAND = COMMAND_PREFIX + "coin"
HEADS = "heads"
TAILS = "tails"
GUESSES = [HEADS, TAILS]
HEADS_COMMAND = COMMAND_PREFIX + HEADS
TAILS_COMMAND = COMMAND_PREFIX + TAILS
GUESS_COMMANDS = [HEADS_COMMAND, TAILS_COMMAND]

class GameCoinInstance(ActiveGame):
	async def handle_public_message(self, base_command, message):
		#wrong command, the game is still going
		if base_command not in GUESS_COMMANDS:
			return True
		await self.conclude(message, base_command == HEADS_COMMAND)
		return False

	@staticmethod
	async def conclude(message, guessed_heads):
		was_heads = random.random() < 0.5
		correct_guess = was_heads == guessed_heads
		await message.channel.send(
			"Result: {}. You {}".format(HEADS if was_heads else TAILS, "win!" if correct_guess else "lose."))

class GameCoin(AvailableGame):
	def base_command(self):
		return COIN_COMMAND

	async def share_rules(self, channel):
		await channel.send(
			f"To flip a coin, start the game with `{COIN_COMMAND}`" +
			f" and input your guess with `{HEADS_COMMAND}` or `{TAILS_COMMAND}`." +
			f"\nAlternatively, flip a coin with `{COIN_COMMAND} {HEADS}` or `{COIN_COMMAND} {TAILS}`")

	async def start_new_game(self, base_command, message):
		if base_command != COIN_COMMAND:
			return None

		#the game was started and finished in one command
		contents = message.content.split(" ")
		if len(contents) >= 2 and contents[1] in GUESSES:
			await GameCoinInstance.conclude(message, contents[1] == HEADS)
			return True

		await message.channel.send(f"`{HEADS_COMMAND}` or `{TAILS_COMMAND}`?")
		return GameCoinInstance()
