import discord
import re
import datetime
from pathlib import Path
import os
import logging
import pathvalidate
import bleach

# TODO: Write how-to guide
# TODO: Check weirdness with datetime
# TODO: Replace pings with user's name
# TODO: User list, pins, roles, emoji
# TODO: Archived threads in forum
# TODO: Get threads from channels

with open("token.txt", "r") as f:
	TOKEN = f.readline()


class MyClient(discord.Client):
	def __init__(self, **options):
		super().__init__(**options)
		self.html_doc_start = """<!DOCTYPE html>
		<html>
		<body>
		<p>"""
		self.html_doc_end = "</p></body></html>"
		self.logger = logging.getLogger("discord")

	async def on_ready(self):
		printlog(f"Logged on as {self.user}", self.logger, logging.INFO)

	async def on_message(self, message):
		# only respond to ourselves
		if message.author != self.user:
			return

		c = message.content
		if c.startswith("P.archive"):
			await self.archive_command(c)

	async def archive_command(self, message_content: str):
		found_ids = re.findall(r'\d+', message_content)
		if len(found_ids) <= 0:
			printlog("Could not find a server or channel id in the command!", self.logger, logging.WARNING)
			return

		for found_id in found_ids:
			try:
				# Doing fetch rather than bothering with get, because I'll need to fetch anyway.
				try:
					found = await self.fetch_channel(found_id)
					if found:
						await self.archive_channel(found)
						continue
				except discord.NotFound:
					pass
				try:
					found = await self.fetch_guild(found_id)
					if found:
						await self.archive_guild(found)
						continue
				except discord.NotFound:
					pass

				printlog("Could not find server or channel with id: " + str(found_id), self.logger, logging.WARNING)
			except discord.Forbidden as e:
				printlog(f"Could not access id ({found_id}), no permission. Error: {e}", self.logger, logging.WARNING)

	async def archive_guild(self, guild: discord.Guild):
		try:
			channels = await guild.fetch_channels()
		except (discord.HTTPException, discord.InvalidData) as e:
			printlog("Failed to fetch channels. Error: " + e, self.logger, logging.ERROR)
			return
		printlog(f"Found {len(channels)} channels: " + str(channels), self.logger, logging.INFO)
		for channel in channels:
			# Channel needs to be re-fetched, because this does not fill in info like category.
			try:
				channel = await self.fetch_channel(channel.id)
			except discord.Forbidden as e:
				printlog(f"Could not get channel {channel.name} ({channel.id}): No permission. Error: {e}", self.logger, logging.WARNING)
				continue
			await self.archive_channel(channel)
		printlog(f"Finished archiving server: {guild.name} ({guild.id})", self.logger, logging.INFO)

	async def archive_channel(self, channel):
		if not self.can_archive_channel(channel):
			printlog(f"Skipping channel ({channel.id}) of type {type(channel)}", self.logger, logging.INFO)
			return
		# Forums are a weird middle ground. I'd prefer to treat them as their own thing,
		# but that they pretend to be channels complicates things.
		# So, I deal with it here.
		if not isinstance(channel, discord.ForumChannel):
			await self.archive_channel_messages(channel)
		await self.archive_threads(channel)

	async def archive_threads(self, channel: discord.abc.GuildChannel):
		if not self.can_channel_have_threads(channel):
			return
		printlog(f"Archiving threads in channel: {channel.name} ({channel.id})", self.logger, logging.INFO)
		channel_threads = channel.threads  # Ignore IDE, this will work.
		for thread in channel_threads:
			await self.archive_channel_messages(thread)
		try:
			if isinstance(channel, discord.TextChannel):
				async for thread in channel.archived_threads(limit=None, private=True, joined=True):
					await self.archive_channel_messages(thread)
			elif isinstance(channel, discord.ForumChannel):
				async for thread in channel.archived_threads(limit=None):
					await self.archive_channel_messages(thread)
		except Exception as e:
			printlog(f"Failed to get threads in channel: {channel.name} ({channel.id}) - Error: {e}", self.logger, logging.ERROR)

	async def archive_channel_messages(self, channel):
		grouping_limit = datetime.timedelta(minutes=10)  # A threshold for the range of time messages will be grouped for.
		last_author = ""
		last_date = ""  # The d/m/y of the last message.
		last_datetime = None
		thread_or_channel = "channel"
		channel_name = channel.recipient if isinstance(channel, discord.DMChannel) else channel.name
		channel_is_server = isinstance(channel, discord.abc.GuildChannel)
		if channel_is_server:
			archive_path = self.get_archive_path_server(channel)
		elif isinstance(channel, discord.GroupChannel):
			archive_path = self.get_archive_path_group(channel)
		elif isinstance(channel, discord.Thread):
			archive_path = self.get_archive_path_thread(channel)
			thread_or_channel = "thread"
		else:
			archive_path = self.get_archive_path_dm(channel)

		milestones_every = datetime.timedelta(seconds=30)
		last_update = datetime.datetime.now()
		archive_count = 0

		if channel_is_server:
			user_id = await channel.guild.fetch_member(self.user.id)
			perms = channel.permissions_for(user_id)
			if not perms.read_message_history or not perms.read_messages:
				printlog(f"Cannot access channel, no permission: {channel.name} ({channel.id})", self.logger, logging.INFO)
				return

		printlog(f"Archiving {thread_or_channel} {channel_name} ({channel.id}) into {archive_path}", self.logger, logging.INFO)
		os.makedirs(os.path.dirname(archive_path), exist_ok=True)
		f = open(archive_path, "w", encoding="utf-8")
		f.write(self.html_doc_start)
		async for message in channel.history(limit=None, oldest_first=True):
			archive_count += 1
			if datetime.datetime.now() - last_update >= milestones_every:
				printlog(f"Archived {archive_count} messages.", self.logger, logging.INFO)
				last_update = datetime.datetime.now()
			m_t = message.created_at  # Datetime object
			m_date = m_t.strftime("%d/%m/%Y")  # Date as a string in my preferred format.
			m_time = m_t.strftime("%H:%M:%S")  # Time as a string in my preferred format.
			time_diff = 0
			if last_datetime is not None:
				time_diff = m_t - last_datetime

			author = str(message.author.display_name)
			content_sanitized = bleach.clean(message.content)
			msg_format = f'<span class="message"><span class="time">{m_time}</span> {content_sanitized}</span>'  # How a message is displayed in my formatting.

			# If a new day has started, cause a message break.
			if m_date != last_date:
				f.write(f'\n<span class="date">======== {m_date} ========</span>\n')
			if last_author != author or time_diff >= grouping_limit or m_date != last_date:
				if channel_is_server:
					span = self.get_author_server(message)
				else:
					span = self.get_author_dm(message)
				f.write(span)
			f.write(f"{msg_format}\n")

			# Save attached files
			if message.attachments:
				atts_string = ""
				atts_tags_string = ""
				for att in message.attachments:
					try:
						atts_string += f"({att.id}_{att.filename}) "
						fname = f"{att.id}_{att.filename}"
						p = Path("attachments", str(channel.id), fname)
						p.parent.mkdir(parents=True, exist_ok=True)
						with open(p, "w+"):
							pass
						await att.save(p)
						if re.search(r".(png|jpg|gif|jpeg)$", att.filename) is not None:
							atts_tags_string += f"<img src='attachments/{channel.id}/{fname}'>\n"
					except (discord.NotFound, discord.HTTPException) as e:
						printlog(f"==Attachment Error==\nMessage snowflake: {message.id}\nError: {e}", self.logger, logging.ERROR)
				f.write(f"<span class='embed_message'>File: {atts_string}</span>\n")
				if atts_tags_string:
					f.write(f"<span class='embed'>{atts_tags_string}</span>\n")

			last_date = m_date
			last_datetime = m_t
			last_author = author
		f.write(self.html_doc_end)
		f.close()
		printlog(f"Finished archiving {thread_or_channel}: {channel_name} ({str(channel.id)})", self.logger, logging.INFO)

	#region Helper functions
	def can_archive_channel(self, channel):
		return isinstance(channel, (discord.VoiceChannel, discord.DMChannel, discord.ForumChannel, discord.TextChannel, discord.GroupChannel))

	def can_channel_have_threads(self, channel):
		return isinstance(channel, (discord.ForumChannel, discord.TextChannel))

	# DM authors don't have role colours, so are handled differently.
	def get_author_dm(self, message):
		cls = "otherAuthor"
		if message.author == self.user:
			cls = "botAuthor"
		span = f'<span class="{cls} message_author">{message.author.display_name}</span>\n'
		return span

	def get_author_server(self, message):
		user_color = self.get_user_color(message.author)
		span = f'<span class="message_author" style="color:{user_color}">{message.author.display_name}</span>\n'
		return span

	def get_user_color(self, user):
		return "#" + hex(user.color.value)[2:]

	def get_archive_path_group(self, channel: discord.GroupChannel):
		name = pathvalidate.sanitize_filename(channel.name)
		return Path(".", "archive", "groups", f"{name}.html")

	def get_archive_path_dm(self, channel: discord.DMChannel) -> Path:
		name = pathvalidate.sanitize_filename(channel.recipient.display_name)
		return Path(".", "archive", "DMs", f"{name}.html")

	def get_archive_path_server(self, channel: discord.abc.GuildChannel) -> Path:
		channel_name = pathvalidate.sanitize_filename(f"{str(channel.position).zfill(3)}-{channel.name}")
		server_name = pathvalidate.sanitize_filename(f"{channel.guild.name}")
		if channel.category:
			category_name = pathvalidate.sanitize_filename(f"{str(channel.category.position).zfill(3)}-{channel.category.name}")
			return Path(".", "archive", "servers", server_name, category_name, f"{channel_name}.html")
		return Path(".", "archive", "servers", server_name, f"{channel_name}.html")

	def get_archive_path_thread(self, thread: discord.Thread) -> Path:
		server_name = pathvalidate.sanitize_filename(thread.guild.name)
		thread_name = pathvalidate.sanitize_filename(f"{int(thread.created_at.timestamp())}-{thread.name}.html")
		p = Path(".", "archive", "servers", server_name)
		if thread.category:
			category_name = pathvalidate.sanitize_filename(f"{str(thread.category.position).zfill(3)}-{thread.category.name}")
			p = p / category_name
		if thread.parent:
			channel_name = pathvalidate.sanitize_filename(f"{str(thread.parent.position).zfill(3)}-{thread.parent.name}-threads")
			p = p / channel_name
		p = p / thread_name

		return p
	#endregion


# Prints to console, also logs.
# I do this because the library I use spams the console otherwise.
# There may be a way to set up a separate logger for myself and join them,
# but this is faster and simpler.
def printlog(message, logger: logging.Logger, level):
	print(message)
	logger.log(level, message)


def main():
	client = MyClient()
	logger = logging.getLogger("discord")
	formatter = logging.Formatter("%(asctime)s | %(name)s |  %(levelname)s: %(message)s")
	logger.setLevel(logging.INFO)

	file_handler = logging.FileHandler(filename='archiver.log', encoding='utf-8', mode='w')
	file_handler.setLevel(logging.DEBUG)
	file_handler.setFormatter(formatter)

	console_handler = logging.StreamHandler()
	console_handler.setLevel(logging.ERROR)
	console_handler.setFormatter(formatter)

	logger.addHandler(file_handler)
	logger.addHandler(console_handler)

	printlog("Connecting to Discord...", logger, logging.INFO)
	client.run(TOKEN, log_handler=None)


if __name__ == "__main__":
	main()
