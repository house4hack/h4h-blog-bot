import telebot
import blogbot_utils as bu
import uuid
import os.path
import queue
import blogprocessor as bp
import json


with open("config.json") as f:
    config = json.load(f)
bot = telebot.TeleBot(config['telegram_bot'])

work_queue = queue.Queue()
worker = bp.BlogProcessorWorker(work_queue, config)
worker.daemon = True
worker.start()

FOLDER = "./temp_img/"


def validate_user(config, message):
    '''Returns true if the user is in the config file, otherwise asks for the password'''
    if message.from_user.id in config["users"]:
        return True
    else:
        bot.reply_to(message, "Access denied - enter the password to get access")
        bot.register_next_step_handler(message, check_password)
        return False
    
def check_password(message):
    '''Checks the password and adds the user to the config file if correct'''
    if message.text == config['access_password']:
        config['users'].append(message.from_user.id)
        with open("config.json","w") as f:
            json.dump(config, f)
        bot.reply_to(message, "Added to access list")
    else:
        bot.reply_to(message, "Access denied - enter the password to get access")
        bot.register_next_step_handler(message, check_password)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    '''Sends the help message'''
    if validate_user(config, message):
        with open("commands.md") as f:
            commands = f.readlines()
        bot.reply_to(message, "".join(commands))



@bot.message_handler(commands=['preview'])
def show_preview(message):
    '''Shows the preview of the blog entry'''
    if validate_user(config, message):
        title = bu.get_title(message.from_user.id)
        contents = bu.get_contents(message.from_user.id)
        bot.reply_to(message, f"{title}\n\n{contents}")


@bot.message_handler(commands=['clear'])
def clear_conversation(message):
    '''Clears the conversation'''
    if validate_user(config, message):
        bu.clear_conversation(message.from_user.id)
        bot.reply_to(message, "Cleared")

@bot.message_handler(commands=['summary'])
def summary(message):
    '''Shows the summary of the conversation'''
    if validate_user(config, message):
        conv = bu.get_conversation(message.from_user.id)
        prompt_count, media_count, caption_count = bu.summary_conversation(conv)
        bot.reply_to(message,  f"Prompts {prompt_count}\n Photos {media_count}\n Photos with caption {caption_count}")


@bot.message_handler(commands=['show'])
def show(message):
    '''Shows the conversation'''
    if validate_user(config, message):
        reply = bu.show_conversation(message.from_user.id)
        bot.reply_to(message, reply)

@bot.message_handler(commands=['delete'])
def delete_wizard(message):
    '''Starts the delete wizard'''
    if validate_user(config, message):
        reply = bu.show_conversation(message.from_user.id)
        bot.reply_to(message, reply + "\n Which item would you like to delete? [0 to cancel]")
        bot.register_next_step_handler(message, delete_item)


def delete_item(message):
    '''Deletes the item, called by the delete wizard'''
    if validate_user(config, message):

        if message.text != '0':
            success = bu.remove_item(message.from_user.id, message.text)
            if success:
                status = "Deleted"
            else:
                status = "Failed deleting "
            reply = bu.show_conversation(message.from_user.id)
            bot.reply_to(message, f'{status} {message.text}\n' + reply)
        else:
            bot.reply_to(message, "Cancelled")

@bot.message_handler(commands=['edit'])
def edit_wizard(message):
    '''Starts the edit wizard'''
    if validate_user(config, message):

        reply_list = bu.show_conversation_as_list(message.from_user.id)

        if bu.get_status(message.from_user.id) != "Draft":
            title_item = len(reply_list) +1 
            contents_item = len(reply_list) + 2

            reply_list.append(f"{title_item}. Title: "+bu.get_title(message.from_user.id))
            reply_list.append(f"{contents_item}. Contents: "+bu.get_contents(message.from_user.id)[:50]+"...")
        else:
            title_item = 0
            contents_item = 0

        reply = "\n".join(reply_list)
        reply += "\n"
        bot.reply_to(message, reply + "\n Which item would you like to edit? [0 to cancel]")
        bot.register_next_step_handler(message, edit_item, contents_item, title_item)

def edit_item(message, contents_item, title_item):
    '''Edits the item, called by the edit wizard'''
    if validate_user(config, message):

        if message.text.strip() == '0':
            bot.reply_to(message, "Cancelled")
        elif int(message.text) < title_item:
            bot.reply_to(message, "What would you like to change it to?")
            bot.register_next_step_handler(message, edit_item2, message.text)
        elif message.text == str(title_item):
            bot.reply_to(message, "What would you like to change the title to?")
            bot.register_next_step_handler(message, edit_title)
        elif message.text == str(contents_item):
            reply = bu.get_contents(message.from_user.id)
            bot.reply_to(message, 'Below is the current contents, what would you like to change it to? (0 to cancel):\n' )
            bot.send_message(message.from_user.id, reply)
            bot.register_next_step_handler(message, edit_contents)

def edit_item2(message, item):
    '''Edits the item, called by the edit wizard'''
    if validate_user(config, message):

        success = bu.edit_item(message.from_user.id, item, message.text)
        if success:
            status = "Edited"
        else:
            status = "Failed editing "
        reply = bu.show_conversation(message.from_user.id)
        bot.reply_to(message, f'{status} {item}\n' + reply)

