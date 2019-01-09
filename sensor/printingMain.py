import json
import pigpio
import datetime
import threading
from collections import Counter
import sensor.printingkivy


class RaspberryPiController:
    bounce = 30
    sensor_dict = {}
    pin_to_name = {}
    counts = {}
    _output = 0
    states = {}

    def __init__(self, filename='pin_dict.json'):
        self.filename = filename
        self.load_pin_dict()
        self.pi = pigpio.pi()
        self.callbacks = []
        self.counts_lock = threading.Lock()

        # TODO add check to check if pin is output pin
        for name, pin in self.sensor_dict.items():
            self.pin_setup(pin, False)

        self.gui = sensor.printingkivy.PrintingGUIApp(self)
        # self.gui.run()  # TODO uncomment

    def load_pin_dict(self):
        try:
            with open(self.filename, 'r') as infile:
                self.sensor_dict = json.load(infile)
                self.pin_to_name = self.lookup_pin_name()
        except FileNotFoundError:
            # TODO either log or stop program since not recording pins
            pass

    def lookup_pin_name(self):
        temp = {}
        for name, pin in self.sensor_dict.items():
            temp[pin] = name

        return temp

    def get_key(self, interval=5, emp=None):
        # TODO change to UTC now?
        now = datetime.datetime.now()
        # Floor to nearest interval (default = 5)
        now = now - datetime.timedelta(minutes=now.minute % interval)

        if not emp:
            emp = self.gui.action_bar.employees[1]

        if self.gui.current_job:
            jo_no = self.gui.current_job.get_current_job()
        else:
            jo_no = 'None'

        return '{0}_{1}_{2}'.format(emp, jo_no, now.strftime('%Y%m%d%H%M'))

    def pin_triggered(self, pin, _level, _tick):
        name = self.pin_to_name[pin]
        key = self.get_key()
        self.update_count(name, key)

    def output_pin_triggered(self, pin, _level, _tick):
        self.pin_triggered(pin, _level, _tick)

        # TODO store output here? and to FeRAM?
        self._output += 1
        self.gui.update_output()

    def pin_setup(self, pin, is_output, bounce=30):
        self.pi.set_mode(pin, pigpio.INPUT)
        self.pi.set_pull_up_down(pin, pigpio.PUD_DOWN)
        self.pi.set_glitch_filter(pin, (bounce * 1000))
        if is_output:
            self.callbacks.append(self.pi.callback(pin, pigpio.RISING_EDGE, self.output_pin_triggered))
        else:
            self.callbacks.append(self.pi.callback(pin, pigpio.RISING_EDGE, self.pin_triggered))

    def update_count(self, name, datetime_stamp):
        with self.counts_lock:
            if self.counts.get(name) is None:
                self.counts[name] = Counter()
            self.counts[name].update(datetime_stamp)

    def get_counts(self):
        with self.counts_lock:
            temp = self.counts.copy()
            self.counts.clear()

        return json.dumps(temp)

    def pin_triggered2(self, pin, level, _tick):
        name = self.pin_to_name[pin]
        self.states[name] = level

        key = 0

        if level and not self.counts[name][key]:
            pass
