import random

COMMAND_PREFIX = "!"

class BotUser:
	def __init__(self, name):
		self.name = name
		self.id = object()
		self.mention = "@" + name
		self.bot = False

	async def send(self, message):
		print(f" : {self.name} << {message}")

class ActiveGame:
	@staticmethod
	def extract_random_hand(count, deck):
		hand = []
		for _ in range(0, count):
			next_card_i = int(random.random() * len(deck))
			next_card = deck[next_card_i]
			temp_card = deck.pop()
			if next_card_i < len(deck):
				deck[next_card_i] = temp_card
			hand.append(next_card)
		return hand

	@staticmethod
	def list_phrase(items):
		if len(items) <= 1:
			return items[0]
		elif len(items) == 2:
			return items[0] + " and " + items[1]
		else:
			last_item = items.pop()
			phrase_without_last = ", ".join(items)
			items.append(last_item)
			return phrase_without_last + ", and " + last_item

	async def handle_public_message(self, base_command, message):
		return False

class AvailableGame:
	async def start_new_game(self, base_command, message):
		return None
