import datetime
import time

import schedule

from server.database import Database


# THIS CLASS IS THE ONE THAT HAS THE TASK OF ACTUALIZING THE DAILY TABLE EVERY DAY WITH THE REMINDERS!
class Reminder:
    def __init__(self, arg):
        self.client = arg

    def daily_actualizations(self):
        # Every day at 01:00 the system will proceed to check if any reminder needs to be removed as expired
        schedule.every().day.at("01:00").do(self.checking_expirations)
        schedule.every().day.at("02:00").do(self.delete_history)
        schedule.every(15).minutes.do(self.remind_information)
        while True:
            schedule.run_pending()
            # Sleeps for half an hour
            time.sleep(30)

    # Delete all reminders which has expired by end_date < today
    def test(self):
        data = [["798116", "2019-10-28 08:00:00", 821061948], ["664029", "2019-10-28 10:00:00", 821061948],
                ["798116", "2019-10-28 10:00:00", 821061948]]
        self.client.send_reminders(data)

    def checking_expirations(self):
        with Database() as db:
            today = str(datetime.date.today())
            db.execute('''DELETE FROM aidebot.daily_reminders WHERE (end_date<'{today}')'''.format(today=today))
            db.execute('''DELETE FROM aidebot.receipts WHERE (end_date<'{today}')'''.format(today=today))

    # Check for reminders of the last hour
    def remind_information(self):
        with Database() as db:
            now = datetime.datetime.now()
            before_now = now - datetime.timedelta(minutes=30)
            now = now.strftime('%H:%M:%S')
            before_now = before_now.strftime('%H:%M:%S')

            data = db.query('''SELECT national_code, time, user_id FROM aidebot.daily_reminders WHERE taken!=3 and time<='{now}' '''.format(now=now))

            #  data = db.query('''SELECT national_code, time, user_id
            #                            FROM aidebot.daily_reminders
            #                            WHERE time >= '{before_now}' and time<='{now}' and taken=0
            #                            '''.format(before_now=before_now, now=now))

            self.client.send_reminders(data)

    # Delete information older than 3 days from history table
    def delete_history(self):
        with Database() as db:
            db.execute('''DELETE FROM aidebot.history WHERE (end_date<'{date}')'''.format(
                date=datetime.datetime.utcnow() - datetime.timedelta(days=3)))


if __name__ == "__main__":
    reminder = Reminder()
    reminder.daily_actualizations()
