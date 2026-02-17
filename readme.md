## This thing archives channels
As much as I can do with, at least.

It is split up into two parts: the discord bot, and the archive viewer.

## Discord bot setup
The Discord bot is a self-bot that uses discord.py-self. This does mean it breaks TOS, so a fair warning there.

To use it, you must set up an appropriate Python environment, and provide the bot with your account's token.

You'll need around Python 3.10 to run this. If you know how to set up a venv, do that! Otherwise, open the folder this program is in, in a command line. Type `pip install -r requirements.txt`. If no bugs, environment should work.

As of writing, [one method](https://www.reddit.com/r/discordapp/comments/1h7isk5/how_could_i_find_my_discord_token_every_guide/) for attaining your token is:
1. Open Discord in your web browser (discord.com/app).
2. Open developer tools (Control + Shift + I, or F12) and open the Network tab within it.
3. Open a different text channel than the one you already had open (to force it to fetch the messages)
4. In the dev tools, look for the messages?limit=50 request. You can filter Fetch/XHR or search for it, if that helps. Once you've found it, click on the request.
5. Under the 'Headers' section, scroll to 'Request headers', then 'Authorization'. The value of that header is the token.

This token should never be shared, it allows things to access your account without going through any authentication.

Create a file in the same directory as archive_bot.py, name it `token.txt`, and paste your token into that file.

The bot should now work. Run archive_bot.py. It should print that it has connected to Discord with your username after a small while.

## Archiving a channel
To archive a channel, make sure archive_bot.py is running. Send a message into any chatroom anywhere formatted as `P.archive [id_list]`. Replace id_list with as many channel or server IDs as you wish to archive. For example: `P.archive 602625365281603637 1045982708410634270`

These IDs are the snowflakes for the relevant channels or servers. With developer mode enabled on Discord, you can right-click on one, and select `Copy Channel ID` or `Copy Server ID`.

The bot will then go through each ID provided, and fetch all messages and media your account has access to in those. It will place these into the `attachments` folder, and the `archive` folder.

## Viewing the archive
Open `archive_viewer.html` in any web browser, I use Firefox right now. On that page, there's a button to load a folder - select the `archive` folder and upload that. It should be self-explanatory from there.

## Feedback
This is for personal and friend use. If you're one of those, you know how to contact me. If you find an issue or have a suggestion, let me know. I love archival, and would like to make this a decent tool for us.