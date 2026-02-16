import discord
import re
import datetime
from pathlib import Path
import os

# TODO: Sanitize text.
# TODO: Write how-to guide
# TODO: Automatically figure out if server or dm
# TODO: Check weirdness with datetime
# TODO: Provide multiple IDs
# TODO: Make print output less noisy


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

	async def on_ready(self):
		print('Logged on as', self.user)

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
			print("Could not find a server or channel id in the command!")
			return

		for found_id in found_ids:
			# Try get methods first, fetch if that fails, then report error.
			found = self.get_channel(found_id)
			if found:
				await self.archive_channel_command(found)
				continue
			found = self.get_guild(found_id)
			if found:
				await self.archive_guild_command(found)
				continue

			found = await self.fetch_channel(found_id)
			if found:
				await self.archive_channel_command(found)
				continue
			found = await self.fetch_guild(found_id)
			if found:
				await self.archive_guild_command(found)
				continue

			print("Could not find server or channel with id: " + str(found_id))

	async def archive_guild_command(self, guild: discord.Guild):
		try:
			channels = await guild.fetch_channels()
		except (discord.HTTPException, discord.InvalidData) as e:
			print("Failed to fetch channels. Error: " + e)
			return
		print(f"Found {len(channels)} channels: " + str(channels))
		for channel in channels:
			await self.archive_channel_command(channel)

	async def archive_channel_command(self, channel):
		if not self.can_archive_channel(channel):
			print(f"Skipping channel ({channel.id}) of type {type(channel)}")
			return
		await self.archive_channel_history(channel)

	async def archive_channel_history(self, channel):
		grouping_limit = datetime.timedelta(minutes=10)  # A threshold for the range of time messages will be grouped for.
		last_author = ""
		last_date = ""  # The d/m/y of the last message.
		last_datetime = None
		channel_is_server = isinstance(channel, discord.abc.GuildChannel)
		if channel_is_server:
			archive_path = self.get_archive_path_server(channel)
		elif isinstance(channel, discord.GroupChannel):
			archive_path = self.get_archive_path_group(channel)
		else:
			archive_path = self.get_archive_path_dm(channel)

		milestones_every = datetime.timedelta(seconds=30)
		last_update = datetime.datetime.now()
		archive_count = 0

		if channel_is_server:
			user_id = await channel.guild.fetch_member(self.user.id)
			perms = channel.permissions_for(user_id)
			if not perms.read_message_history or not perms.read_messages:
				print(f"Cannot access channel, no permission: {channel.name} ({channel.id})")
				return

		print(f"Archiving channel {channel.name} ({channel.id})...")
		os.makedirs(os.path.dirname(archive_path), exist_ok=True)
		f = open(archive_path, "w", encoding="utf-8")
		f.write(self.html_doc_start)
		async for message in channel.history(limit=None, oldest_first=True):
			archive_count += 1
			if datetime.datetime.now() - last_update >= milestones_every:
				print(f"Archived {archive_count} messages.")
				last_update = datetime.datetime.now()
			m_t = message.created_at  # Datetime object
			m_date = m_t.strftime("%d/%m/%Y")  # Date as a string in my preferred format.
			m_time = m_t.strftime("%H:%M:%S")  # Time as a string in my preferred format.
			time_diff = 0
			if last_datetime is not None:
				time_diff = m_t - last_datetime

			author = str(message.author.display_name)
			msg_format = f'<span><span class="time">{m_time}</span> {message.content}</span>'  # How a message is displayed in my formatting.

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
						print(f"==Attachment Error==\nMessage snowflake: {message.id}\nError: {e}")
				f.write(f"<span>File: {atts_string}</span>\n")
				if atts_tags_string:
					f.write(f"<span>{atts_tags_string}</span>\n")

			last_date = m_date
			last_datetime = m_t
			last_author = author
		f.write("</p></body></html>")
		f.close()
		print(f"Finished archiving channel: {channel.name} ({str(channel.id)})")

	def can_archive_channel(self, channel):
		return isinstance(channel, (discord.VoiceChannel, discord.ForumChannel, discord.DMChannel, discord.TextChannel, discord.GroupChannel))

	# DM authors don't have role colours, so are handled differently.
	def get_author_dm(self, message):
		cls = "otherAuthor"
		if message.author == self.user:
			cls = "botAuthor"
		span = f'<span class="{cls}">{message.author.display_name}</span>\n'
		return span

	def get_author_server(self, message):
		user_color = self.get_user_color(message.author)
		span = f'<span style="color:{user_color}">{message.author.display_name}</span>'
		return span

	def get_user_color(self, user):
		return "#" + hex(user.color.value)[2:]

	def get_archive_path_group(self, channel: discord.GroupChannel):
		name = channel.name
		return Path(".", "archive", "groups", f"{name}.html")

	def get_archive_path_dm(self, channel: discord.DMChannel) -> Path:
		name = channel.recipient.display_name
		return Path(".", "archive", "DMs", f"{name}.html")

	def get_archive_path_server(self, channel: discord.abc.GuildChannel) -> Path:
		if channel.category:
			return Path(".", "archive", "servers", channel.guild.name, channel.category.name, f"{channel.name}.html")
		return Path(".", "archive", "servers", channel.guild.name, f"{channel.name}.html")


client = MyClient()
client.run(TOKEN)