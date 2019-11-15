import datetime

import pymysql


class DatabaseConnectionCredentials:

    @property
    def credentials(self):
        return {'ip': 'localhost', 'user': 'paesav', 'password': '12345678', 'database': 'aidebot'}


class Database(DatabaseConnectionCredentials):
    # INITIALIZE THE DATABASE CONNECTION WITH THE CREDENTIALS
    def __init__(self):
        self._conn = pymysql.connect(self.credentials['ip'], self.credentials['user'], self.credentials['password'],
                                     self.credentials['database'])
        self._cursor = self._conn.cursor()

    # METHOD THAT RETURNS AN INSTANCE OF THE DATABASE CONNECTION CREDENTIALS
    def __enter__(self):
        return self

    # METHOD THAT ENDS THE CONNECTION
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.commit()
        self.connection.close()

    # SERIES OF METHODS NEEDED FOR THE MANIPULATION OF THE DATA ON THE MYSQL DATABASE
    @property
    def connection(self):
        return self._conn

    @property
    def cursor(self):
        return self._cursor

    def commit(self):
        self.connection.commit()

    def execute(self, sql_query):
        self.cursor.execute(sql_query)

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    def query(self, sql_query):
        self.cursor.execute(sql_query)
        return self.fetchall()


class DBMethods:

    def check_user(self, user_id):
        with Database() as db:
            data = db.query("SELECT id FROM aidebot.users where id={id}".format(id=user_id))

            if not data:
                return False
            else:
                return True

    def add_user(self, new_user, new_password):
        with Database() as db:
            db.execute(
                "INSERT INTO aidebot.users (id, password) VALUES ({id},'{pwd}')".format(id=new_user,
                                                                                        pwd=new_password))
            data = db.query("SELECT id FROM aidebot.users where id={id}".format(id=new_user))

            if not data:
                return False
            else:
                return True

    def check_password(self, user_id, password):

        with Database() as db:
            data = db.query("SELECT password FROM aidebot.users where id={id}".format(id=user_id))
            if password != data[0][0]:
                return False
            else:
                return True

    def introd_receipt(self, query_parsed, user_id, date):
        with Database() as db:
            exists = self.check_receipt(user_id=user_id, cn=query_parsed['NAME'])
            if not exists:
                db.execute('''INSERT INTO aidebot.receipts (user_id, national_code, frequency, quantity, begin_date, end_date, name)
                            values ({id},{cn},{frequency},'{quantity}','{init}','{end}', '{name}')'''.format(
                    id=user_id, cn=query_parsed['NAME'], frequency=query_parsed['FREQUENCY'],
                    quantity=query_parsed['QUANTITY'],
                    init=date,
                    end=query_parsed['END_DATE'],
                    name=query_parsed['NAME REAL']
                ))
                # Daily Reminders is table used to have the current reminders for one day.
                # Every time day finish we check if end_Date in receipts is today. If it is today, delete reminder from daily_reminders
                self.create_reminders(user_id=user_id, query_parsed=query_parsed)
            else:
                # TODO: Añadir cantidad de pastillas?
                return False

    def check_receipt(self, cn, user_id):
        with Database() as db:
            data = db.query('''SELECT count(*) FROM aidebot.receipts WHERE user_id={id} and national_code={med}
            '''.format(id=user_id, med=cn))
            if data[0][0] == 0:
                return False
            else:
                return True

    def get_receipts(self, user_id, cn):
        with Database() as db:
            data = db.query(''' SELECT national_code, frequency, end_date
                FROM aidebot.receipts 
                WHERE user_id={id} and national_code={cn}
               '''.format(cn=cn, id=user_id
                          ))
            return data

    def get_medicine_frequency(self, user_id, cn):
        with Database() as db:
            data = db.query('''SELECT frequency 
            FROM aidebot.receipts
            WHERE user_id={id} and national_code={cn}
            '''.format(id=user_id, cn=cn))
            return data

    def check_medicine_frequency(self, user_id, cn, freq):
        with Database() as db:
            data = db.query('''SELECT frequency FROM aidebot.receipts WHERE user_id={id} and national_code={cn}
            '''.format(id=user_id, cn=cn))

            if data[0][0] == freq:
                return True
            else:
                return False

    def get_user_receipts_frequency(self, user_id):
        with Database() as db:
            data = db.query(''' SELECT national_code,frequency
             FROM aidebot.receipts 
             WHERE user_id={id}
            '''.format(id=user_id
                       ))
            return data

    def getCNList(self, user_id):
        with Database() as db:
            data = db.query(''' SELECT national_code, name
                FROM aidebot.receipts 
                WHERE user_id={id} ORDER BY frequency ASC
                '''.format(id=user_id))
            return data

    def get_currentTreatment(self, user_id):
        with Database() as db:
            data = db.query(''' SELECT national_code, end_date
                FROM aidebot.receipts 
                WHERE user_id={id}
                '''.format(id=user_id))
            return data

    def intr_taken_pill(self, user_id, query_parsed):
        query_parsed['DATE'] = datetime.datetime.now()
        query_parsed['BOOLEAN'] = "True"
        exact_time = datetime.datetime.now()
        with Database() as db:
            db.execute('''INSERT INTO aidebot.history (user_id, national_code, last_taken_pill, taken)
                                          values ({id},{cn},'{date}', {boolean})'''.format(id=user_id,
                                                                                           cn=query_parsed['NAME'],
                                                                                           date=exact_time,
                                                                                           boolean=query_parsed[
                                                                                               'BOOLEAN'],
                                                                                           ))
            # verify if user has any daily reminder of this med. If so, mark next reminder as taken
            min_time = db.query(
                '''select min(time) from aidebot.daily_reminders where time >= '{time}' and user_id = {id} and 
                national_code = {cn}'''.format(
                    id=user_id, time=exact_time.strftime("%H:%M:%S"), cn=query_parsed['NAME']))
            next_rem = "24:00:00" if str(min_time[0][0]).find("day") > 0 else str(min_time[0][0])

            db.execute('''update aidebot.daily_reminders set Taken = 3 where time = '{time}' and user_id = {id} and 
                national_code = {cn}'''.format(id=user_id, time=next_rem, cn=query_parsed['NAME']))

            data = self.get_cn_from_inventory(user_id, query_parsed['NAME'])
            if data is ():
                return "0"
            else:
                self.reminder_taken(user_id=user_id, cn=query_parsed['NAME'], quantity=str(query_parsed['QUANTITY']))
                return "1"

    def postpone_or_check_reminder(self, user_id, time, cn, condition):
        with Database() as db:
            if condition == "True":
                num = 3
            else:
                data = db.query(''' SELECT Taken FROM aidebot.daily_reminders
                WHERE user_id={id} and national_code={cn} and time='{time}'
                '''.format(id=user_id, cn=cn, time=time))
                num = data[0][0] + 1

            db.execute(
                '''update aidebot.daily_reminders set Taken = {Num} where time = '{time}' and user_id = {id} and national_code = {cn}'''.format(
                    id=user_id, time=time, cn=cn, Num=num))

            return num

    def intr_to_history(self, user_id, query_parsed):
        data = self.get_cn_from_inventory(user_id, query_parsed['NAME'])
        if query_parsed['BOOLEAN'] == "True" and data is ():
            return "False"

        num = self.postpone_or_check_reminder(user_id=user_id, time=query_parsed['DATE'],
                                              cn=query_parsed['NAME'],
                                              condition=query_parsed['BOOLEAN'], )
        if num == 3:
            date = datetime.datetime.now().strftime("%Y-%m-%d") + " " + query_parsed["DATE"]
            with Database() as db:
                db.execute('''INSERT INTO aidebot.history (user_id, national_code, last_taken_pill, taken)
                                       values ({id},{cn},'{date}', {boolean})'''.format(id=user_id,
                                                                                        cn=query_parsed['NAME'],
                                                                                        date=date,
                                                                                        boolean=query_parsed[
                                                                                            'BOOLEAN'],
                                                                                        ))
            return "True"
        return "Postpone"

    def get_history(self, user_id):
        with Database() as db:
            data = db.query(''' SELECT national_code, last_taken_pill, taken
                FROM aidebot.history 
                WHERE user_id={id}
                '''.format(id=user_id))
            return data

    def get_inventory(self, user_id):
        with Database() as db:
            data = db.query(''' SELECT national_code, num_of_pills, expiracy_date
                FROM aidebot.inventory 
                WHERE user_id={id}
                '''.format(id=user_id))
            return data

    def get_cn_from_inventory(self, user_id, cn):
        with Database() as db:
            data = db.query(''' SELECT national_code, num_of_pills, expiracy_date
                FROM aidebot.inventory 
                WHERE user_id={id} and national_code={cn}
                '''.format(id=user_id, cn=cn))
            return data

    def intr_inventory(self, user_id, query_parsed):
        # Quantity es la cantidad que ha de tomarse, no las pastillas que hay
        with Database() as db:
            db.execute('''INSERT INTO aidebot.inventory (user_id,national_code, num_of_pills, expiracy_date)
                        values ({id},{cn},'{quantity}','{exp_date}')'''.format(id=user_id,
                                                                               cn=query_parsed['NAME'],
                                                                               quantity=query_parsed['QUANTITY'],
                                                                               exp_date=query_parsed['EXP_DATE']
                                                                               ))

    def get_reminders(self, user_id, date, to_date=None, cn=None):
        with Database() as db:
            # Journey state: checking reminder for some days
            if to_date:
                date_list = self.get_array_dates(init_date=date, end_date=to_date)
                journey_info = {}

                for day in date_list:
                    data = self.get_calendar(user_id=user_id, date=day.__format__('%Y-%m-%d'))
                    for values in data:
                        national_code = values[0]
                        if national_code not in journey_info:
                            journey_info[national_code] = 0
                        journey_info[national_code] += 1
                return journey_info

            # check if there is actually a reminder of this CN in daily_reminders. If so, get all information of it.
            elif cn:
                if self.check_receipt(cn=cn, user_id=user_id):
                    return self.get_receipts(user_id=user_id, cn=cn)
                else:
                    return '"False"'
            # get calendar tasks for one exact day
            else:
                return self.get_calendar(user_id, date)

    def days_between(self, d1, d2):
        return (abs((d2 - d1).days) + 1)

    def get_array_dates(self, init_date, end_date):
        in_date = datetime.datetime.strptime(init_date, '%Y-%m-%d')
        return [in_date + datetime.timedelta(days=x) for x in range(self.days_between(init_date, end_date))]

    def get_calendar(self, user_id, date):
        with Database() as db:
            data = db.query('''SELECT national_code, time
                                       FROM aidebot.daily_reminders 
                                       WHERE end_date >= '{date}' and user_id={id}
                                       '''.format(date=date, id=user_id))
        return data

    def delete_reminders(self, user_id, national_code):
        with Database() as db:
            # Deleting reminders should delete the entrance of each remind in daily_reminders and receipt, but not from inventory as has all that we have taken always.

            # db.execute('''DELETE FROM aidebot.inventory WHERE user_id={id} and national_code={cn}
            # '''.format(id=user_id, cn=national_code))
            db.execute(
                '''DELETE FROM aidebot.daily_reminders WHERE user_id={id} and national_code={cn}'''.format(id=user_id,
                                                                                                           cn=national_code))
            db.execute('''DELETE FROM aidebot.receipts WHERE user_id={id} and national_code={cn}'''.format(id=user_id,
                                                                                                           cn=national_code))
            return True

    def get_times(self, frequency):
        time = []
        num = 8
        while (num <= 24):
            time.append(str(num) + ':00:00')
            num += int(frequency)
        return time

    def create_reminders(self, user_id, query_parsed):
        for time in self.get_times(query_parsed['FREQUENCY']):
            with Database() as db:
                db.execute('''INSERT INTO aidebot.daily_reminders (user_id, national_code, time, end_date)
                                       values ({id},{cn},'{time}', '{end_date}')'''.format(id=user_id,
                                                                                           cn=query_parsed['NAME'],
                                                                                           end_date=query_parsed[
                                                                                               'END_DATE'],
                                                                                           time=time
                                                                                           ))

    def get_quantity_taken(self, user_id, cn):
        with Database() as db:
            # get the quantity that is taken in each reminder
            data = db.query('''SELECT quantity
                            FROM aidebot.receipts 
                            WHERE national_code >= '{cn}' and user_id={id}
                            '''.format(cn=cn, id=user_id))
            if data[0][0] is not None:
                return data[0][0]
            else:
                return "0"

    def reminder_taken(self, user_id, cn, quantity):
        with Database() as db:
            # there is the possibility of more than one columns of one CN
            data = db.query('''SELECT MIN(expiracy_date)
                            FROM aidebot.inventory 
                            WHERE national_code >= '{cn}' and user_id={id}
                            '''.format(cn=cn, id=user_id))
            if data[0][0] is not None:
                exp_date = datetime.datetime.strftime(data[0][0], "%Y-%m-%d %H:%M:%S")
                # substract quantity to med that expires earlier
                db.execute(
                    '''UPDATE aidebot.inventory SET num_of_pills=num_of_pills-{quantity} where user_id={id} and expiracy_date='{exp_date}' and national_code ={cn}'''.format(
                        cn=cn, id=user_id, exp_date=exp_date, quantity=quantity))

                # check if there is enough pills in inventory for the following three days:
                today = datetime.datetime.now()
                data = db.query('''SELECT end_date
                                FROM aidebot.receipts 
                                WHERE national_code >= '{cn}' and user_id={id}
                                '''.format(cn=cn, id=user_id))
                if data is not ():
                    end_date = data[0][0]
                    pills_needed = min(self.days_between(today, end_date), 3) * int(quantity)
                    data = db.query('''SELECT SUM(num_of_pills)
                                                FROM aidebot.inventory 
                                                WHERE national_code >= '{cn}' and user_id={id}
                                                '''.format(cn=cn, id=user_id))
                    if data is not ():
                        pills_in = int(data[0][0])
                        if pills_in >= pills_needed:
                            return "No reminder"
            return "Remind to buy"


if __name__ == "__main__":
    checker = DBMethods()
