from discord.ext import commands
import log
import re

class Gear(commands.Cog):
	def __init__(self, dad):
		self.dad = dad

	@commands.command()
	async def err(self, ctx):
		pass

	@commands.command()
	async def gen(self, ctx):
		pass

	@commands.command()
	async def say(self, ctx, *, arg):
		chan = ctx.message.channel
		await chan.trigger_typing()
		reply = self.dad.sanitize_mentions(arg, keep_redundant = True,
		                                   keep_unknown = True)['text']
		await chan.send(reply)

	@commands.command()
	async def tts(self, ctx):
		pass

	def compile_regex(self):
		arr = self.get_commands()
		def cmd_name(c):
			return c.name
		arr.sort(key=cmd_name, reverse=True)
		return re.compile( \
			r'^'
			+ re.escape(self.dad.get_command_prefix()) \
			+ r'(' \
			+ r'|'.join([re.escape(c.name) for c in arr]) \
			+ r')(\s.*)?$' \
		)
