from Server.database import DBMethods
import json
import datetime
import logging


class Reminder(object):
    def __init__(self, user_id, medicine, hour_of_pill):
        self.user_id = user_id
        self.cn = medicine["NATIONAL_CODE"]
        self.hour = hour_of_pill


class ServerWorker:

    def __init__(self, user_id):
        self.user_id = user_id
        self.localhost = "localhost"
        self.port = 8080
        self.checker = DBMethods()
        self.logger = logging.getLogger('ServerWorker')

    def connectClient(self):
        # Connexió amb la DB del Servidor
        self.checker = DBMethods()

    def handler_query(self, query):
        parsed_string = json.loads(query)
        instruction = parsed_string["function"]
        # Checking if there is any user with this user_id
        if instruction == "CHECK USER":
            user_id = parsed_string["parameters"]["user_id"]
            print(user_id)
            user_correct = self.checker.check_user(user_id=user_id)
            response = self.bot_parser(user_id=user_id, function="CHECK USER") + ' "boolean": "' + str(
                user_correct) + '"}}'
            self.logger.info(response)
            return response
        # Checking if the user is introducing a correct password (we pass
        elif instruction == "CHECK PASSWORD":
            user_id = parsed_string["user_id"]
            password = parsed_string["parameters"]["password"]
            pwd_correct = self.checker.check_password(user_id=user_id, password=password)
            response = self.bot_parser(user_id=user_id, function="CHECK PASSWORD") +' "boolean": "' + str(
                pwd_correct) + '"}}'
            self.logger.info(response)
            return response
        # Add a new user
        elif instruction == "NEW PASSWORD":
            new_user = parsed_string["user_id"]
            new_password = parsed_string["parameters"]["new_password"]
            user_added = self.checker.add_user(new_user=new_user, new_password=new_password)
            while not user_added:
                user_added = self.checker.add_user(new_user=new_user, new_password=new_password)
            response = self.bot_parser(user_id=new_user, function="NEW PASSWORD") + ' "boolean": "' + str(
                user_added) + '"}}'
            self.logger.info(response)
            return response
        # Introduce medicine
        elif instruction == "INTRODUCE MEDICINE":
            user_id = parsed_string["user_id"]
            national_code = parsed_string["parameters"]["NAME"]
            is_there = self.checker.check_receipt(user_id=user_id, cn=national_code)
            # We are checking if the medicine is already on the database
            if not is_there:
                # If we are here, it means that the medicine wasn't on the database, so we input all the data
                self.checker.introd_receipt(user_id=user_id, query_parsed=parsed_string["parameters"], date=datetime.date.today().strftime("%Y-%m-%d"))
                response = self.bot_parser(user_id=user_id, function="INTRODUCE MEDICINE") + """ "Code": "0"}}"""
                #self.actualize_daily_table(user_id)
                self.logger.info(response)
                return response
            elif not self.checker.check_medicine_frequency(user_id=user_id, cn=national_code,
                                                           freq=parsed_string["parameters"]["FREQUENCY"]):
                # If we are here, the medicine is already on the database, we check first if the frequencies concur,
                # if not PROBLEM!
                response = self.bot_parser(user_id=user_id,
                                           function="INTRODUCE MEDICINE") + '"Code": "1" , "freq_database" : "' + str(
                    self.checker.get_medicine_frequency(user_id=user_id,
                                                        cn=national_code)) + '", "freq_introduced" : "' + str(
                    parsed_string["parameters"]["FREQUENCY"]) + '"}}'
                self.logger.info(response)
                return response

            else:
                # If we are here, the medicine is already on the database, and the times match, so we add the
                # quantity only
                # AQUI EN EL FUTURO TOCAREMOS EL INVENTARIO
                response = self.bot_parser(user_id=user_id, function=
                "INTRODUCE MEDICINE") + '"Code" : "2"}}'
                self.logger.info(response)
                return response

        elif instruction == "JOURNEY":
            # We output a series of actions to be done from a date to another one.
            [user_id, begin, end] = [parsed_string["user_id"], parsed_string["parameters"]["departure_date"],
                                     parsed_string["parameters"]["arrival_date"]]
            # If the beginning date and the end date create conflicts, the method will return a null calendar output
            calendar_output = self.checker.get_reminders(user_id=user_id, date=begin, to_date=end)
            num_days=self.days_between(end, begin)
            if calendar_output is not None:
                journey_info="Quantity of meds to take:\n"
                for output in calendar_output:
                    journey_info+="\t-> "+ output[0]+ " : "+ output[1]*num_days +"\n"
            # Right now, the journey will have the national code, on the future, we will use the medicine name!
            response = self.bot_parser(user_id=user_id,
                                       function="JOURNEY") + '"journey_info" : "' + journey_info + '"}}'
            self.logger.info(response)
            return response

        elif instruction == "TASKS CALENDAR":
            # We output a series of actions to be done from a date.
            [user_id, date_selected] = [parsed_string["user_id"],parsed_string["parameters"]["date"]]
            calendar_output = self.checker.get_reminders(user_id=user_id, date=date_selected)
            if calendar_output is not None:
                journey_info = "Quantity of meds to take:\n"
                for output in calendar_output:
                    journey_info += "\t-> " + output[0] + " : " + output[1]+ "\n"
            response = self.bot_parser(user_id, "TASKS CALENDAR") + '"tasks" : "' + journey_info + '"}}'
            self.logger.info(response)
            return response
        elif instruction == "DELETE REMINDER":
            # We check if the medicine introduced is there or not.
            [user_id, cn] = [parsed_string["user_id"], parsed_string["parameters"]["CN"]]
            deleted = self.checker.delete_information(user_id=user_id, national_code=cn)
            response = self.bot_parser(user_id=user_id, function="DELETE REMINDER") + '"boolean" : "' + str(
                deleted) + '"}}'
            self.logger.info(response)
            return response
        elif instruction == "HISTORY":
            user_id = parsed_string["parameters"]["user_id"]
            history = self.checker.get_history(user_id=user_id)
            if history is not None:
                history_info = "History of all Meds currently being taken :\n"
                for output in history:
                    history_info += "\t-> Taking  " + output[0] + " until the date of " + output[1]+ "\n"
            response = self.bot_parser(user_id=user_id, function="HISTORY") + '"reminder_info" : "' + history_info + '"}}'
            self.logger.info(response)
            return response
        elif instruction == "GET REMINDER":
            [user_id, national_code] = [parsed_string["user_id"], parsed_string["parameters"]["CN"]]
            reminder_info = self.checker.get_reminders(user_id=user_id, date=datetime.date.today().strftime("%Y-%m-%d"), cn=national_code)
            if(reminder_info!="False"):
                reminder_info = "Medicine "+reminder_info[0] +" taken with a frequency of "+reminder_info[1] +" until the date of " +reminder_info[2] +"."
            response = self.bot_parser(self.user_id,
                                       function="GET REMINDER") + '"reminder_info" : "' + reminder_info + '"}}'
            self.logger.info(response)
            return response
        else:
            user_id = parsed_string["user_id"]
            response = self.bot_parser(user_id=user_id,
                                       function="ERROR QUERY") + '"content" : "The query ' + instruction + ' is not on the query database"}}'
            self.logger.info(response)
            return response

    def bot_parser(self, user_id, function):
        return """{"user_id": """ + str(user_id) + ', "function": "' + function + '", "parameters": {'

    def actualize_daily_table(self, user_id=None):
        if user_id:
            today = datetime.date.today().strftime("%Y-%m-%d")
            reminder_info = self.checker.get_reminders(user_id, today)
            response = self.bot_parser(self.user_id, "DAILY REMINDER") + '"reminder_info" : "' + reminder_info + '"}}'
            self.logger.info(response)
            return response
        else:
            today = datetime.date.today().strftime("%Y-%m-%d")
            reminder_info = self.checker.get_reminders_all(today)
            response = self.bot_parser("ALL", "DAILY REMINDER") + '"reminder_info" : "' + reminder_info + '"}}'
            self.logger.info(response)
            return response

    def days_between(d1, d2):
        d1 = datetime.strptime(d1, "%Y-%m-%d")
        d2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((d2 - d1).days)

    def json_query_comprovar(self, query):
        query_1 ="""{
                "glossary": {
                    "title": "example glossary",
                    "GlossDiv": {
                        "title": "S",
                        "GlossList": {
                            "GlossEntry": {
                                "ID": "SGML",
                                "SortAs": "SGML",
                                "GlossTerm": "Standard Generalized Markup Language",
                                "Acronym": "SGML",
                                "Abbrev": "ISO 8879:1986",
                                "GlossDef": {
                                    "para": "A meta-markup language, used to create markup languages such as DocBook.",
                                    "GlossSeeAlso": ["GML", "XML"]
                                },
                                "GlossSee": "markup"
                            }
                        }
                    }
                }
        }"""
        query_jsoned = json.dumps()