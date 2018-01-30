import json
import zmq
import logging
import sqlite3
from collections import OrderedDict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


class ServerSettings:
    MACHINE_PORTS = 'machine_ports'
    QUICK_ACCESS = 'quick_access'
    MISC_SETTINGS = 'misc_settings'

    def __init__(self, filename='server_settings.json'):
        self.filename = filename
        self.logger = logging.getLogger('afRPIsens_server')
        self.machine_ports = OrderedDict()
        self.quick_access = OrderedDict()
        self.misc_settings = {}
        self.load_settings()
        self.logger.debug('Completed setup')

    def save_settings(self):
        self.logger.debug('Saving settings')
        settings_dict = {ServerSettings.MACHINE_PORTS: self.machine_ports,
                         ServerSettings.QUICK_ACCESS: self.quick_access,
                         ServerSettings.MISC_SETTINGS: self.misc_settings}
        with open(self.filename, 'w') as outfile:
            json.dump(settings_dict, outfile)
        self.logger.debug('Saved settings')

    def load_settings(self):
        self.logger.debug('Loading settings')
        try:
            with open(self.filename, 'r') as infile:
                settings_dict = json.load(infile, object_pairs_hook=OrderedDict)
                self.machine_ports = settings_dict[ServerSettings.MACHINE_PORTS]
                self.quick_access = settings_dict[ServerSettings.QUICK_ACCESS]
                self.misc_settings = settings_dict[ServerSettings.MISC_SETTINGS]
        except FileNotFoundError:
            pass
        self.logger.debug('Loaded settings')


class Communication:
    REQUEST_ID = 'request'

    def __init__(self, server_settings: ServerSettings):
        self.logger = logging.getLogger('afRPIsens_server')
        self.server_settings = server_settings
        self.scheduler = BackgroundScheduler()
        self.ports = []
        self.context = None
        self.socket = None

    def req_client(self):

        self.ports = list(self.server_settings.machine_ports.values())

        self.context = zmq.Context()
        self.logger.debug("Connecting to the ports")
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.LINGER, 0)
        for port in self.ports:
            self.socket.connect("tcp://{}".format(port))
            self.logger.debug("Successfully connected to machine %s" % port)

        for request in range(len(self.ports)):
            print("Sending request ", request, "...")
            self.socket.send_string("", zmq.SNDMORE)  # delimiter
            self.socket.send_string("Sensor Data")  # actual message

            # use poll for timeouts:
            poller = zmq.Poller()
            poller.register(self.socket, zmq.POLLIN)

            socks = dict(poller.poll(5 * 1000))

            if self.socket in socks:
                try:
                    self.socket.recv()  # discard delimiter
                    msg_json = self.socket.recv()  # actual message
                    sens = json.loads(msg_json)
                    # TODO edit here
                    for timestamp, values in sens.items():
                        for uniqID, count in values.items():
                            response = "Time: %s :: Data: %s :: Client: %s :: Sensor: %s" % (uniqID, count, port, timestamp)
                            print("Received reply ", request, "[", response, "]")
                except IOError:
                    print("Could not connect to machine")
            else:
                # TODO machine not respond
                print("Machine did not respond")

    def set_jobs(self):
        self.scheduler.remove_all_jobs()
        cron_trigger = CronTrigger(hour='*', minute='*/1')  # TODO set here
        self.scheduler.add_job(self.req_client, cron_trigger, id=Communication.REQUEST_ID)


class DatabaseManager:
    def __init__(self, database_name='afRPIsens.sqlite'):
        self.database_name = database_name
        pass

    def create_table(self, table_name, database=None):
        if database is None:
            database = self.database_name
        db = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            db.execute("DROP TABLE IF EXISTS {}".format(table_name))
            db.execute("CREATE TABLE IF NOT EXISTS {} (time TIMESTAMP PRIMARY KEY NOT NULL, quantity INTEGER NOT NULL)"
                       .format(table_name))
        except Exception as e:
            db.rollback()
        finally:
            db.close()

    def insert_into_table(self, table_name, timestamp, quantity, database=None):
        if database is None:  # Check for database name
            database = self.database_name
        # Establish connection and create table if not exists
        db = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES)
        db.execute("CREATE TABLE IF NOT EXISTS {} (time TIMESTAMP PRIMARY KEY NOT NULL, quantity INTEGER NOT NULL)"
                   .format(table_name))
        # Check if exist same timestamp for machine
        cursor = db.cursor()
        cursor.execute("SELECT * from {} WHERE time=datetime(?)", (timestamp,))
        query = cursor.fetchone()
        if query:  # TODO to test
            _timestamp, count = query
            quantity = quantity + count
            cursor.execute("UPDATE {} SET quantity = ? WHERE time = ?", (quantity, timestamp))
        else:
            cursor.execute("INSERT INTO {} VALUES(datetime(?), ?".format(table_name), (timestamp, quantity))
