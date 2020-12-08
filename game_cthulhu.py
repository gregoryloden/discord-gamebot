import random

from game_common import GameInstanceBase, GameBase, COMMAND_PREFIX

CTHULHU_COMMAND = COMMAND_PREFIX + "cthulhu"
CTHULU_COMMAND = COMMAND_PREFIX + "cthulu"
START_GAME_COMMANDS = [CTHULHU_COMMAND, CTHULU_COMMAND]
TO_COMMAND = COMMAND_PREFIX + "to"
PASS_COMMAND = COMMAND_PREFIX + "pass"
INVESTIGATE_COMMAND = COMMAND_PREFIX + "investigate"
INVESTIGATE_COMMANDs = [TO_COMMAND, PASS_COMMAND, INVESTIGATE_COMMAND]
GAME_TITLE = "__Don't Mess with Cthulhu__"
HIDDEN_CARD = ":purple_square:"
ELDER_SIGN_CARD = ":yellow_square:"
CTHULHU_CARD = ":green_square:"
BLANK_CARD = ":blue_square:"
ELDER_SIGN_CARD_TEXT = ELDER_SIGN_CARD + " **Elder Sign**"
CTHULHU_CARD_TEXT = CTHULHU_CARD + " **Cthulhu**"
BLANK_CARD_TEXT = BLANK_CARD + " **blank card**"
HAND_CARD_ORDER = [
	(ELDER_SIGN_CARD, ELDER_SIGN_CARD_TEXT),
	(CTHULHU_CARD, CTHULHU_CARD_TEXT),
	(BLANK_CARD, BLANK_CARD_TEXT)
]
TOTAL_ROUNDS = 4

