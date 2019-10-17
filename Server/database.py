import pymysql


class DatabaseConnectionCredentials:

    @property
    def credentials(self):
        return {'ip': 'localhost', 'user': 'paesav', 'password': '12345678', 'database': 'aidebot'}


class Database(DatabaseConnectionCredentials):
    def __init__(self):
        self._conn = pymysql.connect(self.credentials['ip'], self.credentials['user'], self.credentials['password'],
                                     self.credentials['database'])
        self._cursor = self._conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.commit()
        self.connection.close()

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
                print("User isn't registered\n")
                return False
            else:
                print("User registered\n")
                return True

    def add_user(self, new_user, new_password):
        with Database() as db:
            db.execute(
                "INSERT INTO aidebot.users (id, password) VALUES ({id},'{pwd}')".format(id=new_user,
                                                                                        pwd=new_password))
            data = db.query("SELECT id FROM aidebot.users where id={id}".format(id=new_user))

            if not data:
                print("User not added\n")
                return False
            else:
                print('User added\n')
                return True

    def check_password(self, user_id, password):

        with Database() as db:
            data = db.query("SELECT password FROM aidebot.users where id={id}".format(id=user_id))
            print(data)
            if password != data[0][0]:
                print('Wrong password')
                return False
            else:
                print('Correct password')
                return True

    def introd_receipt(self, query_parsed, user_id, date):
        with Database() as db:
            db.execute('''INSERT INTO aidebot.receipts (user_id,national_code, frequency, quantity, begin_date, end_date)
                        values ({id},{cn},{frequency},'{quantity}','{init}','{end}')'''.format(
                id=user_id, cn=query_parsed['NAME'], frequency=query_parsed['FREQUENCY'],
                quantity=query_parsed['QUANTITY'],
                init=date,
                end=query_parsed['END_DATE']
            ))
            self.intr_inventory(user_id=user_id, query_parsed=query_parsed)
            self.create_reminders(user_id=user_id, query_parsed=query_parsed)
            # Comprobar que se ha introducido bien

    def check_receipt(self, cn, user_id):
        with Database() as db:
            data = db.query('''SELECT count(*) FROM aidebot.receipts WHERE user_id={id} and national_code={med}
            '''.format(id=user_id, med=cn))
            if data[0][0] == 0:
                return False
            else:
                return True

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

    ''' 
    TODO
    '''

    def intr_inventory(self, user_id, query_parsed):
        with Database() as db:
            db.execute('''INSERT INTO aidebot.inventory (user_id,national_code, num_of_pills, expiracy_date)
                        values ({id},{cn},'{quantity}','{exp_date}')'''.format(id=user_id,
                                                                               cn=query_parsed['NAME'],
                                                                               quantity=query_parsed['QUANTITY'],
                                                                               exp_date=query_parsed['EXP_DATE']
                                                                               ))

    def get_receipts(self, user_id, cn):
        with Database() as db:
            data = db.query(''' SELECT national_code, frequency,end_date
             FROM aidebot.receipts 
             WHERE user_id={id} and national_code={cn}
            '''.format(cn=cn, id=user_id
                       ))
            return data

    def create_reminders(self, user_id, query_parsed):
        with Database() as db:
            db.execute('''INSERT INTO aidebot.daily_reminders (user_id, national_code, frequency)
                                    values ({id},{cn},'{frequency}')'''.format(id=user_id,
                                                                               cn=query_parsed['NAME'],
                                                                               frequency=query_parsed[
                                                                                   'FREQUENCY'],
                                                                               ))

    def get_reminders(self, user_id, date, to_date=None, cn=None):
        with Database() as db:
            if to_date:
                data = db.query(''' SELECT national_code, date
                FROM aidebot.receipts
                WHERE begin_date>='{date}' and end_date<='{to_date}' and user_id={id}
                '''.format(date=date, to_date=to_date, id=user_id))
                return data
            elif cn:
                if(self.check_receipt(self, cn=cn, user_id=user_id)):
                    return self.get_receipts(cn, user_id)
                else:
                    return "False"

            else:
                data = db.query('''SELECT national_code, frequency
                FROM aidebot.daily_reminders 
                WHERE frequency ='{date}' and user_id={id}
                '''.format(date=date, id=user_id))
                return data

    def delete_reminders(self, user_id, national_code):
        with Database() as db:
            db.execute('''DELETE FROM aidebot.inventory WHERE user_id={id} and national_code={cn}
            '''.format(id=user_id, cn=national_code))
            db.execute('''DELETE FROM aidebot.daily_reminders WHERE user_id={id} and national_code={cn}
            '''.format(id=user_id, cn=national_code))
            db.execute('''DELETE FROM aidebot.receipts WHERE user_id={id} and national_code={cn}
                        '''.format(id=user_id, cn=national_code))
            # Comprobar si se ha hecho bien
            return True

    def get_history(self, user_id):
        with Database() as db:
            data = db.query(''' SELECT national_code, end_date
                FROM aidebot.receipts 
                WHERE user_id={id}
                '''.format(id=user_id))
            return data

    def daily_table(self, user_id, national_code):
        return False

    '''
    Reminders batch job methods!
    '''

    def get_all_receipts(self):
        with Database() as db:
            data = db.query('''SELECT *
            FROM aidebot.receipts
            ''')
            return data

    def insert_reminders(self, user_id, cn, date):
        with Database() as db:
            data = db.query('''SELECT *
            FROM aidebot.daily_reminders
            WHERE user_id={id} and national_code = {cn} and cast(frequency as frequency) = '{date}'
            '''.format(id=user_id, cn=cn, date=date))
            if data:
                db.execute('''INSERT INTO aidebot.daily_reminders (user_id, national_code, frequency)
                values ({id},{national_code},'{date}')            
                '''.format(id=user_id, national_code=cn, date=date))

    def suprimir_reminders(self, date):
        with Database() as db:
            db.execute('''DELETE FROM aidebot.daily_reminders WHERE frequency<'{date}'
            '''.format(date=date))
            # Comprobar si se ha hecho bien
            return True


if __name__ == "__main__":
    checker = DBMethods()

''' Users test
 exists = checker.check_user(user_id=1)
    if exists:
        checker.check_password(user_id=1, password='hola')
        checker.check_password(user_id=1, password='prueba')
    else:
        print("Va como el culo, no detecta el unico id :(")
    exists_2 = checker.check_user(user_id=2)
    if exists_2:
        print("Maaaaal, no existe :(((")
    else:
        checker.add_user(new_user=2, new_password='prueba_checker_method')
'''
