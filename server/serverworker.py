import datetime
import json
import logging

import server.cima as cima
from server.database import DBMethods

MAX_DATE = "2036-12-31"


class ServerWorker:

    def __init__(self, user_id):
        self.user_id = user_id
        self.localhost = "localhost"
        self.port = 8080
        self.checker = DBMethods()
        self.logger = logging.getLogger('ServerWorker')

    def handler_query(self, query):
        parsed_string = json.loads(query)
        instruction = parsed_string["function"]
        user_id = parsed_string["user_id"]

        # CHECKING IF THERE IS ANY USER WITH A CERTAIN USER_ID
        if instruction == "CHECK USER":
            user_correct = self.checker.check_user(user_id=user_id)
            response = self.bot_parser(user_id=user_id, function="CHECK USER") + ' "boolean": "' + str(
                user_correct) + '"}}'

        # CHECKING IF THE USER IS INTRODUCING THE CORRECT PASSWORD
        elif instruction == "CHECK PASSWORD":
            password = parsed_string["parameters"]["password"]
            pwd_correct = self.checker.check_password(user_id=user_id, password=password)
            response = self.bot_parser(user_id=user_id, function="CHECK PASSWORD") + ' "boolean": "' + str(
                pwd_correct) + '"}}'

        # ADDING A NEW USER
        elif instruction == "NEW PASSWORD":
            new_password = parsed_string["parameters"]["new_password"]
            new_age=parsed_string["parameters"]["new_age"]
            new_gender=parsed_string["parameters"]["new_gender"]
            new_postalcode=parsed_string["parameters"]["new_postalcode"]
            user_added = self.checker.add_user(new_user=user_id, new_password=new_password, new_age=new_age, new_gender=new_gender, new_postalcode=new_postalcode)
            while not user_added:
                user_added = self.checker.add_user(new_user=user_id, new_password=new_password, new_age=new_age, new_gender=new_gender, new_postalcode=new_postalcode)
            response = self.bot_parser(user_id=user_id, function="NEW PASSWORD") + ' "boolean": "' + str(
                user_added) + '"}}'

        # INTRODUCING NEW PRESCRIPTION
        elif instruction == "INTRODUCE PRESCRIPTION":
            national_code = parsed_string["parameters"]["NAME"]
            is_there = self.checker.check_receipt(user_id=user_id, cn=national_code)
            param = ""
            if not is_there:
                # No more prescriptions with same CN
                self.checker.introd_receipt(user_id=user_id, query_parsed=parsed_string["parameters"],
                                            date=datetime.date.today().strftime("%Y-%m-%d"))
                param = ' "Code": "0"'

            elif not self.checker.check_medicine_frequency(user_id=user_id, cn=national_code,
                                                           freq=parsed_string["parameters"]["FREQUENCY"]):
                # Another prescriptions with same CN different frequency
                param = '"Code": "1" , "freq_database" : "' + str(self.checker.get_medicine_frequency(user_id=user_id,
                                                                                                      cn=national_code)) + '", "freq_introduced" : "' + str(
                    parsed_string["parameters"]["FREQUENCY"][0][0]) + '"'

            else:
                # Same prescriptions already in DB
                param = '"Code" : "2"'

            data = self.checker.get_cn_from_inventory(user_id=user_id, cn=national_code)
            if data is ():
                # User does not have this medicine in its DB inventory
                param += ',"inventory":"None"'
            else:
                total_in_inventory = 0
                for values in data:
                    total_in_inventory += values[1]
                days_between = (datetime.datetime.strptime(parsed_string["parameters"]["END_DATE"],
                                                           "%Y-%m-%d") - datetime.datetime.now()).days + 2
                total_needed = int(parsed_string["parameters"]["QUANTITY"]) * 24 / int(
                    parsed_string["parameters"]["FREQUENCY"]) * days_between
                if total_in_inventory >= total_needed:
                    param += ',"inventory":"Enough"'
                else:
                    param += ',"inventory":"Need to buy"'
            response = self.bot_parser(user_id=user_id, function="INTRODUCE PRESCRIPTION") + param + '}}'

        # INTRODUCING NEW MEDICINE BOUGHT:
        elif instruction == "INTRODUCE MEDICINE":
            self.checker.intr_inventory(user_id=user_id, query_parsed=parsed_string["parameters"])
            response = self.bot_parser(user_id=user_id, function="INTRODUCE MEDICINE") + """ "Code": "0"}}"""

        # INTRODUCING NEW MEDICINE BOUGHT:
        elif instruction == "TAKE PILL":
            out=self.checker.intr_taken_pill(user_id=user_id, query_parsed=parsed_string["parameters"])
            response = self.bot_parser(user_id=user_id, function="TAKE PILL") + '"Code": "'+out+'"}}'

        # THE USER WANTS TO PLAN A JOURNEY
        elif instruction == "JOURNEY":
            # WE OUTPUT A SERIES OF ACTIONS TO BE DONE FROM A LEAVING DATE TO THE DEPARTURE ONE
            [begin, end] = [parsed_string["parameters"]["departure_date"],
                            parsed_string["parameters"]["arrival_date"]]
            # IF THE BEGINNING DATe AND THE END DATE CONFLICTS, THE METHOD WILL RETURN A NULL CALENDAR OUTPUT
            calendar_output = self.checker.get_reminders(user_id=user_id, date=begin, to_date=end)
            if bool(calendar_output):
                journey_info = ""
                for output in list(calendar_output.keys()):
                    journey_info += "\\t-> " + cima.get_med_name(str(output)) + " : " + str(
                        calendar_output[output]) + "\\n"
            else:
                journey_info = "No meds need to be taken as there is no prescription for these dates."
            response = self.bot_parser(user_id=user_id,
                                       function="JOURNEY") + '"journey_info" : "' + journey_info + '"}}'

        # THE USER WANTS INFORMATION ABOUT THE REMINDERS OF A SPECIFIC DATE
        elif instruction == "TASKS CALENDAR":
            # WE OUTPUT A SERIES OF ACTIONS TO BE DONE FOR A SPECIFIC DATE
            date_selected = parsed_string["parameters"]["date"]
            calendar_output = self.checker.get_reminders(user_id=user_id, date=date_selected)
            if calendar_output is not None:
                journey_info = ""
                for output in calendar_output:
                    time = str(output[1]).split(',')[1] if len(str(output[1]).split(',')) == 2 else str(output[1])
                    journey_info += "\\t-> " + cima.get_med_name(str(output[0])) + " : " + time + "\\n"
            response = self.bot_parser(user_id, "TASKS CALENDAR") + '"tasks" : "' + journey_info + '"}}'

        # THE USER WANTS TO DELETE A REMINDER
        elif instruction == "DELETE REMINDER":
            # WE CHECK IF A MEDICINE REMINDER IS THERE FIRST
            cn = parsed_string["parameters"]["CN"]
            deleted = self.checker.delete_reminders(user_id=user_id, national_code=cn)
            response = self.bot_parser(user_id=user_id, function="DELETE REMINDER") + '"boolean" : "' + str(
                deleted) + '"}}'

        # THE USER ASKS FOR THE CURRENT TREATMENT
        elif instruction == "CURRENT TREATMENT":
            current_treatment = self.checker.get_currentTreatment(user_id=user_id)
            if current_treatment is not ():
                current_treatment_info = ""
                for output in current_treatment:
                    date_str = str(output[1]).split()[0]
                    if date_str == MAX_DATE:
                        current_treatment_info += "\\t-> Taking *" + cima.get_med_name(
                            str(output[0])) + " chronically* \\n"
                    else:
                        current_treatment_info += "\\t-> Taking *" + cima.get_med_name(
                            str(output[0])) + "* until the date of *" + date_str + "*\\n"
            else:
                current_treatment_info = "False"
            response = self.bot_parser(user_id=user_id,
                                       function="CURRENT TREATMENT") + '"reminder_info" : "' + current_treatment_info + '"}}'

        # THE USER ASKS FOR THE HISTORY OF PILLS TAKEN
        elif instruction == "HISTORY":
            history = self.checker.get_history(user_id=user_id)
            if history is not ():
                history_info = ""
                for output in history:
                    history_info += "\\t-> " + cima.get_med_name(str(output[0])) + " of " + str(output[1])
                    if output[2]:
                        history_info += ": taken\\n"
                    else:
                        history_info += ": not taken\\n"
            else:
                history_info = "False"
            response = self.bot_parser(user_id=user_id,
                                       function="HISTORY") + '"history" : "' + history_info + '"}}'

            # THE USER ASKS TO INTRODUCE HISTORY OF PILLS TAKEN
        elif instruction == "INTRODUCE HISTORY":
            history = self.checker.intr_to_history(user_id=user_id, query_parsed=parsed_string["parameters"])
            query="None"
            if parsed_string["parameters"]["BOOLEAN"] == "True":
                quantity=self.checker.get_quantity_taken(user_id=user_id, cn=parsed_string["parameters"]["NAME"])
                query= self.checker.reminder_taken(user_id=user_id, cn=parsed_string["parameters"]["NAME"], quantity_taken=quantity)
            response = self.bot_parser(user_id=user_id,
                                       function="INTRODUCE HISTORY") + '"boolean" : "' + str(history) + '" , "remind":"'+query+'"}}'

            # THE USER ASKS FOR THE HISTORY OF PILLS TAKEN
        elif instruction == "INVENTORY":
            inventory = self.checker.get_inventory(user_id=user_id)
            if inventory is not ():
                inventory_info = ""
                for output in inventory:
                    inventory_info += "\\t-> There are " + str(output[1]) + " of " + cima.get_med_name(
                        str(output[0])) + " which expire on " + datetime.datetime.strftime(output[2],
                                                                                           "%Y-%m-%d")+"\\n"
            else:
                inventory_info = "False"
            response = self.bot_parser(user_id=user_id,
                                       function="INVENTORY") + '"inventory" : "' + inventory_info + '"}}'

        # THE USER ASKS FOR THE REMINDERS FOR TODAY ON A SPECIFIC NATIONAL CODE
        elif instruction == "GET REMINDER":
            national_code = parsed_string["parameters"]["CN"]
            reminder_info = self.checker.get_reminders(user_id=user_id, date=datetime.date.today().strftime("%Y-%m-%d"),
                                                       cn=national_code)
            # THIS MEANS THAT WE GOT INFORMATION ABOUT THIS MEDICINE, SO WE ARE PARSING IT
            if reminder_info != '"False"':
                date_str = datetime.datetime.strftime(reminder_info[0][2], "%Y-%m-%d")
                reminder_info = '"CN":"' + str(reminder_info[0][0]) + '","frequency":"' + str(
                    reminder_info[0][1]) + '","end_date":"' + date_str + '"'
            else:
                # THIS MEANS THAT WE GOT NO INFORMATION ABOUT THIS MEDICINE FOR THE REMINDERS OF TODAY AND WE SEND NONE.
                reminder_info = '"CN":' + reminder_info
            response = self.bot_parser(self.user_id,
                                       function="GET REMINDER") + reminder_info + '}}'

        elif instruction == "GET LIST":
            data = self.checker.getCNList(user_id)
            if data is ():
                info='"Boolean":"False"}'
            else:
                references={}
                for item in data:
                    references[item[0]]=item[1]
                info=json.dumps(references).replace('{','')
            response=self.bot_parser(self.user_id, function="GET LIST") + info +'}'

        # IF WE SEND A WRONG QUERY, WE SEND THE INFORMATION LIKE THIS
        else:
            response = self.bot_parser(user_id=user_id,
                                       function="ERROR QUERY") + '"content" : "The query ' + instruction + ' is not on the query database"}}'
        self.logger.info(response)
        return response

    # METHOD USED TO PARSE ALL THE INFORMATION SENT TO THE CLIENT.PY (JSON)
    def bot_parser(self, user_id, function):
        return """{"user_id": """ + str(user_id) + ', "function": "' + function + '", "parameters": {'
