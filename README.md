H4H Blog Bot
===

[House4Hack](https://www.house4hack.co.za/) or H4H is a makerspace in Centurion, South Africa.  This telegram bot was create to increase visibility of the House4Hack meetups on Tuesday evenings.  The idea is to take a couple of pictures, add optional captions and a short prompt and for ChatGPT to compose a reasonably true account of a project or activity during the makerspace meetup

Details
===
* Uses [OpenAI ChatGPT 3.5](https://platform.openai.com/docs/guides/gpt/chat-completions-api) to generate the contents
* No database required - all data is stored in the file-system
* Uses Jinja2 templates for the prompts and system prompts that can be configured externally and reloaded without restarting the bot
* Supports user specified or random styles (inserted in the system_prompt) to give some variety to the generated contents
* Supports stashing and unstashing of contents to allow for multiple blog posts to be generated in parallel
* Supports editing of prompts and captions
* Supports editing of the generated contents before publishing
* Supports previewing of the generated contents before publishing
* Supports publishing of the generated contents to Wordpress as a draft
* Supports photos and video content (mp4 tested and limited to < 20MB)


Example
===

For example, the following prompt was given to the bot:



![Example Prompt](https://raw.githubusercontent.com/house4hack/h4h-blog-bot/main/docs/prompt.png)

And the following photos:

![Example Photo 1](https://raw.githubusercontent.com/house4hack/h4h-blog-bot/main/docs/altimeter.png)


![Example Photo 2](https://raw.githubusercontent.com/house4hack/h4h-blog-bot/main/docs/electronics.png)

The bot then generated the following blog post:
![Example Blog Post](https://raw.githubusercontent.com/house4hack/h4h-blog-bot/main/docs/wordpress.png)

Installation
===
Development was done in Python 3.10.4

Simply clone the repository and install the requirements:

```bash
pip install -r requirements.txt
```

Configuration
===

Before using the bot, a config.json file needs to be created in the root folder.  A config_example.json file is provided as a template.  The following fields need to be filled in:
```json
{"access_password": "",
 "open_ai_key": "",
 "telegram_bot": "",
 "users": [],
 "wordpress_key": "",
 "wordpress_user": "",
 "wordpress_category":1,
 "wordpress_url": ""}
 ```

 Keys as follows:

    * access_password: Password used to access the bot - specify a password that can be shared with users at the meetup
    * open_ai_key: OpenAI API key
    * telegram_bot: Telegram bot API key (create a bot using BotFather and get the API key)
    * users: List of telegram user IDs that are allowed to use the bot (will be populated automatically when users use the bot for the first time)
    * wordpress_key: Wordpress API key
    * wordpress_user: Wordpress user name that will publish the blog post
    * wordpress_category: Wordpress category ID that will be used for the blog post
    * wordpress_url: Wordpress URL - url for the wordpress site (e.g. https://www.house4hack.co.za)

To get a Wordpress API key - follow [these instructions](https://osomcode.com/create-authentication-wordpress-rest-api-without-plugins/)

Tested using Wordpress version 6.2.2


Usage
===

Password based authentication is used to limit access to the bot.  Once a user enters the correct password, the user ID is added to the config file and the user can use the bot without entering the password again.

The following commands are supported:

- /start or /help - this message
- /clear - clear the contents of the current prompts and photos
- /summary - provides a count of prompts, photos and captions
- /show - more verbose summary of the current prompts and photos
- /delete - delete prompts or photos from the buffer
- /make - generate contents from the promps and photos
- /preview - preview generated contents
- /publish - push the generated contents and photos to wordpress
- /stash - saves the current contents for later retrieval using /unstash
- /stashlist - list the current saved contents
- /unstash - loads stashed contents into the current working buffer
- /reload - reload templates from github
- /style - set the current style

To add a prompt, simply send a text message to the bot.  To add a photo, send a photo to the bot.  To add a caption to a photo, send a text message to the bot with the photo attached.  You can also edit prompts or captions and will be updated in the buffer.

Use /edit or /delete to modify the current buffer.  You can optionally edit the style of the generated contents using /style.  Or update the prompt templates on github and then use /reload to update the templates locally.

The /make command will generate the contents from the prompts and photos.  The /preview command will show the generated contents.  The /publish command will push the generated contents and photos to wordpress as **draft**.


Known limitations
===

Due to the nature of the short prompts and limited context provided, ChatGPT may produce details that are entirely untrue or misleading.  Editing the preview and reading the generated article before publishing is highly recommended!

It is not particularly robust and sometimes fails to follow the instructions about generating the title or placing the photos.  But for this use-case still useful - ymmv.

