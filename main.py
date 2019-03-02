#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 19 12:27:26 2018

@author: Milan Roberson
"""

import logging
import pickle
from signal import SIGINT, SIGTERM, SIGABRT

import telegram
from telegram.ext import (Updater, CommandHandler, ConversationHandler,
                            RegexHandler, MessageHandler, Filters,
                            CallbackContext, CallbackQueryHandler)
from telegram import (ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, Update)
from telegram.error import (TelegramError, Unauthorized, BadRequest, TimedOut,
                            ChatMigrated, NetworkError)
from api_key import TOKEN

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

class HABot(object):
    ha_ids = []
    ha_chat_ids = []
    ha_names = []
    has = {}
    cases = {}

CHOOSING, SUMMON, INFO, WAITING, HEALTHAD = range(5)

emergency_warning = "If this is an emergency, call 626-395-5000 if you are on campus, and 911 otherwise."


need_am_keyboard = ReplyKeyboardMarkup([["I need a Health Ad"],["I am a Health Ad"]],
            one_time_keyboard=True)

response_keyboard = ReplyKeyboardMarkup([["I can respond"],["I cannot respond"]],
            one_time_keyboard=True)

r_IL_KB = InlineKeyboardMarkup([[InlineKeyboardButton("I can respond", callback_data=1)],
    [InlineKeyboardButton("I cannot respond", callback_data=0)]])

def start(update: Update, context: CallbackContext):
    update.message.reply_text(emergency_warning, reply_markup=need_am_keyboard)
    return CHOOSING

def healthad(update: Update, context: CallbackContext):
    update.message.reply_text(emergency_warning)
    return name_loc(bot, update, user_data)

def healthad_public(update: Update, context: CallbackContext):
    update.message.reply_text(emergency_warning)
    try:
        logging.info("trying to send PM")
        context.bot.send_message(chat_id=update.message.from_user.id,
                text = "You need a Health Ad.",
                reply_markup = need_am_keyboard)
        return SUMMON
        # send them a pm
    except TelegramError:
        logging.info("oops, they need to pm us first")
        update.message.reply_text("Start a conversation at t.me/HealthAdBot to summon a health ad.")

def name_loc(update: Update, context: CallbackContext):
    update.message.reply_text("Name and location of person in need?")
    return SUMMON

def need_am_handler(update: Update, context: CallbackContext):
    if (update.message.text == "I need a Health Ad"):
        return name_loc(update, context)
    else:
        if update.effective_user.id not in HABot.ha_ids:
            user = update.effective_user
            HABot.ha_ids.append(user.id)
            HABot.ha_chat_ids.append(update.message.chat_id)
            name = ""
            if user.first_name is not None:
                name += user.first_name
                if user.last_name is not None:
                    name += " " + user.last_name
            if name == "":
                name = user.username;
            HABot.ha_names.append(name)
            HABot.has[str(user.id)] = name
            update.message.reply_text("Thank you, " + name + ". You have been registered as a Health Ad!")
            logging.info(name + " registered as a Health Ad")
            logging.info(HABot.ha_ids)
            logging.info(HABot.ha_chat_ids)
            logging.info(HABot.ha_names)
        else:
            update.message.reply_text("I know")
        return HEALTHAD

        # I am a Health Ad. Register me to get alerts.

def summon(update: Update, context: CallbackContext):
    case_id = hash(update.message.text)
    context.user_data["id"] = case_id
    context.user_data["name_loc"] = update.message.text
    context.user_data["chat_id"] = update.effective_user.id
    HABot.cases[str(case_id)] = context.user_data
    logging.info('summoning health ads for ' + update.message.text)
    for HA_id in HABot.has.keys():
        context.bot.send_message(chat_id=HA_id,
                reply_markup = r_IL_KB,
                text = "Health Ad needed: " + context.user_data["name_loc"])

    # summon health ads
    update.message.reply_text("Health Ads have been notified. " +
                "Can you tell me a bit about what's wrong?")
    return INFO

def info_handler(update: Update, context: CallbackContext):
    if "info" in context.user_data.keys():
        context.user_data["info"] += "\n" + update.message.text
    else:
        context.user_data["info"] = update.message.text
    HABot.cases[context.user_data["id"]] = context.user_data
    for HA_id in HABot.has.keys():
        context.bot.send_message(chat_id=HA_id,
                text = "More info about " + context.user_data["name_loc"] +
                ": " + context.user_data["info"])
    # pass info along
    update.message.reply_text("This information was passed")
    logging.info("passing info " + update.message.text)
    return INFO

def response_cb_handler(update: Update, context: CallbackContext):
    if (int(update.callback_query.data)):
        handled_case = None
        for case_id, case in HABot.cases.items():
            if case["name_loc"] in update.callback_query.message.text:
                handled_case = case
        if handled_case is None:
            update.message.reply_text("Please reply to a message regarding a case.")
        else:
            update.callback_query.edit_message_text(update.callback_query.message.text + "\nGreat, thanks!")
            for HA_id in HABot.has.keys():
                if int(HA_id) != update.effective_user.id:
                    context.bot.send_message(chat_id = int(HA_id),
                            text = "Someone is handling " + handled_case["name_loc"])
            context.bot.send_message(chat_id = handled_case["chat_id"],
                    text = HABot.has[str(update.effective_user.id)] + " is on their way")
    else:
        update.callback_query.edit_message_text(update.callback_query.message.text + "\nNo problem. Let me know if you change your mind.",
                reply_markup = r_IL_KB)
                #reply_markup = response_keyboard)

def response_handler(update: Update, context: CallbackContext):
    if (update.message.text == "I can respond"):
        handled_case = None
        if update.message.reply_to_message is None:
            update.message.reply_text("Please reply to a message regarding a case.")
            return
        for case_id, case in HABot.cases.items():
            if case["name_loc"] in update.message.reply_to_message.text:
                handled_case = case
        if handled_case is None:
            update.message.reply_text("Please reply to a message regarding a case.")
        else:
            update.message.reply_text('Great, thanks!')
            for HA_id in HABot.has.keys():
                if int(HA_id) != update.effective_user.id:
                    context.bot.send_message(chat_id = int(HA_id),
                            text = "Someone is handling " + handled_case["name_loc"])
            context.bot.send_message(chat_id = handled_case["chat_id"],
                    text = HABot.has[str(update.effective_user.id)] + " is on their way")
    else:
        update.message.reply_text("No problem. Let me know if you change your mind.",
                #reply_markup = r_IL_KB,
                reply_markup = response_keyboard)


def error(update: Update, context: CallbackContext):
    try:
        raise context.error
    except Unauthorized:
        pass
        # remove update.message.chat_id from conversation list
    except BadRequest:
        pass
        # handle malformed requests
    except TimedOut:
        pass
        # handle slow connection problems
    except NetworkError:
        pass
        # handle other connection problems
    except ChatMigrated as e:
        pass
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        pass
        # handle all other Telegram errors any time soon

def int_handler(signum, frame):
    data = {
        'ids': HABot.ha_ids,
        'chat_ids': HABot.ha_chat_ids,
        'names': HABot.ha_names,
        'has': HABot.has,
        'cases': HABot.cases
    }
    with open('HA_save.pkl', 'wb') as f:
        pickle.dump(data, f);
    if (signum in [SIGINT,SIGTERM,SIGABRT]):
        import os
        os._exit(1)

def main():
    try:
        with open('HA_save.pkl', 'rb') as f:
            data = pickle.load(f)
            HABot.ha_ids = data['ids']
            HABot.ha_chat_ids = data['chat_ids']
            HABot.ha_names = data['names']
            HABot.has = data['has']
            HABot.cases = data['cases']
            logging.info(str(HABot.ha_ids))
            logging.info(str(HABot.ha_chat_ids))
            logging.info(str(HABot.ha_names))
            logging.info(str(HABot.has))
            logging.info(str(HABot.cases))
    except FileNotFoundError:
        pass
    updater = Updater(TOKEN, user_sig_handler=int_handler, use_context=True)
    dp = updater.dispatcher

    start_handler = CommandHandler('start', start, filters = Filters.private)
    healthad_handler = CommandHandler('healthad', healthad, pass_user_data=True, filters = Filters.private)
    public_handler = CommandHandler('healthad', healthad_public, filters = Filters.group)
    ha_resp_handler = MessageHandler(Filters.regex('^(I can respond|I cannot respond)$'),
            response_handler)
    ha_resp_il_handler = CallbackQueryHandler(response_cb_handler)
    #ha_resp_handler = RegexHandler('^(I can respond|I cannot respond)$',
    #                            response_handler,
    #                            pass_user_data=True)
    conv_handler = ConversationHandler(
        entry_points = [start_handler, healthad_handler,
            MessageHandler(Filters.private & Filters.regex('^(I need a Health Ad|I am a Health Ad)$'),
                                    need_am_handler,
                                    pass_user_data=True)],

        states={
            CHOOSING: [MessageHandler(Filters.regex('^(I need a Health Ad|I am a Health Ad)$'),
                                    need_am_handler,
                                    pass_user_data=True)],
            SUMMON: [MessageHandler(Filters.text,
                                summon,
                                pass_user_data=True)],
            INFO: [MessageHandler(Filters.text &
                        ~Filters.regex('^(I can respond|I cannot respond)$'),
                                info_handler,
                                pass_user_data=True)],
            HEALTHAD: [ha_resp_handler, start_handler, healthad_handler]
            },

        fallbacks=[
            MessageHandler(Filters.regex('^I need a Health Ad$'),
                        need_am_handler,
                        pass_user_data=True),
            ha_resp_handler,
            ha_resp_il_handler]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(public_handler)

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        # save cases, health ads to file
        with open('HA_save.pkl', 'wb') as f:
            data = {
                'ids': HABot.ha_ids,
                'chat_ids': HABot.ha_chat_ids,
                'names': HABot.ha_names,
                'has': HABot.has,
                'cases': HABot.cases
            }
            pickle.dump(data, f);
