# !/usr/bin/env
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
"""
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import json
import logging
import re
from threading import Event

import telegram
from telegram import KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from telegram.replykeyboardremove import ReplyKeyboardRemove
from botui import strings_bot as st
import botui.telegramcalendar as telegramcalendar
import server.cima as cima
from imagerecognition.ocr.ocr import TextRecognition
from server.serverworker import ServerWorker
from nlp.nlp import NLP

# LOG INFORMATION
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('AideBot')

# TOKENS FOR THE TELEGRAM BOT
TOKEN_PROVE = '877926240:AAEuBzlNaqYM_kXbOMxs9lzhFsR7UpoqKWQ'
TOKEN_AIDEBOT = '902984072:AAFd0KLLAinZIrGhQvVePQwBt3WJ1QQQDGs'
TOKEN_PILLDORA = '938652990:AAETGF-Xh2_njSdCLn2KibcprZXH1hhqsiI'

# STATES OF THE APP
LOGIN, NEW_USER, CHOOSING, INTR_PRESCRIPTION, INTR_MEDICINE, TAKE_PILL, LOCATION, SHOW_INFORMATION, CHECK_PRE, CHECK_MED, CHECK_PILL, CHECK_PILL_PHOTO, GET_CN, CHECK_REM, JOURNEY, END, REMINDERS = range(
    17)

# MAX_DATE FORBID BY MYSQL:
MAX_DATE = "2036-12-31"

# cross icon:
crossIcon = u"\u274C"
# FUNCTIONS FOR COMMUNICATING WITH DATA BASE
QUERIES = ['CHECK USER', 'CHECK PASSWORD', 'NEW PASSWORD', 'INTRODUCE PRESCRIPTION', 'INTRODUCE MEDICINE', 'TAKE PILL',
           'CHECK PILL', 'VERIFICATE PILL'
                         'TASKS CALENDAR', 'CURRENT TREATMENT', 'JOURNEY', 'HISTORY', 'INVENTORY']

PRESCRIPTION_TAGS = ['NAME', 'QUANTITY', 'FREQUENCY', 'END_DATE']

MEDICINE_TAGS = ['NAME', 'QUANTITY', 'EXP_DATE']
NLP_TAGS = ['NAME', 'QUANTITY', 'EXP_DATE', 'FREQUENCY', 'END_DATE']
NLP_OPTION = ['INTRODUCE MEDICINE', 'INTRODUCE PRESCRIPTION']

PILL_TAGS = ['NAME', 'QUANTITY']
markup = {}
markup['eng'] = ReplyKeyboardMarkup(st.reply_keyboard['eng'], one_time_keyboard=True, resize_keyboard=True)
markup['esp'] = ReplyKeyboardMarkup(st.reply_keyboard['esp'], one_time_keyboard=True, resize_keyboard=True)

loc_button = {}
loc_button['eng'] = KeyboardButton(text="Send Location", request_location=True)
loc_button['esp'] = KeyboardButton(text="Enviar ubicación", request_location=True)
location_keyboard = {}
location_keyboard['eng'] = [[loc_button['eng'], "Don't Send Location"]]
location_keyboard['esp'] = [[loc_button['esp'], "No enviar ubicación"]]

# markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
yes_no_markup = {}
gender_markup = {}
taken_pill_markup = {}
loc_markup = {}
day_markup = {}
yes_no_markup['eng'] = ReplyKeyboardMarkup(st.yes_no_reply_keyboard['eng'], one_time_keyboard=True,
                                           resize_keyboard=True)
yes_no_markup['esp'] = ReplyKeyboardMarkup(st.yes_no_reply_keyboard['esp'], one_time_keyboard=True,
                                           resize_keyboard=True)
gender_markup['eng'] = ReplyKeyboardMarkup(st.gender_reply_keyboard['eng'], one_time_keyboard=True,
                                           resize_keyboard=True)
gender_markup['esp'] = ReplyKeyboardMarkup(st.gender_reply_keyboard['esp'], one_time_keyboard=True,
                                           resize_keyboard=True)
taken_pill_markup['eng'] = ReplyKeyboardMarkup(st.taken_pill_keyboard['eng'], one_time_keyboard=True,
                                               resize_keyboard=True)
taken_pill_markup['esp'] = ReplyKeyboardMarkup(st.taken_pill_keyboard['esp'], one_time_keyboard=True,
                                               resize_keyboard=True)
loc_markup['eng'] = ReplyKeyboardMarkup(location_keyboard['eng'], one_time_keyboard=True, resize_keyboard=True)
loc_markup['esp'] = ReplyKeyboardMarkup(location_keyboard['esp'], one_time_keyboard=True, resize_keyboard=True)
start_keyboard = [[InlineKeyboardButton(text="START", callback_data="/start")]]
start_markup = InlineKeyboardMarkup(start_keyboard)
day_markup['eng'] = ReplyKeyboardMarkup(st.day_keyboard['eng'], one_time_keyboard=True, resize_keyboard=True)
day_markup['esp'] = ReplyKeyboardMarkup(st.day_keyboard['esp'], one_time_keyboard=True, resize_keyboard=True)


class PillDora:
    """
    Telegram bot that serves as an aide to the clients of the product. It has a set of features that help customers
    to remember to take their pills (how many and when) and manages the customer's receipts and meds provisions.
    """
    # MANAGE WHOLE BOT INFORMATION
    aide_bot = {}
    # BOT WE COMMUNICATE TO
    bot = telegram.Bot(TOKEN_PROVE)
    # MANAGE THREADS STATES SYNCHRONICITY
    event = Event()

    # GETTERS AND SETTERS TO EASY FUNCTIONS
    def set_state(self, user_id, state):
        self.aide_bot[user_id]['states'][1] = self.aide_bot[user_id]['states'][0]
        self.aide_bot[user_id]['states'][0] = state
        return state

    # Returns the state of the bot for a specific user_id
    def get_states(self, user_id):
        return self.aide_bot[user_id]['states']

    def set_handling(self, user_id, text):
        self.aide_bot[user_id]['handling'] = text

    # Returns the state of being handling the bot for a specific user_id
    def get_handling(self, user_id):
        return self.aide_bot[user_id]['handling']

    def in_end(self, user_id):
        if (list(self.aide_bot.keys()).count(user_id) == 0):
            return False
        return self.aide_bot[user_id]['states'][0] == END

    def set_reminder(self, user_id, cn, time):
        self.aide_bot[user_id]['reminder']['cn'] = cn
        self.aide_bot[user_id]['reminder']['time'] = time

    def get_reminder(self, user_id):
        return self.aide_bot[user_id]['reminder']

    def set_new_user(self, user_id, key, value):
        self.aide_bot[user_id]['new_user'][key] = value

    def get_new_user(self, user_id):
        return self.aide_bot[user_id]['new_user']

    # Returns the last prescription associated for a specific user_id
    def get_prescription(self, user_id):
        return self.aide_bot[user_id]['prescription']

    # Insertion of a prescription for a specific user_id
    def set_prescription(self, user_id, num, text):
        self.aide_bot[user_id]['prescription'][PRESCRIPTION_TAGS[num]] = text

    # Returns the last medicine associated for a specific user_id
    def get_medicine(self, user_id):
        return self.aide_bot[user_id]['medicine']

    # Insertion of a medicine for a specific user_id
    def set_medicine(self, user_id, num, text):
        self.aide_bot[user_id]['medicine'][MEDICINE_TAGS[num]] = text

    # Returns the last medicine associated for a specific user_id
    def get_pill(self, user_id):
        return self.aide_bot[user_id]['pill']

    # Insertion of a medicine for a specific user_id
    def set_pill(self, user_id, num, text):
        self.aide_bot[user_id]['pill'][PILL_TAGS[num]] = text
        return text

    # Returns the dates on a journey for a specific user_id
    def get_dates(self, user_id):
        return self.aide_bot[user_id]['journey']

    # Insertion of the date of a journey depending on the text, it is the departure or return for a specific user_id
    def set_dates(self, user_id, text, date):
        if text == "departure":
            self.aide_bot[user_id]['journey'][0] = date
        else:
            self.aide_bot[user_id]['journey'][1] = date

    # Insertion of the number of medicines associated to a medicine for a specific user_id
    def set_counter(self, user_id, num):
        self.aide_bot[user_id]['intr_prescription_counter'] = num

    # Returns the number of medicines associated to a medicine for a specific user_id
    def get_counter(self, user_id):
        return self.aide_bot[user_id]['intr_prescription_counter']

    # Set the language associated to an specific user_id
    def set_language(self, user_id, lang):
        self.aide_bot[user_id]['language'] = lang

    # Returns the language associated to an specific user_id
    def get_language(self, user_id):
        return self.aide_bot[user_id]['language']

    # Insertion of the query that the Client sends to the ServerWorker for a specific user_id
    def set_query(self, user_id, keys, values):
        # We use a dictionary for the parameters of the query on the JSON string
        parameters = {key: value for key, value in zip(keys, values)}
        self.aide_bot[user_id]['query'] = parameters

    # Returns the query that that the Client sends to the ServerWorker for a specific user_id
    def get_query(self, user_id):
        return self.aide_bot[user_id]['query']

    # Insertion of the function that the bot is currently on for a specific user_id
    def set_function(self, user_id, text):
        self.aide_bot[user_id]['function'] = text

    # Returns the function that the bot is doing for a specific user_id
    def get_function(self, user_id):
        return self.aide_bot[user_id]['function']

    def send_query(self, user_id, query):
        """Sends the query to the ServerWorker and returns the JSON query response.

        :param user_id: User unique identifier (login)
        :param query: Query to be send to the ServerWorker
        :return: the response to the query from sever
        """
        return self.aide_bot[user_id]['serverworker'].handler_query(query)

    def create_query(self, user_id):
        """Creates a JSON from the parameters that we have introduced using the Getters and Setters.

        :param user_id: User unique identifier (login)
        :return: query string generated
        """
        # We create a pseudo-class to have a template for the JSON
        query = {
            'user_id': user_id,
            'function': self.get_function(user_id),
            'parameters': self.get_query(user_id)
        }
        query = json.dumps(query)
        logger.info(query)
        return query

    def start(self, update, context):
        """Manages /start command initializing a new self.aide_bot dictionary for the new user. It also manages a login.

        :param update: Updater for bot token
        :param context: Handler context
        :return: the new state to be on
        """
        user_id = update.message.from_user.id
        name = self.get_name(update.message.from_user)
        self.aide_bot[user_id] = {'states': [LOGIN, LOGIN], 'intr_prescription_counter': 0,
                                  'prescription': {tag: '' for tag in PRESCRIPTION_TAGS},
                                  'medicine': {tag: '' for tag in MEDICINE_TAGS},
                                  'pill': {tag: '' for tag in PILL_TAGS},
                                  'journey': ['None', 'None'],
                                  'function': 'none',
                                  'query': {},
                                  'reminder': {'cn': "None", 'time': 'None'},
                                  'new_user': {'new_password': 'None', 'new_age': "None", 'new_gender': 'None',
                                               'new_postalcode': 'None'},
                                  'serverworker': ServerWorker(user_id),
                                  'language': self.define_language(update.message.from_user.language_code),
                                  'handling': 'False'}
        logger.info('User ' + name + ' has connected to AideBot: ID is ' + str(user_id))
        message = update.message.text
        if str(message).startswith("/start") or str(message).startswith("/START"):
            self.bot.send_message(chat_id=user_id, text=(eval(st.STR_START_WELCOME[self.get_language(user_id)])))
        elif str(message).startswith("I have had") or str(message).startswith("He tenido"):
            self.bot.send_message(chat_id=user_id, text=st.STR_WELCOME_NOT_GOOD[self.get_language(user_id)])
        else:
            self.bot.send_message(chat_id=user_id, text=st.STR_WELCOME_YES_GOOD[self.get_language(user_id)])

        if self.user_verification(user_id) == "True":
            update.message.reply_text(st.STR_START_ENTERPASSWORD[self.get_language(user_id)])
            return self.set_state(user_id, LOGIN)
        else:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text=st.STR_START_CREATEUSER[self.get_language(user_id)])
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text=st.STR_START_ENTERPASSWORD[self.get_language(user_id)])
        return self.set_state(user_id, NEW_USER)

    def define_language(self, language_code):
        if language_code == 'es' or language_code == 'ca':
            return 'esp'
        else:
            return 'eng'

    @staticmethod
    def get_name(user):
        """Resolve message data to a readable name.

        :param user: User identifier
        :return: first name of the user
        """
        try:
            name = user.first_name
        except (NameError, AttributeError):
            logger.info("No username or first name.. wtf")
            return ""
        return name

    def user_verification(self, user_id):
        """Verification of the UserID, if he has account or if it is first visit in AideBot.

        :param user_id: User unique identifier
        :return: a boolean indicating whether the user is registered or not
        """
        self.set_function(user_id, 'CHECK USER')
        self.set_query(user_id, ["user_id"], [str(user_id)])
        query = self.create_query(user_id)
        response = self.send_query(user_id, query)
        return json.loads(response)["parameters"]["boolean"]

    def pwd_verification(self, password, user_id):
        """ Verification of the password for a UserID in DataBase.

        :param password: Password introduced by the user
        :param user_id: User unique identifier
        :return: whether the password is the correct one or not
        """
        self.set_function(user_id, 'CHECK PASSWORD')
        self.set_query(user_id, ['password'], [password])
        query = self.create_query(user_id)
        response = self.send_query(user_id, query)
        return json.loads(response)["parameters"]["boolean"]

    @run_async
    def intr_pwd(self, update, context):
        """Method used to ask and introduce a password to check the identity of the user.

        :param update: Updater for bot token
        :param context: Handler's context
        :return: the new state to be on (LOGIN if fails, CHOOSING if succeeds)
        """
        user_id = update.message.from_user.id
        password = update.message.text
        message_id = update.message.message_id
        self.bot.delete_message(chat_id=user_id, message_id=message_id - 1)
        self.bot.delete_message(chat_id=user_id, message_id=message_id)
        if self.pwd_verification(password, user_id) == "False":
            update.message.reply_text(st.STR_INTR_PWD_WRONGPASS[self.get_language(user_id)])
            return self.set_state(user_id, LOGIN)
        update.message.reply_text(st.STR_INTR_PWD_HELPYOU[self.get_language(user_id)],
                                  reply_markup=markup[self.get_language(user_id)])
        return self.set_state(user_id, CHOOSING)

    @run_async
    def new_user(self, update, context):
        """ Function used to create user account --> associates a UserID with a new password.pu

        :param update: Updater for bot token
        :param context: Handler's context
        :return: the new state to be on (NEW_USER if fails, CHOOSING if succeeds)
        """
        user_id = update.message.from_user.id
        if self.get_counter(user_id) == 0:
            password = update.message.text
            logger.info('User introduced new password:  ' + password)
            user_id = update.message.from_user.id
            self.bot.delete_message(chat_id=user_id, message_id=update.message.message_id - 1)
            self.bot.delete_message(chat_id=user_id, message_id=update.message.message_id)

            # Check for password difficulty:
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
            if len(password) < 6 or len(password) > 12:
                i = 0

            if i > 2:
                # update.message.reply_text("Valid Password")
                # Introduce new UserID-Password to DataBase
                self.set_new_user(user_id, 'new_password', password)
                # query = self.create_query(user_id)
                # self.send_query(user_id, query)
                # update.message.reply_text(st.STR_NEW_USER_VALIDPASS[self.get_language(user_id)], reply_markup = markup[self.get_language(user_id)])
                update.message.reply_text(st.STR_NEW_USER_VALIDPASS[self.get_language(user_id)])
                update.message.reply_text(st.STR_NEW_USER_AGE[self.get_language(user_id)])
                self.set_counter(user_id, self.get_counter(user_id) + 1)

                return self.set_state(update.message.from_user.id, NEW_USER)

            update.message.reply_text(
                st.STR_NEW_USER_NOTVALIDPASS[self.get_language(user_id)])
            return self.set_state(update.message.from_user.id, NEW_USER)

        elif self.get_counter(user_id) == 1:
            age = update.message.text
            # self.set_query(user_id, [""], [age])
            self.set_new_user(user_id, 'new_age', age)
            update.message.reply_text(st.STR_NEW_USER_GENDER[self.get_language(user_id)],
                                      reply_markup=gender_markup[self.get_language(user_id)])
            self.set_counter(user_id, self.get_counter(user_id) + 1)
            return self.set_state(update.message.from_user.id, NEW_USER)

        elif self.get_counter(user_id) == 2:
            gender = update.message.text
            self.set_new_user(user_id, 'new_gender', gender)
            update.message.reply_text(st.STR_NEW_USER_POSTAL_CODE[self.get_language(user_id)])
            # string del postal code
            self.set_counter(user_id, self.get_counter(user_id) + 1)
            return self.set_state(update.message.from_user.id, NEW_USER)

        elif self.get_counter(user_id) == 3:
            postal_code = update.message.text
            self.set_counter(user_id, 0)
            # add to database
            self.set_new_user(user_id, 'new_postalcode', postal_code)
            self.set_function(user_id, 'NEW PASSWORD')

            user = self.get_new_user(user_id)
            print(str(user))
            self.set_query(user_id, ["user_id", "new_password", "new_age", "new_gender", "new_postalcode"],
                           [str(user_id), user['new_password'], user['new_age'], user['new_gender'],
                            user['new_postalcode']])
            query = self.create_query(user_id)
            response = json.loads(self.send_query(user_id, query))

            update.message.reply_text(st.STR_NEW_USER_VALIDREGISTER[self.get_language(user_id)],
                                      reply_markup=markup[self.get_language(user_id)])
            return self.set_state(update.message.from_user.id, CHOOSING)

    def manage_response(self, update, context):
        """Sends a query and gets the response, deciding what to do depending on the response 'function' field.

        :param update: Updater for bot token
        :param context: Handler's context
        :return: state CHOOSING
        """
        user_id = update.message.from_user.id
        if (self.get_query(user_id) != "None") and (self.get_query(user_id) != {"None": "None"}):
            query = self.create_query(user_id)
            response = json.loads(self.send_query(user_id, query))
            if response['function'] == 'INTRODUCE PRESCRIPTION':
                if response['parameters']["Code"] == "0":
                    logger.info("Medicine correctly introduced")
                elif response['parameters']["Code"] == "1":
                    logger.info("Medicine already in the database with different frequencies. PROBLEM")
                    update.message.reply_text(
                        st.STR_MANAGE_RESPONSE_ALREADYPRESCRIPT1[self.get_language(user_id)])
                elif response['parameters']["Code"] == "2":
                    logger.info("Medicine already in the database with same frequencies. NO PROBLEM")
                    update.message.reply_text(st.STR_MANAGE_RESPONSE_ALREADYPRESCRIPT2[self.get_language(user_id)])
                if response['parameters']['inventory'] == "None":
                    update.message.reply_text(st.STR_MANAGE_RESPONSE_EMPTYINVENTORY[self.get_language(user_id)])
                    return self.show_location(user_id=user_id)
                elif response['parameters']['inventory'] == "Enough":
                    update.message.reply_text(st.STR_MANAGE_RESPONSE_FULLINVENTORY[self.get_language(user_id)])
                elif response['parameters']['inventory'] == "Need to buy":
                    update.message.reply_text(st.STR_MANAGE_RESPONSE_BUYINVENTORY[self.get_language(user_id)])
                    return self.show_location(user_id=user_id)

            elif response['function'] == 'INTRODUCE MEDICINE':
                if response['parameters']["Code"] == "0":
                    logger.info("Medicine correctly introduced")

            elif response['function'] == "DELETE REMINDER":
                if response['parameters']:
                    logger.info("Medicine correctly deleted")
                else:
                    logger.info("Medicine not deleted as did not exist in the database")
                    update.message.reply_text(st.STR_MANAGE_RESPONSE_DELETEREMINDER[self.get_language(user_id)])
                    self.delete_reminder()
                    return self.set_state(update.message.from_user.id, CHOOSING)

            elif response['function'] == "JOURNEY":
                logger.info("Medicines to take during journey correctly retrieved")
                update.message.reply_text(
                    eval(st.STR_MANAGE_RESPONSE_JOURNEY[self.get_language(user_id)]))

            elif response['function'] == "TAKE PILL":
                logger.info("Pills taken correctly introduced to history")
                if response['parameters']["Code"] == "1":
                    logger.info("Pill taken correctly introduced")
                    self.bot.send_message(chat_id=user_id,
                                          text=st.STR_MANAGE_RESPONSE_TAKEPILL1[self.get_language(user_id)])
                elif response['parameters']["Code"] == "0":
                    logger.info("Pill taken correctly introduced. However, no inventory for these pills.")
                    self.bot.send_message(chat_id=user_id,
                                          text=st.STR_MANAGE_RESPONSE_TAKEPILL0[self.get_language(user_id)])
                    return self.show_location(user_id)

        self.set_query(user_id, ["None"], ["None"])
        self.set_function(user_id, "None")
        logger.info('User ' + self.get_name(update.message.from_user) + ' in the menu')
        update.message.reply_text(st.STR_MANAGE_RESPONSE_END[self.get_language(user_id)],
                                  reply_markup=markup[self.get_language(user_id)])
        return self.set_state(update.message.from_user.id, CHOOSING)

    @run_async
    def intr_prescription(self, update, context):
        """ Method that gets a new medicine to the recipes and starts the form.

        :param update: Updater for bot token
        :param context: Handler's context
        :return: new state INTR_PRESCRIPTION
        """
        user_id = update.message.from_user.id
        logger.info('User introducing new prescription')
        update.message.reply_text(
            st.INTR_PRESCRIPTION_MSSGS[self.get_language(user_id)][self.get_counter(update.message.from_user.id)])
        return self.set_state(update.message.from_user.id, INTR_PRESCRIPTION)

    def send_new_prescription(self, update, context):
        """Asks the user information in order to complete the prescription form, and once completed sets the query
        ready to be sent.

        :param update: Updater for bot token
        :param context: Handler's context
        :return: state INTR_PRESCRIPTION while form not completed, state CHECK_PRE once completed
        """
        voice = False
        try:
            user_id = update.message.from_user.id
            if self.get_counter(user_id) == 0:  # If we are in the first field of the form
                if update.message.photo:  # If user sent a photo, we apply
                    medicine_cn, validation_num = self.handle_pic(update, context, user_id)
                else:
                    if self.valid_input(update.message.text):
                        medicine_cn, validation_num = self.split_code(update.message.text)
                    else:
                        update.message.reply_text(
                            st.STR_INTR_PWD_METACHARACTERS[self.get_language(user_id)])
                        return INTR_PRESCRIPTION

                if "error" in [medicine_cn, validation_num] or not self.verify_code(medicine_cn, validation_num):
                    update.message.reply_text(
                        st.STR_SEND_NEW_PRESCRIPTION_ERROR[self.get_language(user_id)])
                    return INTR_PRESCRIPTION
                else:
                    self.set_prescription(user_id, self.get_counter(user_id), medicine_cn)
            else:
                if update.message.voice:
                    voice = True
                    answer = self.handle_voice(update, context, user_id)
                    answer_key = answer.parameters[PRESCRIPTION_TAGS[self.get_counter(
                        user_id)]]  # De todos los parametros que recibimos solo quiere analizar el que pertenece a esa KEYWORD
                    if len(str(answer_key)) == 0:
                        update.message.reply_text("An error has occurred, please repeat the audio")
                        return INTR_PRESCRIPTION
                    elif self.get_counter(user_id) == 1:  # trata la cantidad
                        answer_key = str(answer_key)
                        answer_key = answer_key.split('.')[0]
                    elif self.get_counter(user_id) == 2:  # trata la frequencia
                        answer_key = answer.parameters['FREQUENCY']['amount']
                        answer_key = str(answer_key)
                        answer_key = answer_key.split('.')[0]
                    elif self.get_counter(user_id) == 3:  # trata la fecha
                        answer_key = self.split_date(answer_key)

                    update.message.reply_text(answer_key)  # se podra borrar luego
                    self.set_prescription(user_id, self.get_counter(user_id), str(answer_key))

                elif update.message.text and self.valid_input(update.message.text):
                    self.set_prescription(user_id, self.get_counter(user_id), update.message.text)
                else:
                    update.message.reply_text(
                        eval(st.STR_SEND_NEW_PRESCRIPTION_META_RESPOND[self.get_language(user_id)]))
                    return INTR_PRESCRIPTION
        except Exception as e:
            print(e)
            user_id = update.callback_query.from_user.id

        self.set_counter(user_id, self.get_counter(user_id) + 1)
        logger.info(self.get_prescription(user_id))
        if self.get_counter(user_id) != len(st.INTR_PRESCRIPTION_MSSGS[self.get_language(user_id)]):
            if self.get_counter(user_id) < 3:
                update.message.reply_text(
                    st.INTR_PRESCRIPTION_MSSGS[self.get_language(user_id)][self.get_counter(user_id)])
                return INTR_PRESCRIPTION
            else:
                update.message.reply_text(
                    st.INTR_PRESCRIPTION_MSSGS[self.get_language(user_id)][self.get_counter(user_id)])

                if voice == False:
                    context.bot.send_message(chat_id=user_id,
                                             text="Please select: ",
                                             reply_markup=telegramcalendar.create_calendar())
                elif self.get_counter(user_id) > 1:
                    return INTR_PRESCRIPTION
                return CHECK_PRE
        else:
            self.set_counter(user_id, 0)
            a = list(self.get_prescription(user_id).keys())
            a.append('NAME REAL')
            b = list(self.get_prescription(user_id).values())
            b.append(cima.get_med_name(self.get_prescription(user_id)['NAME']))
            context.bot.send_message(chat_id=user_id,
                                     text=st.STR_SEND_NEW_PRESCRIPTION_ISCORRECT[self.get_language(user_id)],
                                     reply_markup=yes_no_markup[self.get_language(user_id)])
            context.bot.send_message(chat_id=user_id,
                                     text=self.show_prescription(user_id), parse_mode=telegram.ParseMode.MARKDOWN)

            self.set_query(user_id, a, b)
            self.set_function(user_id, 'INTRODUCE PRESCRIPTION')
            return self.set_state(user_id, CHECK_PRE)

    def handle_pic(self, update, context, user_id):
        """
        :param update:
        :param context:
        :param user_id:
        :return:
        """
        file = context.bot.getFile(update.message.photo[-1].file_id)
        filename = f"/home/paesav/Imágenes/{user_id}.jpg"
        file.download(filename)
        medicine_cn, validation_number = self.medicine_search(filename)
        return medicine_cn, validation_number

    def handle_voice(self, update, context, user_id):
        newFile = context.bot.getFile(update.message.voice.file_id)
        filename_src = f"/home/paesav/PAET2019/PillDora/Voice/{user_id}.ogg"
        filename_out = f"/home/paesav/PAET2019/PillDora/Voice/{user_id}.wav"
        newFile.download(filename_src)
        text = NLP().init(filename_src, filename_out, self.get_language(user_id))
        return text

    @staticmethod
    def medicine_search(filename):
        number, validation_number = TextRecognition().init(filename,
                                                           "/home/paesav/PAET2019/PillDora/imagerecognition/ocr/frozen_east_text_detection.pb")
        return number, validation_number

    @staticmethod
    def split_code(cn):
        if '.' in cn:
            return cn.split('.')[0], cn.split('.')[-1]
        elif len(cn) == 7:
            return cn[:6], cn[6]
        else:
            return 'error', 'error'

    def valid_input(self, text):
        return not ("'" in text or '"' in text or '*' in text)

    @staticmethod
    def split_date(date):
        return (date.split("T")[0])

    @staticmethod
    def split_value(answer_key):
        answer_key = str(answer_key)
        answer_key = answer_key.split('.')[0]
        return str(answer_key)

    @staticmethod
    def verify_code(medicine, validation_number):
        sum1 = 3 * (int(medicine[1]) + int(medicine[3]) + int(medicine[5]))
        sum2 = int(medicine[0]) + int(medicine[2]) + int(medicine[4])
        sum3 = sum1 + sum2 + 27
        res = 10 - (sum3 % 10)
        return res == int(validation_number)

    def show_prescription(self, user_id):
        med_str = eval(st.STR_SHOW_PRESCRIPTION_MEDSTR[self.get_language(user_id)])

        date_str = self.get_prescription(user_id)['END_DATE']
        if date_str == MAX_DATE:
            med_str += st.STR_SHOW_PRESCRIPTION_CHRONIC[self.get_language(user_id)]
        else:
            med_str += eval(st.STR_SHOW_PRESCRIPTION_UNTIL[self.get_language(user_id)])
        return med_str

    @run_async
    def intr_medicine(self, update, context):
        """ Method that gets quantities of new medicine.

        :param update: Updater for bot token
        :param context: Handler's context
        :return: new state INTR_MEDICINE
        """
        user_id = update.message.from_user.id
        logger.info('User introducing new medicine')
        update.message.reply_text(
            st.INTR_MEDICINE_MSSGS[self.get_language(user_id)][self.get_counter(update.message.from_user.id)])
        return self.set_state(update.message.from_user.id, INTR_MEDICINE)

    def send_new_medicine(self, update, context):
        """Asks the user information in order to complete the medicine form, and once completed sets the query ready to
        be sent.

        :param update: Updater for bot token
        :param context: Handler's context
        :return: state INTR_MEDICINE while form not completed, state CHECK_MED once completed
        """
        voice = False

        try:
            user_id = update.message.from_user.id
            if self.get_counter(user_id) == 0:  # If we are in the first field of the form
                if update.message.photo:  # If user sent a photo, we apply
                    medicine_cn, validation_num = self.handle_pic(update, context, user_id)
                else:
                    medicine_cn, validation_num = self.split_code(update.message.text)

                if "error" in [medicine_cn, validation_num] or not self.verify_code(medicine_cn, validation_num):
                    update.message.reply_text(
                        st.STR_SNED_NEW_MEDICINE_ERROR[self.get_language(user_id)])
                    return INTR_MEDICINE
                else:
                    self.set_medicine(user_id, self.get_counter(user_id), medicine_cn)
            else:
                if update.message.voice:
                    voice = True
                    answer = self.handle_voice(update, context, user_id)
                    answer = answer.parameters[MEDICINE_TAGS[self.get_counter(
                        user_id)]]  # De todos los parametros que recibimos solo quiere analizar el que pertenece a esa KEYWORD
                    if len(str(answer)) == 0:
                        update.message.reply_text("An error has occurred, please repeat the audio")
                        return INTR_MEDICINE
                    elif self.get_counter(user_id) == 2:
                        answer = self.split_date(answer)
                    update.message.reply_text(answer)  # se podra borrar luego
                    self.set_medicine(user_id, self.get_counter(user_id), str(answer))

                else:
                    print("no detecto voz")
                    self.set_medicine(user_id, self.get_counter(user_id), update.message.text)
        except:
            user_id = update.callback_query.from_user.id

        self.set_counter(user_id, self.get_counter(user_id) + 1)
        logger.info(self.get_medicine(user_id))
        if self.get_counter(user_id) != len(st.INTR_MEDICINE_MSSGS[self.get_language(user_id)]):
            if self.get_counter(user_id) < 2:
                update.message.reply_text(st.INTR_MEDICINE_MSSGS[self.get_language(user_id)][self.get_counter(user_id)])
                return INTR_MEDICINE
            else:
                update.message.reply_text(st.INTR_MEDICINE_MSSGS[self.get_language(user_id)][self.get_counter(user_id)])

                if voice == False:
                    context.bot.send_message(chat_id=user_id,
                                             text="Please select: ",
                                             reply_markup=telegramcalendar.create_calendar())
                elif self.get_counter(user_id) > 1:
                    return INTR_MEDICINE
                return CHECK_MED
        else:
            self.set_counter(user_id, 0)
            context.bot.send_message(chat_id=user_id,
                                     text=st.STR_SEND_NEW_MEDICINE_ISCORRECT[self.get_language(user_id)],
                                     reply_markup=yes_no_markup[self.get_language(user_id)])
            context.bot.send_message(chat_id=user_id,
                                     text=self.show_medicine(user_id), parse_mode=telegram.ParseMode.MARKDOWN)
            self.set_query(user_id, list(self.get_medicine(user_id).keys()), list(self.get_medicine(user_id).values()))
            self.set_function(user_id, 'INTRODUCE MEDICINE')
            return self.set_state(user_id, CHECK_MED)

    def show_medicine(self, user_id):
        med_str = eval(st.STR_SHOW_MEDICINE_INITIALSTRING[self.get_language(user_id)])

        date_str = self.get_medicine(user_id)['EXP_DATE']
        if date_str == MAX_DATE:
            med_str += st.STR_SHOW_MEDICINE_NOCADUCA[self.get_language(user_id)]
        else:
            med_str += eval(st.STR_SHOW_MEDICINE_ELDIA[self.get_language(user_id)])
        return med_str

    @run_async
    def intr_nlp(self, update, context):
        """ Method that gets quantities of new medicine.

        :param update: Updater for bot token
        :param context: Handler's context
        :return: new state INTR_MEDICINE
        """
        user_id = update.message.from_user.id
        logger.info('User using NLP mode')
        update.message.reply_text(
            st.INTR_NLP_MSSGS[self.get_language(user_id)][self.get_counter(update.message.from_user.id)])
        return self.set_state(update.message.from_user.id, NLP)

    def nlp_mode(self, update, context):
        print(update.message.from_user.id)
        try:
            user_id = update.message.from_user.id
            if self.get_counter(user_id) == 0:  # If we are in the first field of the form
                if update.message.photo:  # If user sent a photo, we apply
                    medicine_cn, validation_num = self.handle_pic(update, context, user_id)
                else:
                    medicine_cn, validation_num = self.split_code(update.message.text)

                if "error" in [medicine_cn, validation_num] or not self.verify_code(medicine_cn, validation_num):
                    update.message.reply_text(
                        "An error has occurred, please repeat the photo or manually introduce the CN")
                    return NLP
                else:
                    self.set_medicine(user_id, 0, medicine_cn)
                    self.set_prescription(user_id, 0, medicine_cn)

            else:
                if update.message.voice:
                    answer = self.handle_voice(update, context, user_id)

                else:  # text detection
                    answer = NLP().text_input(update.message.text, self.get_language(user_id))

                intent_detected = answer.intent.display_name
                print(intent_detected)
                if intent_detected == NLP_OPTION[0]:  # itnroduce medicine
                    # self.set_medicine(user_id, 0, name)
                    if (len(str(answer.parameters[MEDICINE_TAGS[1]])) == 0 or len(
                            answer.parameters[MEDICINE_TAGS[2]]) == 0):
                        update.message.reply_text("An error has occurred, please repeat the audio")
                        return NLP
                    else:
                        self.set_medicine(user_id, 1, str(answer.parameters[MEDICINE_TAGS[1]]))
                        self.set_medicine(user_id, 2, self.split_date(answer.parameters[MEDICINE_TAGS[2]]))

                elif intent_detected == NLP_OPTION[1]:  # itnroduce prescription
                    print("estoy entrando aqui")
                    if (len(str(answer.parameters[PRESCRIPTION_TAGS[1]])) == 0 or len(
                            str(answer.parameters[PRESCRIPTION_TAGS[2]]['amount'])) == 0 or len(
                            answer.parameters[PRESCRIPTION_TAGS[3]]) == 0):
                        update.message.reply_text("An error has occurred, please repeat the audio")
                        return NLP

                    else:
                        self.set_prescription(user_id, 1, self.split_value(
                            answer.parameters[PRESCRIPTION_TAGS[1]]))  # cantidad de pastillas cada vez

                        self.set_prescription(user_id, 2, self.split_value(
                            answer.parameters[PRESCRIPTION_TAGS[2]]['amount']))  # frequencia de pastillas cada vez

                        self.set_prescription(user_id, 3,
                                              self.split_date(answer.parameters[PRESCRIPTION_TAGS[3]]))  # fecha

        except:
            user_id = update.callback_query.from_user.id

        self.set_counter(user_id, self.get_counter(user_id) + 1)
        logger.info(self.get_medicine(user_id))

        if self.get_counter(user_id) == 1:  # si acaba de introducir un medicamento
            update.message.reply_text(st.INTR_NLP_MSSGS[self.get_language(user_id)][self.get_counter(user_id)])
            return NLP
        else:
            if intent_detected == NLP_OPTION[0]:
                self.set_counter(user_id, 0)
                context.bot.send_message(chat_id=user_id,
                                         text=st.STR_SEND_NEW_MEDICINE_ISCORRECT[self.get_language(user_id)],
                                         reply_markup=yes_no_markup[self.get_language(user_id)])
                context.bot.send_message(chat_id=user_id,
                                         text=self.show_medicine(user_id), parse_mode=telegram.ParseMode.MARKDOWN)
                self.set_query(user_id, list(self.get_medicine(user_id).keys()),
                               list(self.get_medicine(user_id).values()))
                self.set_function(user_id, intent_detected)
                return self.set_state(user_id, CHECK_MED)

            else:
                self.set_counter(user_id, 0)
                a = list(self.get_prescription(user_id).keys())
                a.append('NAME REAL')
                b = list(self.get_prescription(user_id).values())
                b.append(cima.get_med_name(self.get_prescription(user_id)['NAME']))
                context.bot.send_message(chat_id=user_id,
                                         text=st.STR_SEND_NEW_PRESCRIPTION_ISCORRECT[self.get_language(user_id)],
                                         reply_markup=yes_no_markup[self.get_language(user_id)])
                context.bot.send_message(chat_id=user_id,
                                         text=self.show_prescription(user_id), parse_mode=telegram.ParseMode.MARKDOWN)

                self.set_query(user_id, a, b)
                self.set_function(user_id, intent_detected)
                return self.set_state(user_id, CHECK_PRE)

    @run_async
    def take_pill(self, update, context):
        """ Method that introduce pill take.
        :param update: Updater for bot token
        :param context: Handler's context
        :return: new state TAKE_PILL
        """
        logger.info('User introducing new pill taken')
        user_id = update.message.from_user.id
        dict = self.list_of_current_cn(user_id)
        if 'Boolean' not in dict:
            dyn_markup = self.makeKeyboard(dict, user_id)
            update.message.reply_text(st.INTR_PILL_MSSGS[self.get_language(user_id)][self.get_counter(update.message.from_user.id)],
                                      reply_markup=dyn_markup)
        else:
            update.message.reply_text(st.INTR_PILL_MSSGS[self.get_language(user_id)][self.get_counter(update.message.from_user.id)])
        return self.set_state(update.message.from_user.id, TAKE_PILL)

    def send_new_pill(self, update, context):
        """Asks the user information in order to complete the medicine form, and once completed sets the query ready to
        be sent.

        :param update: Updater for bot token
        :param context: Handler's context
        :return: state TAKE_PILL while form not completed, state CHECK_PILL once completed
        """

        try:
            user_id = update.message.from_user.id
            if self.get_counter(user_id) == 0:  # If we are in the first field of the form
                if update.message.photo:  # If user sent a photo, we apply
                    medicine_cn, validation_num = self.handle_pic(update, context, user_id)
                else:
                    medicine_cn, validation_num = self.split_code(update.message.text)

                if "error" in [medicine_cn, validation_num] or not self.verify_code(medicine_cn, validation_num):
                    update.message.reply_text(
                        st.STR_SEND_NEW_PILL_ERROR[self.get_language(user_id)])
                    return TAKE_PILL
                else:
                    self.set_pill(user_id, self.get_counter(user_id), medicine_cn)
            else:
                self.set_pill(user_id, self.get_counter(user_id), update.message.text)
        except:
            user_id = update.callback_query.from_user.id

        self.set_counter(user_id, self.get_counter(user_id) + 1)
        logger.info(self.get_pill(user_id))
        if self.get_counter(user_id) != len(st.INTR_PILL_MSSGS[self.get_language(user_id)]):
            self.bot.send_message(chat_id=user_id,
                                  text=st.INTR_PILL_MSSGS[self.get_language(user_id)][self.get_counter(user_id)])
            return TAKE_PILL
        else:
            self.set_counter(user_id, 0)
            context.bot.send_message(chat_id=user_id,
                                     text=st.STR_SEND_NEW_PILL_ISTAKENCORRECTLY[self.get_language(user_id)],
                                     reply_markup=yes_no_markup[self.get_language(user_id)])
            context.bot.send_message(chat_id=user_id,
                                     text=self.show_pill(user_id), parse_mode=telegram.ParseMode.MARKDOWN)
            self.set_query(user_id, list(self.get_pill(user_id).keys()), list(self.get_pill(user_id).values()))
            self.set_function(user_id, 'TAKE PILL')
            return self.set_state(user_id, CHECK_PILL)

    def show_pill(self, user_id):
        med_str = med_str = st.STR_SHOWPILL_TAKING[self.get_language(user_id)] + self.get_pill(user_id)['QUANTITY'] + st.STR_SHOWPILL_PILLSOF[self.get_language(user_id)] + \
                  cima.get_med_name(self.get_pill(user_id)['NAME']).split(' ')[0] + "* !"
        return med_str

    def check_pill(self, update, context):
        user_id = update.message.from_user.id
        context.bot.send_message(chat_id=user_id,
                                 text=st.STR_CHECK_PILL[self.get_language(user_id)],
                                 reply_markup=yes_no_markup[self.get_language(user_id)])
        return self.set_state(user_id, CHECK_PILL_PHOTO)

    def verificate_pill(self, update, context):
        user_id = update.message.from_user.id
        photo = update.message.photo
        # code checking photos

        return self.manage_response(update, context)

    def list_of_current_cn(self, user_id):
        self.set_function(user_id, 'GET LIST')
        self.set_query(user_id, ["user_id"], [str(user_id)])
        query = self.create_query(user_id)
        response = self.send_query(user_id, query)
        return json.loads(response)["parameters"]

    def makeKeyboard(self, arg, user_id):
            lista = []
            for key in arg:
                print("esto es arg[key]"+str(arg[key])+ "esto es key"+ str(key))
                lista.append([InlineKeyboardButton(text=arg[key], callback_data=key)])
            if self.get_states(user_id)[0] == SHOW_INFORMATION:
                lista.append([InlineKeyboardButton(text=st.STR_MAKEKEYBOARD, callback_data='Others')])
            print("esta es la lista" + str(lista))
            dyn_markup = InlineKeyboardMarkup(lista)
            return dyn_markup

    @run_async
    def show_information(self, update, context):
        logger.info('User ' + self.get_name(update.message.from_user) + '  searching for information')
        try:
            user_id = update.message.from_user.id
        except:
            user_id = update.callback_query.from_user.id
        self.set_state(user_id=user_id, state=SHOW_INFORMATION)
        dict = self.list_of_current_cn(user_id)
        if 'Boolean' not in dict:
            dyn_markup = self.makeKeyboard(dict, user_id)
            update.message.reply_text(
                st.STR_SHOW_INFORMATION_CHOOSEMED,
                reply_markup=dyn_markup)
            return self.set_state(user_id=user_id, state=CHOOSING)
        else:
            update.message.reply_text(st.STR_SHOW_INFORMATION_CHOOSEMED [self.get_language(user_id)])
            return SHOW_INFORMATION

    def show_infoAbout(self, update, context):
        try:
            user_id = update.message.from_user.id
            if update.message.photo:  # If user sent a photo, we apply
                medicine_cn, validation_num = self.handle_pic(update, context, user_id)
            else:
                if self.valid_input(update.message.text):
                    medicine_cn, validation_num = self.split_code(update.message.text)
                else:
                    update.message.reply_text(
                        st.STR_SHOW_INFOABOUT_METACHARACTERS[self.get_language(user_id)])
                    return SHOW_INFORMATION

            if "error" in [medicine_cn, validation_num] or not self.verify_code(medicine_cn, validation_num):
                update.message.reply_text(
                    st.STR_SHOW_INFOABOUT_ERROR[self.get_language(user_id)])
                return self.set_state(user_id=update.message.from_user.id, state=SHOW_INFORMATION)
            else:
                update.message.reply_text(cima.get_info_about(medicine_cn))
                update.message.reply_text(text=st.STR_SHOW_INFOABOUT_HELPEND[self.get_language(user_id)],
                                          reply_markup=markup[self.get_language(user_id)])
                return self.set_state(user_id=update.message.from_user.id, state=CHOOSING)
        except:
            user_id = update.callback_query.from_user.id
            medicine_cn = update.callback_query.data
            self.bot.send_message(text=cima.get_info_about(medicine_cn), chat_id=user_id)
            self.bot.send_message(chat_id=user_id, text=st.STR_SHOW_INFOABOUT_HELPEND[self.get_language(user_id)],
                                  reply_markup=markup[self.get_language(user_id)])
            return self.set_state(user_id=user_id, state=CHOOSING)

    def show_location(self, user_id):
        self.bot.send_message(chat_id=user_id, text=st.STR_SHOW_LOCATION[self.get_language(user_id)],
                              reply_markup=loc_markup[self.get_language(user_id)])
        # to clear all queries possibly made
        self.set_query(user_id, ["None"], ["None"])
        self.set_function(user_id, "None")
        return self.set_state(user_id, LOCATION)

    def print_location(self, update, context):
        user_id = update.message.from_user.id
        # If we want to delete the message of location, just use line below
        # self.bot.delete_message(chat_id=user_id, message_id=update.message.message_id)
        lat, lon = update.message.location.latitude, update.message.location.longitude

        maps = 'https://www.google.com/maps/search/farmacias+cercanas/@' + str(lat) + ',' + str(lon) + 'z'
        url = " <a href ='" + maps + "'> Click Here </a>"
        self.bot.send_message(chat_id=user_id,
                              text=url,
                              parse_mode=telegram.ParseMode.HTML)
        if self.get_states(user_id=user_id)[1] == REMINDERS:
            self.event.set()
            return self.set_state(user_id, END)
        else:
            self.bot.send_message(chat_id=user_id, text=st.STR_PRINT_LOCATION_HELPEND[self.get_language(user_id)],
                                  reply_markup=markup[self.get_language(user_id)])
            return self.set_state(user_id, CHOOSING)

    @run_async
    def see_calendar(self, update, context):
        logger.info('User ' + self.get_name(update.message.from_user) + '  seeing calendar')
        update.message.reply_text("Please select a date: ",
                                  reply_markup=telegramcalendar.create_calendar())

    @run_async
    # Method that handles the situations and depending on the current state, changes the state
    def inline_handler(self, update, context):
        user_id = update.callback_query.from_user.id
        if self.get_states(user_id)[0] == TAKE_PILL:
            self.send_new_pill(update, context)
        elif self.get_states(user_id)[0] == CHOOSING and self.get_states(user_id)[1] == SHOW_INFORMATION:
            medicine_cn = update.callback_query.data
            if medicine_cn == "Others":
                self.bot.send_message(chat_id=user_id,
                                      text="Please Introduce CN of medicine you want information about, or take a photo of it? \U0001F48A")
            else:
                self.show_infoAbout(update, context)
        elif self.get_states(user_id)[0] == CHECK_REM:
            self.get_medicine_CN(update, context)
        elif self.get_states(user_id)[0] == END or self.get_states(user_id)[0] == REMINDERS:
            name = update.callback_query.from_user.first_name
            self.bot.send_message(chat_id=user_id, text=(eval(st.STR_START_WELCOME_2[self.get_language(user_id)])),
                                  reply_markup=day_markup[self.get_language(user_id)])
        else:
            selected, date = telegramcalendar.process_calendar_selection(context.bot, update)
            if date is not None:
                date_str = date.strftime("%Y-%m-%d")
                if date_str == MAX_DATE:
                    date_str = "CHRONIC"
            if selected:
                if self.get_states(user_id)[0] == CHOOSING:
                    '''
                    context.bot.send_message(chat_id=user_id,
                                             text="You selected %s" % date_str,
                                             reply_markup=ReplyKeyboardRemove())
                                             '''
                if self.get_states(user_id)[0] == CHOOSING:
                    self.get_calendar_tasks(update, context, date.strftime("%Y-%m-%d"), user_id)
                    self.set_state(user_id, CHOOSING)
                elif self.get_states(user_id)[0] == JOURNEY:
                    self.set_journey(update, context, date.strftime("%Y-%m-%d"))
                    if self.get_states(user_id)[1] == CHOOSING:
                        self.set_state(user_id, JOURNEY)
                    elif self.get_states(user_id)[1] == JOURNEY:
                        self.set_state(user_id, JOURNEY)
                elif self.get_states(user_id)[0] == INTR_PRESCRIPTION:
                    context.bot.send_message(chat_id=user_id,
                                             text=date_str,
                                             reply_markup=ReplyKeyboardRemove())
                    self.set_prescription(user_id, self.get_counter(user_id), date.strftime("%Y-%m-%d"))
                    self.send_new_prescription(update, context)
                elif self.get_states(user_id)[0] == INTR_MEDICINE:
                    context.bot.send_message(chat_id=user_id,
                                             text=date_str,
                                             reply_markup=ReplyKeyboardRemove())
                    self.set_medicine(user_id, self.get_counter(user_id), date.strftime("%Y-%m-%d"))
                    self.send_new_medicine(update, context)
                elif self.get_states(user_id)[0] == NLP:
                    context.bot.send_message(chat_id=user_id,
                                             text=date_str,
                                             reply_markup=ReplyKeyboardRemove())
                    self.set_medicine(user_id, self.get_counter(user_id), date.strftime("%Y-%m-%d"))
                    self.send_new_medicine(update, context)
                    # self.set_prescription(user_id, self.get_counter(user_id), date.strftime("%Y-%m-%d"))
                    # self.send_new_prescription(update, context)

    @run_async
    # Returns all the reminders associated for a specific date and user_id
    def get_calendar_tasks(self, update, context, date, user_id):
        date_str = date
        if date_str == MAX_DATE:
            date_str = st.GET_CALENDAR_TASKJS_CHRONIC[self.get_language(user_id)]
        # connects to DataBase with Date and UserId asking for all the tasks of this date
        self.set_function(user_id, "TASKS CALENDAR")
        self.set_query(user_id, ["date"], [date])
        query = self.create_query(user_id)
        response = json.loads(self.send_query(user_id, query))
        message_id = update.callback_query.message.message_id
        self.bot.delete_message(chat_id=user_id, message_id=message_id)
        self.bot.send_message(chat_id=user_id,
                              text=eval(st.STR_GET_CALENDAR_TASKS_REMINDERS[self.get_language(user_id)]))
        self.bot.send_message(chat_id=user_id, text=st.STR_GET_CALENDAR_TASKS_HELPEND[self.get_language(user_id)],
                              reply_markup=markup[self.get_language(user_id)])

    @run_async
    # Method that prints systematically the current Treatment for a certain user_id
    def see_currentTreatment(self, update, context):
        logger.info('User ' + self.get_name(update.message.from_user) + ' seeing current Treatment')
        # connects to DataBase with UserId asking for all the medications he is currently taking
        user_id = update.message.from_user.id
        self.set_function(user_id, "CURRENT TREATMENT")
        self.set_query(user_id, ["user_id"], [str(user_id)])
        query = self.create_query(user_id)
        response = json.loads(self.send_query(user_id, query))
        if response['parameters']['reminder_info'] == "False":
            self.bot.send_message(chat_id=user_id, text=st.STR_SEE_CURRENTTREATMENT_IF[self.get_language(user_id)])
        else:
            self.bot.send_message(chat_id=user_id,
                                  text=eval(st.STR_SEE_CURRENTTREATMENT_ELSE[self.get_language(user_id)]),
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        self.set_query(user_id, ["None"], ["None"])
        return self.manage_response(update, context)

    @run_async
    # Method that prints systematically the History for a certain user_id
    def see_history(self, update, context):
        logger.info('User ' + self.get_name(update.message.from_user) + ' seeing History')
        # connects to DataBase with UserId asking if user took last reminders
        user_id = update.message.from_user.id
        self.set_function(user_id, "HISTORY")
        self.set_query(user_id, ["user_id"], [str(user_id)])
        query = self.create_query(user_id)
        response = json.loads(self.send_query(user_id, query))
        if response['parameters']['history'] == "False":
            update.message.reply_text(st.STR_SEE_HISTORY_IF[self.get_language(user_id)])
        else:
            update.message.reply_text(
                eval(st.STR_SEE_HISTORY_ELSE[self.get_language(user_id)]))
        self.set_query(user_id, ["None"], ["None"])
        return self.manage_response(update, context)

    @run_async
    # Method that prints systematically the Inventory for a certain user_id
    def see_inventory(self, update, context):
        logger.info('User ' + self.get_name(update.message.from_user) + ' seeing Inventory')
        # connects to DataBase with UserId asking if user took last reminders
        user_id = update.message.from_user.id
        self.set_function(user_id, "INVENTORY")
        self.set_query(user_id, ["user_id"], [str(user_id)])
        query = self.create_query(user_id)
        response = json.loads(self.send_query(user_id, query))
        if response['parameters']['inventory'] == "False":
            update.message.reply_text(st.STR_SEE_INVENTORY_IF[self.get_language(user_id)])
        else:
            update.message.reply_text(eval(st.STR_SEE_INVENTORY_ELSE[self.get_language(user_id)]))
        self.set_query(user_id, ["None"], ["None"])
        return self.manage_response(update, context)

    @run_async
    # Deletes a reminder using a CN for a certain user_id
    def delete_reminder(self, update, context):
        logger.info('User ' + self.get_name(update.message.from_user) + ' deleting reminder')
        user_id = update.message.from_user.id
        dict = self.list_of_current_cn(user_id)
        print(str(dict))
        if 'Boolean' not in dict:
            dyn_markup = self.makeKeyboard(dict, user_id)
            update.message.reply_text(st.STR_DELETE_REMINDER_CHOOSEMED[self.get_language(user_id)],
                                      reply_markup=dyn_markup)
            return self.set_state(user_id, CHECK_REM)
        else:
            update.message.reply_text(st.STR_DELETE_REMINDER_ANYMED[self.get_language(user_id)])
            update.message.reply_text(text=st.STR_DELETE_REMINDER_HELPEND[self.get_language(user_id)],
                                      reply_markup=markup[self.get_language(user_id)])
            return self.set_state(user_id, CHOOSING)

    # Method that asks for a CN and prints all the information and asks about if it should be removed or not
    def get_medicine_CN(self, update, context):
        try:
            if self.valid_input(update.message.text):
                medicine_CN = update.message.text
            else:
                update.message.reply_text(
                    st.STR_GETMEDICINECN_METACHARACTERS[self.get_language(user_id)])
                return GET_CN
            user_id = update.message.from_user.id
        except:
            user_id = update.callback_query.from_user.id
            medicine_CN = update.callback_query.data

        # connects to DataBase with UserId and get the current reminder for this medicine_CN.
        self.set_function(user_id, "GET REMINDER")
        self.set_query(user_id, ["CN"], [medicine_CN])
        query = self.create_query(user_id)
        response = json.loads(self.send_query(user_id, query))
        reminder_info = response['parameters']
        if reminder_info['CN'] == "False":
            self.bot.send_message(chat_id=user_id, text=st.STR_GETMEDICINECN_IFFALSE[self.get_language(user_id)])
            self.bot.send_message(chat_id=user_id, text=st.STR_GETMEDICINECN_HELPEND[self.get_language(user_id)], reply_markup=markup[self.get_language(user_id)])
            return self.set_state(user_id, CHOOSING)
        end_date = response['parameters']['end_date']
        if end_date == MAX_DATE:
            reminder_info = eval(st.STR_GETMEDICINECN_REMINDERINFOIF[self.get_language(user_id)])
        else:
            reminder_info = eval(st.STR_GETMEDICINECN_REMINDERINFOELSE[self.get_language(user_id)])
        self.bot.send_message(chat_id=user_id, text=st.STR_GETMEDICINECN_SHOULDREMOVE[self.get_language(user_id)] + reminder_info, parse_mode=telegram.ParseMode.MARKDOWN)
        self.bot.send_message(chat_id=user_id, text=st.STR_GETMEDICINECN_ISTHIS[self.get_language(user_id)], reply_markup=yes_no_markup[self.get_language(user_id)])
        self.set_query(user_id, ["CN"], [response['parameters']['CN']])
        self.set_function(user_id, 'DELETE REMINDER')
        return self.set_state(user_id, CHECK_REM)    
        
        
    # Method that creates a journey to be handled later and asks for the information
    @run_async
    def create_journey(self, update, context):
        user_id = update.message.from_user.id
        boolean = self.get_states(update.message.from_user.id)[0] == CHOOSING
        self.set_state(update.message.from_user.id, CHOOSING)
        logger.info('User ' + self.get_name(update.message.from_user) + ' creating journey')
        self.set_state(update.message.from_user.id, JOURNEY)
        if boolean:
            update.message.reply_text(st.STR_CREATE_JOURNEY_IF[self.get_language(user_id)],
                                      reply_markup=telegramcalendar.create_calendar())
        else: 
            update.message.reply_text(st.STR_CREATE_JOURNEY_ELSE[self.get_language(user_id)],
                                      reply_markup=telegramcalendar.create_calendar())
        return JOURNEY

    # Method that asks for the dates needed for a journey and changes the state of the bot to JOURNEY
    def set_journey(self, update, context, date):
        date_str = date
        if date == MAX_DATE:
            date_str = st.STR_SET_JOURNEY_CHRONIC[self.get_language(user_id)]
        user_id = update.callback_query.from_user.id
        if self.get_states(user_id)[1] == CHOOSING:
            self.set_dates(user_id, "departure", date)
            context.bot.send_message(chat_id=user_id,
                                     text=eval(st.STR_SET_JOURNEY_DEPARTURE[self.get_language(user_id)]),
                                     reply_markup=telegramcalendar.create_calendar())

        if self.get_states(user_id)[1] == JOURNEY:
            self.set_dates(user_id, "arrival", date)
            context.bot.send_message(chat_id=user_id,
                                     text=eval(st.STR_SET_JOURNEY_ARRIVAL[self.get_language(user_id)]),
                                     reply_markup=yes_no_markup[self.get_language(user_id)])
            self.set_query(user_id, ["departure_date", "arrival_date"],
                           [self.get_dates(user_id)[0], self.get_dates(user_id)[1]])
            self.set_function(user_id, 'JOURNEY')

    def send_reminders(self, data):
        for message in data:
            self.send_reminder(user_id=message[2], cn=str(message[0]), time=str(message[1]))

    # Sends a reminder using parsing
    def send_reminder(self, user_id, cn, time):
        if self.in_end(user_id):
            self.set_reminder(user_id, str(cn), str(time))
            reminder = st.STR_SEND_REMINDER_REMIDNER[self.get_language(user_id)]
            self.bot.send_message(chat_id=user_id,
                                  text="*`" + reminder + "`*\n",
                                  parse_mode=telegram.ParseMode.MARKDOWN,
                                  reply_markup=taken_pill_markup[self.get_language(user_id)])
            self.event.clear()
            return self.set_state(user_id, REMINDERS)
        else:
            return self.delay_reminder(user_id, cn, time)

    def delay_reminder(self, user_id, cn, time):
        self.event.wait()
        self.send_reminder(user_id, cn, time)
        self.event.clear()

    def intr_history_yes(self, update, context):
        user_id = update.message.from_user.id
        self.set_function(user_id, "INTRODUCE HISTORY")
        reminder = self.get_reminder(user_id)
        self.set_query(user_id, ["user_id", "NAME", "DATE", "BOOLEAN"],
                       [str(user_id), reminder['cn'], reminder['time'], "True"])
        query = self.create_query(user_id)
        response = json.loads(self.send_query(user_id, query))
        if response['parameters']['boolean'] == "False":
            update.message.reply_text(
                STR_INTR_HISTORY_YES_IFFALSE[self.get_language(user_id)])
            return self.show_location(user_id=user_id)
        if response['parameters']['remind'] == "Remind to buy":
            update.message.reply_text(
                st.STR_INTR_HISTORY_YES_IFREMINDTOBUY[self.get_language(user_id)])
            return self.show_location(user_id=user_id)
        elif response['parameters']['remind'] == "No reminder":
            update.message.reply_text(st.STR_INTR_HISTORY_YES_ELIFNOREMINDER[self.get_language(user_id)])
        self.event.set()
        return self.set_state(user_id, END)

    def intr_history_no(self, update, context):
        user_id = update.message.from_user.id
        self.set_function(user_id, "INTRODUCE HISTORY")
        reminder = self.get_reminder(user_id)
        self.set_query(user_id, ["user_id", "NAME", "DATE", "BOOLEAN"],
                       [str(user_id), reminder['cn'], reminder['time'], "False"])
        query = self.create_query(user_id)
        response = json.loads(self.send_query(user_id, query))
        if (response["parameters"]["boolean"] == "Postpone"):
            self.bot.send_message(chat_id=user_id, text=st.STR_INTR_HISTORY_NO_IFPOSTPONE[self.get_language(user_id)])
        else:
            self.bot.send_message(chat_id=user_id,
                                  text=st.STR_INTR_HISTORY_NO_ELSE[self.get_language(user_id)])
        self.event.set()
        return self.set_state(user_id, END)

    # Ends the communication between the user and the bot
    def exit(self, update, context):
        user_id = update.message.from_user.id
        self.bot.send_message(chat_id=user_id, text=st.STR_EXIT[self.get_language(user_id)], reply_markup=start_markup)
        logger.info('User ' + self.get_name(update.message.from_user) + ' finish with AideBot')
        self.event.set()
        return self.set_state(user_id, END)

    def getToTheMenu(self, update, context):
        try:
            user_id = update.message.from_user.id
        except:
            user_id = update.callback_query.from_user.id
        self.set_handling(user_id=user_id, text="False")
        self.set_pill(user_id=user_id, num=0, text="None")
        self.set_pill(user_id=user_id, num=1, text="None")
        self.set_function(user_id=user_id, text="None")
        self.set_dates(user_id=user_id, text="departure", date="None")
        self.set_dates(user_id=user_id, text="arrival", date="None")
        self.set_counter(user_id=user_id, num=0)
        logger.info('User ' + self.get_name(update.message.from_user) + ' in the menu after quitting from function')
        update.message.reply_text("Is there any other way I can help you?",
                                  reply_markup=markup[self.get_language(user_id)])
        return self.set_state(user_id=user_id, state=CHOOSING)

    # Main of the Client.py, where the bot is activated and creates the transition to the different functionalities
    def main(self):
        # Create the Updater and pass it your bot's token.
        # Make sure to set use_context=True to use the new context based callbacks
        updater = Updater(token=TOKEN_PROVE, use_context=True, workers=50)
        dp = updater.dispatcher
        conv_handler = ConversationHandler(
            allow_reentry=True,
            entry_points=[CommandHandler('start', self.start)],

            states={
                LOGIN: [MessageHandler(Filters.text, self.intr_pwd)],
                NEW_USER: [MessageHandler(Filters.text, self.new_user)],
                CHOOSING: [MessageHandler(Filters.regex('^New Prescription') | Filters.regex('^Nueva Receta'),
                                          self.intr_prescription),
                           MessageHandler(Filters.regex('^New Medicine') | Filters.regex('^Nuevo Medicamento'),
                                          self.intr_medicine),
                           MessageHandler(Filters.regex('^Voice') | Filters.regex('^Voz'),
                                          self.intr_nlp),
                           MessageHandler(Filters.regex('^Take Pill') | Filters.regex('^Tomar Pastilla'),
                                          self.take_pill),
                           MessageHandler(Filters.regex('^Calendar') | Filters.regex('^Calendario'),
                                          self.see_calendar),
                           MessageHandler(Filters.regex('^Current Treatment') | Filters.regex('^Tratamientos Actuales'),
                                          self.see_currentTreatment),
                           MessageHandler(Filters.regex('^History') | Filters.regex('^Historial'),
                                          self.see_history),
                           MessageHandler(Filters.regex('^Inventory') | Filters.regex('^Inventorio'),
                                          self.see_inventory),
                           MessageHandler(Filters.regex('^Information') | Filters.regex('^Información'),
                                          self.show_information),
                           MessageHandler(Filters.regex('^Delete reminder') | Filters.regex('^Eliminar Recordatorio'),
                                          self.delete_reminder),
                           MessageHandler(Filters.regex('^Journey') | Filters.regex('^Viaje'),
                                          self.create_journey),
                           MessageHandler(Filters.regex('^Exit') | Filters.regex('^Salir'), self.exit)
                           ],
                INTR_PRESCRIPTION: [
                    MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                    MessageHandler(Filters.text | Filters.photo | Filters.voice, self.send_new_prescription)],
                INTR_MEDICINE: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                                MessageHandler(Filters.text | Filters.photo | Filters.voice, self.send_new_medicine)],
                NLP: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                      MessageHandler(Filters.text | Filters.photo | Filters.voice, self.nlp_mode)],
                TAKE_PILL: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                            MessageHandler(Filters.text | Filters.photo, self.send_new_pill)],
                SHOW_INFORMATION: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                                   MessageHandler(Filters.text | Filters.photo, self.show_infoAbout)],
                LOCATION: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                           MessageHandler(Filters.location, self.print_location),
                           MessageHandler(Filters.regex("^Don't Send Location") | Filters.regex("No enviar ubicación"), self.manage_response)],
                CHECK_PRE: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                            MessageHandler(Filters.regex('^YES$') | Filters.regex('^SÍ'), self.manage_response),
                            MessageHandler(Filters.regex('^NO$'), self.intr_prescription)],
                CHECK_MED: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                            MessageHandler(Filters.regex('^YES$') | Filters.regex('^SÍ'), self.manage_response),
                            MessageHandler(Filters.regex('^NO$'), self.intr_medicine)],
                CHECK_REM: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                            MessageHandler(Filters.regex('^YES$') | Filters.regex('^SÍ'), self.manage_response),
                            MessageHandler(Filters.regex('^NO$'), self.delete_reminder)],
                CHECK_PILL: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                             MessageHandler(Filters.regex('^YES$') | Filters.regex('^SÍ'), self.verificate_pill),
                             MessageHandler(Filters.regex('^NO$'), self.take_pill)],
                CHECK_PILL_PHOTO: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                                   MessageHandler(Filters.photo, self.manage_response),
                                   MessageHandler(Filters.regex('^NO$'), self.delete_reminder)],
                GET_CN: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                         MessageHandler(Filters.text, self.get_medicine_CN)],
                JOURNEY: [MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.getToTheMenu),
                          MessageHandler(Filters.regex('^YES$') | Filters.regex('^SÍ'), self.manage_response),
                          MessageHandler(Filters.regex('^NO$'), self.create_journey)],
                END: [MessageHandler(Filters.regex('^TAKEN'), self.intr_history_yes),
                      MessageHandler(Filters.regex('^POSTPONE'), self.intr_history_no),
                      MessageHandler(Filters.text, self.start)
                      ]
            },
            fallbacks=[MessageHandler(Filters.regex('^Exit$') | Filters.regex('^Salir'), self.exit)]
        )

        dp.add_handler(conv_handler)
        dp.add_handler(CallbackQueryHandler(self.inline_handler))
        updater.start_polling()
        updater.idle()

        if __name__ == '__main__':
            pilldora = PillDora()
        pilldora.main()