class GameCthulhuInstance(GameInstanceBase):
	def __init__(self, channel, players, cultist_count, extra_roles_count):
		super().__init__()
		self.channel = channel
		self.all_players = players
		self.investigators = []
		self.cultists = []
		self.hands = {}
		self.next_player = None
		self.elder_signs_found = 0
		self.round_progress = 0
		self.current_turn_message = None
		self.current_round = 0

		total_roles_count = len(players) + extra_roles_count
		for player in players:
			if random.random() < cultist_count / total_roles_count:
				self.cultists.append(player)
				cultist_count -= 1
			else:
				self.investigators.append(player)
			total_roles_count -= 1

	async def start_game(self):
		for investigator in self.investigators:
			await investigator.send(GAME_TITLE + ": You are an :blue_square: **Investigator**")
		for cultist in self.cultists:
			await cultist.send(GAME_TITLE + ": You are a :red_square: **Cultist**")
		await self.advance_round()

	async def advance_round(self):
		self.current_round += 1
		player_count = len(self.all_players)
		cards_per_hand = TOTAL_ROUNDS + 2 - self.current_round
		deck = [CTHULHU_CARD] + [ELDER_SIGN_CARD] * (player_count - self.elder_signs_found)
		deck += [BLANK_CARD] * (player_count * cards_per_hand - len(deck))
		self.next_player = self.all_players[int(random.random() * player_count)]
		for player in self.all_players:
			hand = extract_random_hand(cards_per_hand, deck)
			self.hands[player] = hand
			hand_message_contents = []
			for (card_value, card_text) in HAND_CARD_ORDER:
				cards = sum(card is card_value for card in hand)
				if cards > 0:
					hand_message_contents.append(f"**{cards}**x {card_text}")
			hand.insert(0, len(hand))
			await player.send(f"Round {self.current_round}: You have {self.list_phrase(hand_message_contents)}")
		self.current_turn_message = None
		await self.post_game_state(None)

	async def post_game_state(self, last_found_card):
		player_count = len(self.all_players)
		state = [
			"Round {}{}: {}/{} cards flipped, **{}**x {} found total".format(
				self.current_round,
				" concluded" if self.round_progress == player_count else "",
				self.round_progress,
				player_count,
				self.elder_signs_found,
				ELDER_SIGN_CARD_TEXT)
		]
		if last_found_card:
			last_found_card_text = (
				"an " + ELDER_SIGN_CARD_TEXT if last_found_card is ELDER_SIGN_CARD else
				CTHULHU_CARD_TEXT if last_found_card is CTHULHU_CARD else
				"a " + BLANK_CARD_TEXT)
			state.insert(0, "You found " + last_found_card_text + "\n")
		if self.next_player:
			state.append(
				("{}, you investigate next." +
						" To investigate a player, use `{} @player`, `{} @player`, or `{} @player`")
					.format(self.next_player.mention, TO_COMMAND, PASS_COMMAND, INVESTIGATE_COMMAND))
		for player in self.all_players:
			hand = self.hands[player]
			hidden_cards = hand[0]
			hand_contents = [HIDDEN_CARD] * hidden_cards + ["  "] + hand[hidden_cards + 1:] + [": ", player.mention]
			state.append(" ".join(hand_contents))
		if self.current_turn_message:
			await self.current_turn_message.delete()
		self.current_turn_message = await self.channel.send("\n".join(state))

	async def post_end_game_state(self, investigators_won):
		investigators = ":blue_square: **Investigators**"
		cultists = ":red_square: **Cultists**"
		state = [
			"Game over. " + (investigators if investigators_won else cultists) + " win!",
			investigators + ": " + " ".join(investigator.mention for investigator in self.investigators),
			cultists + ": " + " ".join(cultist.mention for cultist in self.cultists)
		]
		await self.channel.send("\n".join(state))

	async def handle_public_message(self, base_command, message):
		#wrong command, the game is still going
		if base_command not in INVESTIGATE_COMMANDs:
			return True

		if message.author.id != self.next_player.id:
			await self.channel.send(message.author.mention + " it is not your turn yet")
			return True
		if len(message.mentions) != 1:
			await self.channel.send(message.author.mention + ", you must investigate one player")
			return True
		to_player_id = message.mentions[0].id
		if to_player_id == message.author.id:
			await self.channel.send(message.author.mention + ", you cannot investigate yourself")
			return True
		to_player = next((player for player in self.all_players if player.id == to_player_id), None)
		if not to_player:
			await self.channel.send(
				message.author.mention + ", that person is not currently playing in this channel")
			return True

		#we found a valid player to investigate
		self.next_player = to_player
		self.round_progress += 1
		hand = self.hands[to_player]
		revealed_card = hand[hand[0]]
		hand[0] -= 1
		if revealed_card is ELDER_SIGN_CARD:
			self.elder_signs_found += 1
		await self.post_game_state(revealed_card)

		#cultists win
		if revealed_card is CTHULHU_CARD:
			await self.post_end_game_state(False)
			return False
		#investigators win
		elif self.elder_signs_found == len(self.all_players):
			await self.post_end_game_state(True)
			return False
		#nothing special, the round hasn't ended
		elif self.round_progress < len(self.all_players):
			return True
		#round is over and we have future rounds, advance to the next round
		elif self.current_round < TOTAL_ROUNDS:
			await self.advance_round()
			return True
		#round is over and it was the last round, cultists win
		else:
			await self.post_end_game_state(False)
			return False

class GameCthulhu(GameBase):
	async def start_new_game(self, base_command, message):
		if base_command not in START_GAME_COMMANDS:
			return None

		contents = message.content.split(" ")
		players_count = len(message.mentions)
		if players_count < 3:
			await message.channel.send(GAME_TITLE + " needs at least 3 players to start")
			return True
		for player in message.mentions:
			if player.bot:
				await message.channel.send(player.mention + " is a bot and cannot play")
				return True

		#automatically determine cultist count, but allow players to override
		#default: 3/4/5/6 get 2, 7,8,9 get 3, etc.
		cultist_count = max((players_count + 2) // 3, 2)
		for content in contents:
			if not content.isdigit():
				continue

			cultist_count = int(content)
			if cultist_count >= players_count:
				await message.channel.send("Please specify a cultist count less than " + str(players_count))
				return True
			break

		#a 3 player game can have 0-2 cultists
		if players_count == 3:
			extra_roles_count = 2
			cultist_count_text = str(max(cultist_count - 2, 0)) + "-" + str(cultist_count)
		elif players_count % 3 == 0:
			extra_roles_count = 0
			cultist_count_text = str(cultist_count)
		else:
			extra_roles_count = 1
			cultist_count_text = str(max(cultist_count - 1, 0)) + " or " + str(cultist_count)

		await message.channel.send(
			"Beginning a(n) " + str(players_count) +
			"-player game of " + GAME_TITLE +
			" with " + cultist_count_text +
			" cultists.")

		instance = GameCthulhuInstance(message.channel, message.mentions, cultist_count, extra_roles_count)
		await instance.start_game()
		return instance
