import os
from pkg_resources import resource_filename
from hearthstone import cardxml
from hearthstone.enums import CardType
from ..logging import log
from ..rules import POISONOUS
from ..utils import get_script_definition


ACTION_SCRIPTS = ("activate", "combo", "deathrattle", "draw", "inspire", "play")
EVENT_SCRIPTS = ("enrage", "events", "in_hand", "update")
EVAL_SCRIPTS = ("cost_mod", "powered_up")


class CardDB(dict):
	def __init__(self, filename):
		self.filename = filename
		self.initialized = False

	def __getitem__(self, *args):
		if not self.initialized:
			self.initialize()
		return super().__getitem__(*args)

	def __iter__(self):
		if not self.initialized:
			self.initialize()
		return super().__iter__()

	@staticmethod
	def merge(id, card):
		"""
		Find the xmlcard and the card definition of \a id
		Then return a merged class of the two
		"""
		carddef = get_script_definition(id)
		if carddef:
			card.scripts = type(id, (carddef, ), {})
		else:
			card.scripts = type(id, (), {})

		for script in ACTION_SCRIPTS:
			actions = getattr(card.scripts, script, None)
			if actions is None:
				# Set the action by default to avoid runtime hasattr() calls
				setattr(card.scripts, script, ())
			elif not hasattr(actions, "__iter__") and not callable(actions):
				# Ensure the actions are always iterable
				setattr(card.scripts, script, (actions, ))

		# TODO: Merge with ACTION_SCRIPTS
		for script in EVENT_SCRIPTS:
			actions = getattr(card.scripts, script, None)
			if actions is None:
				setattr(card.scripts, script, [])
			elif not hasattr(actions, "__iter__") and not callable(actions):
				setattr(card.scripts, script, [actions])

		for script in EVAL_SCRIPTS:
			func = getattr(card.scripts, script, None)
			if func is None:
				setattr(card.scripts, script, None)

		# Set some additional events based on the base tags...
		if card.poisonous:
			card.scripts.events.append(POISONOUS)

		return card

	def initialize(self):
		log.info("Initializing card database")
		self.initialized = True
		if not os.path.exists(self.filename):
			raise RuntimeError("%r does not exist. Create it with `bootstrap`." % (self.filename))

		db, xml = cardxml.load(self.filename)
		for id, card in db.items():
			self[id] = self.merge(id, card)

		log.info("Merged %i cards", len(self))

	def filter(self, **kwargs):
		"""
		Returns a list of card IDs matching the given filters. Each filter, if not
		None, is matched against the registered card database.
		cards.
		Examples arguments:
		\a collectible: Whether the card is collectible or not.
		\a type: The type of the card (hearthstone.enums.CardType)
		\a race: The race (tribe) of the card (hearthstone.enums.Race)
		\a rarity: The rarity of the card (hearthstone.enums.Rarity)
		\a cost: The mana cost of the card
		"""
		if not self.initialized:
			self.initialize()

		cards = self.values()

		if "type" not in kwargs:
			kwargs["type"] = [CardType.SPELL, CardType.WEAPON, CardType.MINION]

		for attr, value in kwargs.items():
			if value is not None:
				# What? this doesn't work?
				# cards = __builtins__["filter"](lambda c: getattr(c, attr) == value, cards)
				cards = [
					card for card in cards if (isinstance(value, list) and
					getattr(card, attr) in value) or getattr(card, attr) == value
				]

		return [card.id for card in cards]


# Here we import every card from every set and load the cardxml database.
# For every card, we will "merge" the class with its Python definition if
# it exists.
if "db" not in globals():
	xmlfile = resource_filename("fireplace", "CardDefs.xml")
	db = CardDB(xmlfile)
	filter = db.filter
