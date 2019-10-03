
#!/usr/bin/env
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.

"""
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler, Filters, ConversationHandler, \
    CallbackQueryHandler
from telegram.ext.dispatcher import run_async

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import requests
import telegram
import telegramcalendar
import re
import logging

from PillDora.Client import TOKEN_PROVE

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('AideBot')

TOKEN_AIDEBOT = '902984072:AAFd0KLLAinZIrGhQvVePQwBt3WJ1QQQDGs'
TOKEN_PROVE = '877926240:AAEuBzlNaqYM_kXbOMxs9lzhFsR7UpoqKWQ'

LOGIN, NEW_USER, CHOOSING, INTR_MEDICINE, CHECK_MED, CHECK_REM,  CALENDAR_TASKS, GET_CN, JOURNEY, JOURNEY_2= range(10)

aide_bot={}

reply_keyboard = [['Introduce Medicine', 'Calendar'],['History', 'Delete reminder'],['Journey', 'Exit']]
yes_no_reply_keyboard = [['YES', 'NO']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
yes_no_markup = ReplyKeyboardMarkup(yes_no_reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

#manage command /start of Telegram Input --> Starts program AideBot for determined user
def start(update, context):
    logger.info('User has connected to AideBot: /start')
    user_id = update.message.from_user.id
    aide_bot[user_id]={'states': [LOGIN, LOGIN], 'parameters':[]}
    name = get_name(update.message.from_user)
    context.bot.send_message(chat_id=user_id, text=("Welcome " + name + " ! My name is AideBot"))
    logger.info('Name of user is: ' + name + " and its ID is " + str(user_id))
    if (user_verification(update, context)):
        update.message.reply_text("Enter your password in order to get Assistance:")
        return set_state(user_id, LOGIN)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text=("Welcome to the HealthCare Assistant AideBot."
                                                                       "Enter new password for creating your account:"))
    return set_state(user_id, NEW_USER)

# Resolve message data to a readable name
def get_name(user):
    try:
        name = user.first_name
    except (NameError, AttributeError):
        try:
            name = user.username
        except (NameError, AttributeError):
            logger.info("No username or first name.. wtf")
            return ""
    return name


# Verificates password for UserID in DataBase
def pwd_verification(password):
    return True


# Verificates is UserID has account or it is first visit in AideBot
def user_verification(update, context):
    user_id = update.message.from_user.id
    #return (send_hamza("{state=user;user_id="+user_id+"}")
    return True

def set_state(user_id , state):
    aide_bot[user_id]['states'][1]=aide_bot[user_id]['states'][0]
    aide_bot[user_id]['states'][0]=state
    return state

# function used to Introduce Password
@run_async
def intr_pwd(update, context):
    password = update.message.text
    logger.info('Password for user ' +get_name(update.message.from_user)+ ' is ' + password)
    if (pwd_verification(password) == False):
        update.message.reply_text("Wrong Password. Enter correct password again:")
        return LOGIN
    update.message.reply_text('Welcome ' + get_name(update.message.from_user) + '. How can I help you?',
                              reply_markup=markup)
    return set_state(update.message.from_user.id, CHOOSING)


# function used to create user account --> associate UserID with Pwd
@run_async
def new_user(update, context):
    password = update.message.text
    # check if password difficulty.
    logger.info('New password is ' + password)
    i = 0

    if re.search("[a-z]", password):
        i = i + 1
    if re.search("[0-9]", password):
        i = i + 1
    if re.search("[A-Z]", password):
        i = i + 1
    if re.search("[$#@]", password):
        i = i + 1
    if re.search("\s", password):
        i = 0
    if (len(password) < 6 or len(password) > 12):
        i = 0

    if (i > 2):
        update.message.reply_text("Valid Password")
        update.message.reply_text('Welcome ' + get_name(update.message.from_user) + '. How can I help you?',
                                  reply_markup=markup)
        # Introdue new UserID-Password to DataBase
        x = False
        return set_state(update.message.from_user.id, CHOOSING)

    update.message.reply_text(
        "Not a Valid Password. Enter Password with 6 to 12 characters and minimum 3 of these types of characters: uppercase, lowercase, number and $, # or @")
    return set_state(update.message.from_user.id, NEW_USER)


def choose_function(update, context):
    logger.info('User ' +get_name(update.message.from_user)+ ' in the menu')
    update.message.reply_text("Is there any other way I can help you?", reply_markup=markup)
    return set_state(update.message.from_user.id, CHOOSING)



@run_async
def intr_medicine(update, context):
    logger.info('User ' +get_name(update.message.from_user)+ ' introducing new medicine')
    update.message.reply_text(
        'Please Introduce New Medicine using next format:\nCodeCN-Quantity-Frequency-EndDate-Expiration Date')
    return set_state(update.message.from_user.id, INTR_MEDICINE)


def send_new_medicine(update, context):
    medicine = update.message.text.split('-')
    if (len(medicine)!=5):
        logger.info('Error: user ' + get_name(update.message.from_user) + ' did not introduce all fields of new medicine')
        update.message.reply_text("Warning: complete all the fields as mentioned before.")
        return intr_medicine(update, context)
    else:
        logger.info(
            'New medicine for user  ' +get_name(update.message.from_user)+ ' .\n\tCN : ' + medicine[0] + '\n\tQuantity : ' + medicine[1] + '\n\tFrequency : ' +
            medicine[2] + '\n\tEndDate : ' + medicine[3] + '\n\tExpiration Date : ' + medicine[4])
        update.message.reply_text(
            'Medicine correctly introduced!\n\tCN : ' + medicine[0] + '\n\tQuantity : ' + medicine[1] + '\n\tFrequency : ' +
            medicine[2] + '\n\tEndDate : ' + medicine[3] + '\n\tExpiration Date : ' + medicine[4])
        update.message.reply_text('Is the medicine correctly introduced? ', reply_markup=yes_no_markup)
        return set_state(update.message.from_user.id, CHECK_MED)

@run_async
def see_calendar(update, context):
    logger.info('User ' +get_name(update.message.from_user)+ '  seeing calendar')
    update.message.reply_text("Please select a date: ",
                              reply_markup=telegramcalendar.create_calendar())
@run_async
def inline_handler(update, context):
    selected, date = telegramcalendar.process_calendar_selection(context.bot, update)
    user_id=update.callback_query.from_user.id
    if selected:
        if (aide_bot[user_id]['states'][0] == CHOOSING):
            context.bot.send_message(chat_id=user_id,
                         text="You selected %s" % (date.strftime("%d/%m/%Y")),
                         reply_markup=ReplyKeyboardRemove())

    if(aide_bot[user_id]['states'][0]==CHOOSING):
        get_calendar_tasks(update, context, date.strftime("%d/%m/%Y"))
        return set_state(user_id, CHOOSING)
    elif(aide_bot[user_id]['states'][0]==JOURNEY):
        set_journey(update, context, date.strftime("%d/%m/%Y"))
        set_state(user_id, JOURNEY_2)
    else:
        set_journey(update, context, date.strftime("%d/%m/%Y"))
        set_state(user_id, CHOOSING)


@run_async
def get_calendar_tasks(update, context, date):
    logger.info('Tasks for the user on the date '+ date)
    #connects to DataBase with Date and UserId asking for all the tasks of this date
    context.bot.send_message(chat_id=update.callback_query.from_user.id, text="Is there any other way I can help you?",
                             reply_markup=markup)

@run_async
def see_history(update, context):
    logger.info('User ' +get_name(update.message.from_user)+ '  seeing history')
    #connects to DataBase with UserId asking for all the meds currently taking
    user_id = update.message.from_user.id
    return choose_function(update, context)

@run_async
def delete_reminder(update, context):
    logger.info('User ' +get_name(update.message.from_user)+ ' deleting reminder')
    update.message.reply_text('Please Introduce CN of the Medicine you want to delete the reminder:')
    return set_state(update.message.from_user.id, GET_CN)

def get_medicine_CN(update, context):
    medicine_CN = update.message.text
    #connects to DataBase with UserId and get the current reminder for this medicine_CN.
    update.message.reply_text('Reminder asked to be removed:\n\tMedicine: \n\tTaken from:\n\tEnd date:\n\tFrequency: ')
    update.message.reply_text('Is this the reminder you want to remove? ', reply_markup=yes_no_markup)
    return set_state(update.message.from_user.id, CHECK_REM)


@run_async
def create_journey(update, context):
    logger.info('User ' + get_name(update.message.from_user) + ' creating journey')
    set_state(update.message.from_user.id, JOURNEY)
    update.message.reply_text("Wow fantastic! So you are going on a trip...\nWhen are you leaving?",
                          reply_markup=telegramcalendar.create_calendar())


def set_journey(update, context, date, ):
    user_id=update.callback_query.from_user.id
    if (aide_bot[user_id]['states'][0] == JOURNEY):
        logger.info("Department date "+ date)
        context.bot.send_message(chat_id=user_id,
                                 text="Alright. I see you are leaving on "+date+". When will you come back?",
                              reply_markup=telegramcalendar.create_calendar())

    if (aide_bot[user_id]['states'][0] == JOURNEY_2):
        logger.info("Arrival date "+ date)
        context.bot.send_message(chat_id=user_id,
                                 text="The arrival Date is on "+ date+"\nIs this information correct?",
                                  reply_markup=yes_no_markup)
        return set_state(user_id, JOURNEY_2)


def exit(update, context):
    update.message.reply_text("See you next time")
    logger.info('User ' +get_name(update.message.from_user)+ ' finish with AideBot')
    return ConversationHandler.END




def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    updater = Updater(token=TOKEN_PROVE, use_context=True, workers=50)
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        allow_reentry=True,
        entry_points=[CommandHandler('start', start)],

        states={
            LOGIN: [MessageHandler(Filters.text, intr_pwd)],
            NEW_USER: [MessageHandler(Filters.text, new_user)],
            CHOOSING: [MessageHandler(Filters.regex('^(Introduce Medicine)$'),
                                      intr_medicine),
                       MessageHandler(Filters.regex('^Calendar$'),
                                      see_calendar),
                       MessageHandler(Filters.regex('^History'),
                                      see_history),
                       MessageHandler(Filters.regex('^Delete reminder'),
                                      delete_reminder),
                       MessageHandler(Filters.regex('^Journey'),
                                      create_journey),
                       ],
            INTR_MEDICINE: [MessageHandler(Filters.text, send_new_medicine)],
            CHECK_MED: [MessageHandler(Filters.regex('^YES$'), choose_function),
                    MessageHandler(Filters.regex('^NO$'), intr_medicine)
                    ],
            CHECK_REM: [MessageHandler(Filters.regex('^YES$'), choose_function),
                    MessageHandler(Filters.regex('^NO$'), delete_reminder)
                    ],
            GET_CN: [MessageHandler(Filters.text, get_medicine_CN)],
            JOURNEY_2: [MessageHandler(Filters.regex('^YES$'), choose_function),
                    MessageHandler(Filters.regex('^NO$'), create_journey)
                    ]
        },
        fallbacks=[MessageHandler(Filters.regex('^Exit$'), exit)]

    )

    dp.add_handler(conv_handler)
    dp.add_handler(CallbackQueryHandler(inline_handler))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
