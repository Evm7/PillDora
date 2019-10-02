from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler, Filters, ConversationHandler, \
    CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import requests
import telegram
import telegramcalendar
import re
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('AideBot')

TOKEN_AIDEBOT = '902984072:AAFd0KLLAinZIrGhQvVePQwBt3WJ1QQQDGs'
TOKEN_PROVE = '877926240:AAEuBzlNaqYM_kXbOMxs9lzhFsR7UpoqKWQ'
LOGIN, NEW_USER, CHOOSING, INTR_MEDICINE, CHECK_MED, CHECK_REM , CALENDAR_CHOOSE, CALENDAR_TASKS, GET_CN = range(9)

reply_keyboard = [['Introduce Medicine', 'Calendar'],
                  ['History', 'Delete reminder'],
                  ['Journey', 'Done']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

yes_no_reply_keyboard = [['YES', 'NO']]
yes_no_markup = ReplyKeyboardMarkup(yes_no_reply_keyboard, one_time_keyboard=True)


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
    return True


# function used to Introduce Password
def intr_pwd(update, context):
    password = update.message.text
    logger.info('Password is ' + password)
    if (pwd_verification(password) == False):
        update.message.reply_text("Wrong Password. Enter correct password again:")
        return LOGIN
    update.message.reply_text('Welcome ' + get_name(update.message.from_user) + '. How can I help you?',
                              reply_markup=markup)
    return CHOOSING


# function used to create user account --> associate UserID with Pwd
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
        return CHOOSING

    update.message.reply_text(
        "Not a Valid Password. Enter Password with 6 to 12 characters and minimum 3 of these types of characters: uppercase, lowercase, number and $, # or @")
    return NEW_USER


def choose_function(update, context):
    logger.info('User in the menu')
    update.message.reply_text("Is there any other way I can help you?", reply_markup=markup)

def start(update, context):
    logger.info('User has connected to AideBot: /start')
    user_id = update.message.from_user.id
    name = get_name(update.message.from_user)
    context.bot.send_message(chat_id=update.message.chat_id, text=("Welcome " + name + " ! My name is AideBot"))
    logger.info('Name of user is: ' + name + " and its ID is " + str(user_id))
    if (user_verification(update, context)):
        update.message.reply_text("Enter your password in order to get Assistance:")
        return LOGIN
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text=("Welcome to the HealthCare Assistant AideBot."
                                                                       "Enter new password for creating your account:"))
    return NEW_USER


def intr_medicine(update, context):
    logger.info('User introducing new medicine')
    update.message.reply_text(
        'Please Introduce New Medicine using next format:\nCodeCN-Quantity-Frequency-EndDate-Expiration Date')
    return INTR_MEDICINE


def send_new_medicine(update, context):
    medicine = update.message.text.split('-')
    logger.info(
        'User introducing new medicine.\n\tCN : ' + medicine[0] + '\n\tQuantity : ' + medicine[1] + '\n\tFrequency : ' +
        medicine[2] + '\n\tEndDate : ' + medicine[3] + '\n\tExpiration Date : ' + medicine[4])
    update.message.reply_text(
        'Medicine correctly introduced!\n\tCN : ' + medicine[0] + '\n\tQuantity : ' + medicine[1] + '\n\tFrequency : ' +
        medicine[2] + '\n\tEndDate : ' + medicine[3] + '\n\tExpiration Date : ' + medicine[4])
    update.message.reply_text('Is the medicine correctly introduced? ', reply_markup=yes_no_markup)
    return CHECK_MED


def see_calendar(update, context):
    logger.info('User seeing calendar')
    update.message.reply_text("Please select a date: ",
                              reply_markup=telegramcalendar.create_calendar())

def inline_handler(update, context):
    selected, date = telegramcalendar.process_calendar_selection(context.bot, update)
    if selected:
        context.bot.send_message(chat_id=update.callback_query.from_user.id,
                         text="You selected %s" % (date.strftime("%d/%m/%Y")),
                         reply_markup=ReplyKeyboardRemove())
        get_calendar_tasks(update, context, date.strftime("%d/%m/%Y"))
    return CHOOSING


def get_calendar_tasks(update, context, date):
    logger.info('Tasks for the user on the date '+ date)
    #connects to DataBase with Date and UserId asking for all the tasks of this date
    context.bot.send_message(chat_id=update.callback_query.from_user.id, text="Is there any other way I can help you?",
                             reply_markup=markup)


def see_history(update, context):
    logger.info('User seeing history')
    #connects to DataBase with UserId asking for all the meds currently taking
    user_id = update.message.from_user.id
    return choose_function(update, context)


def delete_reminder(update, context):
    logger.info('User deleting reminder')
    update.message.reply_text('Please Introduce CN of the Medicine you want to delete the reminder:')
    return GET_CN

def get_medicine_CN(update, context):
    medicine_CN = update.message.text
    #connects to DataBase with UserId and get the current reminder for this medicine_CN.
    update.message.reply_text('Reminder asked to be removed:\n\tMedicine: \n\tTaken from:\n\tEnd date:\n\tFrequency: ')
    update.message.reply_text('Is this the reminder you want to remove? ', reply_markup=yes_no_markup)
    return CHECK_REM

def done(update, context):
    update.message.reply_text("See you next time")
    logger.info('User finish with AideBot')
    return ConversationHandler.END


def create_journey(update, context):

    logger.info('User creating journey')
    return choose_function(update, context)


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    updater = Updater(token=TOKEN_PROVE, use_context=True)
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
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
            CALENDAR_CHOOSE: [MessageHandler(Filters.text, inline_handler)],
            GET_CN: [MessageHandler(Filters.text, get_medicine_CN)]

        },
        fallbacks=[MessageHandler(Filters.regex('^Done$'), done)]

    )

    dp.add_handler(conv_handler)
    dp.add_handler(CallbackQueryHandler(inline_handler))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
