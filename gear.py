from discord.ext import commands
import log
import re

class Gear(commands.Cog):
	def __init__(self, dad):
		self.dad = dad

	@commands.command()
	async def say(self, ctx, *, arg):
		chan = ctx.message.channel
		await chan.trigger_typing()
		pos = 0
		reply = ''
		for m in self.dad._mention_regex.finditer(arg):
			span = m.span()
			mention = m.group(0)
			reply += arg[pos:span[0]] + \
			         self.dad._member_mention[mention.lower()]
			pos = span[1]
		reply += arg[pos:len(arg)]
		await chan.send(reply)

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