def edit_title(message):
    '''Edits the title, called by the edit wizard'''
    if validate_user(config, message):

        success = bu.set_title(message.from_user.id, message.text)
        if success:
            status = "Edited"
        else:
            status = "Failed editing "
        title = bu.get_title(message.from_user.id)
        contents = bu.get_contents(message.from_user.id)
        reply = f"Title: {title}\nContents: {contents[:20]}..."
        bot.reply_to(message, f'{status} title\n' + reply)

def edit_contents(message):
    '''Edits the contents, called by the edit wizard'''
    if validate_user(config, message):

        if message.text.strip() == '0':
            bot.reply_to(message, "Cancelled")
        else:
            success = bu.set_contents(message.from_user.id, message.text)
            if success:
                status = "Edited"
            else:
                status = "Failed editing "
            title = bu.get_title(message.from_user.id)
            contents = bu.get_contents(message.from_user.id)
            reply = f"Title: {title}\nContents: {contents[:20]}..."
            bot.reply_to(message, f'{status} contents\n' + reply)


@bot.edited_message_handler(content_types=['text'])
def handle_textedit_function(message):
    '''Handles the editing of text messages'''
    if validate_user(config, message):

        bu.edit_message(message.from_user.id, message.message_id, message.text)
        bot.reply_to(message, 'Prompt updated')

@bot.edited_message_handler(content_types=['photo'])
def handle_captionedit_function(message):
    '''Handles the editing of captions'''
    if validate_user(config, message):

        bu.edit_message(message.from_user.id, message.message_id, message.caption)
        bot.reply_to(message, 'Prompt updated')


@bot.message_handler(commands=['make'])
def process_blog_wizard(message):
    '''Starts the blog processing wizard'''
    if validate_user(config, message):

        status, status_message = bu.validate_conversation(message.from_user.id)
        reply = bu.show_conversation(message.from_user.id)
        if not status:
            bot.reply_to(message, f'Nope! {status_message}\n' + reply)
        if status:
            bot.reply_to(message, f'Are you sure you want to create a preview based on the below? (type yes)\n' + reply)
            bot.register_next_step_handler(message, process_blog)


def process_blog(message):
    '''Processes the blog, called by the blog processing wizard'''
    if validate_user(config, message):

        if message.text.strip().lower() == 'yes':
            bot.reply_to(message, "Starting, this may take a while")
            bu.process_blog(message.from_user.id, work_queue)
        else:
            bot.reply_to(message, "ok")



@bot.message_handler(commands=['publish'])
def publish_blog_wizard(message):
    '''Starts the blog publishing wizard'''
    if validate_user(config, message):

        status, status_message = bu.validate_conversation(message.from_user.id)
        reply = bu.show_conversation(message.from_user.id)
        if not status:
            bot.reply_to(message, f'Nope! {status_message}\n' + reply)
        if status:
            bot.reply_to(message, f'Are you sure you want to create a blog entry based on the below? (type yes)\n' + reply)
            bot.register_next_step_handler(message, publish_blog)


def publish_blog(message):
    '''Publishes the blog, called by the blog publishing wizard'''
    if validate_user(config, message):

        if message.text.strip().lower() == 'yes':
            bot.reply_to(message, "Publishing, this may take a while")
            bu.publish_blog(message.from_user.id, work_queue)
        else:

            bot.reply_to(message, "ok")




@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    '''Handles the adding of photos'''
    if validate_user(config, message):

        fileID = message.photo[-1].file_id
        file_info = bot.get_file(fileID)
        downloaded_file = bot.download_file(file_info.file_path)
        _, ext = os.path.splitext(file_info.file_path)


        fn = FOLDER + f"image-{uuid.uuid4()}{ext}"
        with open(fn, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        bu.add_to_conversation(message.from_user.id,message.message_id, message.caption, fn)
        bot.reply_to(message, "Image added")

@bot.message_handler(commands=['stash'])
def stash_handler(message):
    '''Stashes the conversation'''
    if validate_user(config, message):    
        token = bu.stash(message.from_user.id)
        bu.clear_conversation(message.from_user.id)
        bot.reply_to(message, f"Stashed:{token}")  


@bot.message_handler(commands=['stashlist'])
def stash_handler(message):
    '''Shows the list of stashes'''
    if validate_user(config, message):    
        bot.reply_to(message, bu.stash_list(message.from_user.id))

@bot.message_handler(commands=['unstash'])
def unstash_wizard(message):
    '''Starts the unstash wizard'''
    if validate_user(config, message):    
        prompt_count, photo_count, caption_count =  bu.summary_conversation_for_user(int(message.from_user.id))
        count = prompt_count + photo_count + caption_count
        if count > 0:
            bot.reply_to(message, "You have unsaved items in your conversation. Please /stash or /clear before unstashing")
        else:
            bot.reply_to(message, "Select the item you wish to unstash (0 to cancel):\n" + bu.stash_list(message.from_user.id))
            bot.register_next_step_handler(message, unstash_handler)

def unstash_handler(message):
    '''Unstashes the item, called by the unstash wizard'''
    if validate_user(config, message):    
        if message.text != '0':
            bu.unstash(message.from_user.id, message.text)
            bot.reply_to(message, "Unstashed")
        else:
            bot.reply_to(message, "Cancelled")
        





@bot.message_handler(content_types=['text'])
def handle_text(message):
    '''Handles the adding of text messages'''
    if validate_user(config, message):
        bu.add_to_conversation(message.from_user.id, message.message_id, message.text)
        bot.reply_to(message,"Prompt added")




bot.infinity_polling()


