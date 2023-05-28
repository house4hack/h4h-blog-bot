import telebot
import blogbot_utils as bu
import uuid
import os.path

import json


with open("config.json") as f:
    config = json.load(f)
bot = telebot.TeleBot(config['telegram_bot'])

FOLDER = "./temp_img/"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    print(message)
    bot.reply_to(message, "Howdy, how are you doing?")



@bot.message_handler(commands=['clear'])
def clear_conversation(message):
    bu.clear_conversation(message.from_user.id)
    bot.reply_to(message, "Cleared")

@bot.message_handler(commands=['summary'])
def summary(message):
    conv = bu.get_conversation(message.from_user.id)
    prompt_count, media_count, caption_count = bu.summary_conversation(conv)
    bot.reply_to(message,  f"Prompts {prompt_count}\n Photos {media_count}\n Photos with caption {caption_count}")


@bot.message_handler(commands=['show'])
def show(message):
    
    reply = bu.show_conversation(message.from_user.id)
    bot.reply_to(message, reply)

@bot.message_handler(commands=['delete'])
def delete_wizard(message):
    reply = bu.show_conversation(message.from_user.id)
    bot.reply_to(message, reply + "\n Which item would you like to delete? [0 to cancel]")
    bot.register_next_step_handler(message, delete_item)


def delete_item(message):
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

@bot.edited_message_handler(content_types=['text'])
def handler_function(message):
    bu.edit_message(message.from_user.id, message.message_id, message.text)
    bot.reply_to(message, 'Prompt updated')


@bot.message_handler(commands=['make'])
def process_blog_wizard(message):
    status, status_message = bu.validate_conversation(message.from_user.id)
    reply = bu.show_conversation(message.from_user.id)
    if not status:
        bot.reply_to(message, f'Nope! {status_message}\n' + reply)
    if status:
        bot.reply_to(message, f'Are you sure you want to create a blog entry based on the below? (type yes)\n' + reply)
        bot.register_next_step_handler(message, process_blog)


def process_blog(message):
    if message.text.strip().lower() == 'yes':
        bot.reply_to(message, "Starting, this may take a while")
        bu.process_blog(message.from_user.id)
    else:
        bot.reply_to(message, "ok")


@bot.message_handler(commands=['tasks'])
def show_tasks(message):
    reply = bu.get_tasks(message.from_user.id)
    if reply.strip() == "":
        reply = f"No tasks"
    bot.reply_to(message, reply)


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    fileID = message.photo[-1].file_id
    file_info = bot.get_file(fileID)
    downloaded_file = bot.download_file(file_info.file_path)
    _, ext = os.path.splitext(file_info.file_path)


    fn = FOLDER + f"image-{uuid.uuid4()}{ext}"
    with open(fn, 'wb') as new_file:
        new_file.write(downloaded_file)
    
    bu.add_to_conversation(message.from_user.id,message.message_id, message.caption, fn)
    bot.reply_to(message, "Image added")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    bu.add_to_conversation(message.from_user.id, message.message_id, message.text)
    bot.reply_to(message,"Prompt added")



bot.infinity_polling()


