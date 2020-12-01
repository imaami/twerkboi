from discord.ext import commands
from gpt2 import GPT2
#from inferkit import InferKit
from cfg import Cfg
from gear import Gear
import log
import re
import secrets

class TwerkBoi:
	@staticmethod
	def list_tail(arr: []):
		return arr[-1] if (len(arr) > 0) else None

	@staticmethod
	def msg_author_id(msg: {}):
		if (type(msg) == dict) and ('author' in msg) and \
		   (type(msg['author']) == dict) and ('id' in msg['author']):
			return msg['author']['id']
		return None

	@staticmethod
	def is_sentence_end(txt: str):
		tmp = txt.strip()
		c = tmp[-1:]
		if c == '"':
			c = tmp[-2:-1]
		return c == '!' or c == '.' or c == '?'

	def get_command_prefix(self):
		return self._cfg.command_prefix

	def _is_cmd(self, msg):
		return (None != self._cmd_regex.match(msg.content))

	def __init__(self, cfg_file: str = None, **kwargs):

		self._cfg = Cfg(cfg_file, **kwargs)
		self._discord = commands.Bot(self._cfg.command_prefix)
		self._gpt2 = GPT2('gpt2-large', sampling_count = 3)
		#self._inferkit = InferKit(self._cfg.inferkit_api_key)
		self._channels = {}
		self._member_mention = {}
		self._mention_regex = None

		self.init_entropy_store()

		self._discord.add_cog(Gear(self))
		cog = self._discord.get_cog('Gear')
		self._cmd_regex = cog.compile_regex()

		@self._discord.event
		async def on_ready():
			# Get member list sorted in reverse order by lower-case
			# display name. This particular sorting choice ensures
			# that a regex matching any member name will find the
			# longest possible match in case of common prefixes.
			def display_name_lc(m):
				return m.display_name.lower()
			members = list(self._discord.get_all_members())
			members.sort(key=display_name_lc, reverse=True)

			arr = []
			for member in members:
				name = member.display_name
				arr.append(re.escape(name))
				# TODO: handle name collisions
				self._member_mention['@' + name.lower()] = member.mention
			self._mention_regex = re.compile('@((' + '|'.join(arr) + r')|\S*)', flags=re.I)

			user = self._discord.user
			self._name_regex = re.compile(r'(' + re.escape(user.display_name) + r')\]\s*', flags=re.I)
			log.info('Logged in as ' + log.green(str(user), 1))

		@self._discord.event
		async def on_message(msg):
			chan = msg.channel
			is_cmd = self._is_cmd(msg)
			msg_log = self.chan_msg_log(chan.id)

			if len(msg_log) == 0:
				await self.chan_get_history(msg_log, chan)
			else:
				self.chan_append_msg(msg_log, msg, is_cmd, TwerkBoi.list_tail(msg_log))

			await self._discord.process_commands(msg)

			try:
				user = chan.guild.me
			except Exception:
				user = None
			if not user:
				user = self._discord.user

			if msg.author == user:
				if TwerkBoi.is_sentence_end(msg.content):
					return
				if self.get_entropy(4) < 3:
					return

			if is_cmd:
				is_tts = (msg.clean_content[1:4] == 'tts')
				if is_tts:
					is_gen = True
				else:
					is_gen = (msg.clean_content[1:4] == 'gen')
					if not is_gen:
						return
				prefix = msg.clean_content[5:]
			else:
				is_gen = False
				is_tts = False
				prefix = ''

			if len(prefix) > 0:
				log.warn('prefix: ' + prefix)

			#user_id = user.id
			#mentioned = False

			#for member in msg.mentions:
			#	if member.id == user_id:
			#		mentioned = True

			#if (not is_gen) and (not mentioned):
			#	return

			prompt = self.gen_prompt(msg_log, user, prefix)
			#await chan.trigger_typing()
			#reply = self._inferkit.generate(prompt)

			await chan.trigger_typing()

			reply = None
			reply_ends = False

			for attempt in range(0, 10):
				index = 0
				replies = [self.prune_reply(r, prefix, user) \
				           for r in self._gpt2.generate(prompt, 20)]
				for r in replies:
					if r == None:
						r = ''
					else:
						r_ends = TwerkBoi.is_sentence_end(r)
						if reply == None:
							reply = r
							reply_ends = r_ends
						elif r_ends:
							if not reply_ends:
								reply = r
								reply_ends = True
							elif len(r) > len(reply):
								reply = r
					log.info(log.green('-> (' + str(index) + ') ' + r, 1))
					index += 1

				if reply != None:
					break

			if reply == None:
				reply = self._cfg.command_prefix + \
				        'err Unable to generate a reply'

			await chan.send(reply, tts=is_tts)

	def chan_msg_log(self, id: int):
		return self._channels.setdefault(id, [])

	async def chan_get_history(self, msg_log: [], channel):
		hist = await channel.history(limit=256).flatten()
		prev_msg = TwerkBoi.list_tail(msg_log)
		for i in range(len(hist)-1, -1, -1):
			msg = hist[i]
			prev_msg = self.chan_append_msg(msg_log, msg, self._is_cmd(msg), prev_msg)

	def chan_append_msg(self, msg_log: [], msg, is_cmd, prev_msg = None):
		author = msg.author
		clean_content = msg.clean_content
		same_author = (TwerkBoi.msg_author_id(prev_msg) == author.id)

		if same_author:
			fmt_msg = clean_content
		else:
			fmt_msg = ('[' if prev_msg == None else '\n[') \
			          + author.display_name + ']\n' + clean_content

		if is_cmd:
			# Command message: don't log, print w/ different color
			log_entry = prev_msg
			fmt_msg = log.black(fmt_msg, 1)
		elif same_author:
			log_entry = prev_msg
			log_entry['content'].append(msg.content)
			log_entry['clean_content'].append(clean_content)
			log_entry['text'] += '\n' + fmt_msg
		else:
			log_entry = {
				'author': {
					'id': author.id,
					'display_name': author.display_name,
					'name': author.name + '#' + author.discriminator
				},
				'content': [msg.content],
				'clean_content': [clean_content],
				'text': fmt_msg
			}
			msg_log.append(log_entry)

		log.debug(fmt_msg)
		return log_entry

	def msg_log_dump(self, msg_log: []):
		if len(msg_log) < 1:
			text = ''
		else:
			text = msg_log[0]['text']
			for log_entry in msg_log[1:]:
				text += '\n' + log_entry['text']
		return text

	def gen_prompt(self, msg_log: [], author, start_with: str = ''):
		last_msg = TwerkBoi.list_tail(msg_log)
		same_author = (TwerkBoi.msg_author_id(last_msg) == author.id)

		text = self.msg_log_dump(msg_log) + '\n'
		if not same_author:
			text += '\n[' + author.display_name + ']\n'

		#text = self.msg_log_dump(msg_log) + '\n'
		#if not same_author:
		#	text += '\n\n[' + author.display_name + ']\n'
		#elif len(start_with) > 0:
		#	text += '\n'

		pos = -3000 + len(start_with)
		text = text[pos:]
		#log.debug(log.yellow(text) + log.magenta(start_with), end = '')

		return text + start_with

	def sanitize_mentions(self, input: str, filter = [],
	                      keep_redundant = False, keep_unknown = False):
		pos = 0
		output = ''
		filtered = {}
		mentions_seen = {}

		for name in filter:
			filtered['@' + name.lower()] = True

		for m in self._mention_regex.finditer(input):
			span = m.span()
			output += input[pos:span[0]]
			pos = span[1]

			# Group 2 matches mentions of known (valid) usernames.
			# Absence of group 2 means this is a garbage word that
			# begins with '@'. The bot will happily generate these
			# and get into a feedback loop where more than half of
			# its output consists of made-up username mentions.
			# It's usually best to discard anything that looks like
			# a mention unless it's a real user.
			unknown = (m.group(2) == None)
			if unknown and not keep_unknown:
				# discard unknown user mention
				continue

			mention = m.group(0)
			cleaned_mention = mention.lower()
			redundant = (cleaned_mention in mentions_seen)

			if not redundant:
				# mark mention as seen
				mentions_seen[cleaned_mention] = True

			if cleaned_mention in filtered:
				# discard filtered mention
				continue

			if redundant and not keep_redundant:
				# discard redundant mention
				continue

			if not unknown:
				mention = self._member_mention[cleaned_mention]

			output += mention

		output += input[pos:len(input)]

		return {
			'text': output,
			'seen': mentions_seen
		}

	def prune_reply(self, lines, prefix, user, is_gen = False):
		if (len(lines) > 0) and \
		   (len(prefix) > 0) and \
		   not prefix.isspace():
			lines[0] = prefix + lines[0]

		arr = []
		for line in lines:
			if line[0] == '[':
				line = line[1:]
				m = self._name_regex.match(line)
				if m == None:
					break
				span = m.span()[1]
				if span >= len(line):
					continue
				line = line[span:]
			arr.append(line)

		#need_receiver_mention = (self._cfg.auto_mention and (not is_gen))

		#if (not need_receiver_mention) and (len(arr) < 1):
		#	return

		reply = self.sanitize_mentions(' '.join(arr),
		                               [user.display_name])['text']

		#if need_receiver_mention:
		#	if len(reply) > 0:
		#		reply = msg.author.mention + ' ' + reply
		#	else:
		#		reply = msg.author.mention

		if (len(reply) < 1) or reply.isspace():
			reply = None

		return reply

	def init_entropy_store(self):
		self._entropy_store = secrets.randbits(32)
		self._entropy_nbits = 32

	def get_entropy(self, nbits: int):
		# Can't deal with this
		if nbits < 0 or nbits > 32:
			raise ValueError('nbits out of range')

		# Not an error, just stupid
		if nbits == 0:
			return 0

		# Fill entropy store if it has currently less than nbits left
		if self._entropy_nbits < nbits:
			bits = secrets.randbits(32 - self._entropy_nbits)
			self._entropy_store |= bits << self._entropy_nbits
			self._entropy_nbits = 32

		# Yeet the requested bits
		bits = self._entropy_store & ((1 << nbits) - 1)
		self._entropy_store >>= nbits
		self._entropy_nbits -= nbits

		return bits

	def run(self):
		self._discord.run(self._cfg.discord_bot_token)
