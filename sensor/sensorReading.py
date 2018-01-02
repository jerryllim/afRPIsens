import sensor.sensorGUI as sensorGUI
import sensor.sensorGlobal as sensorGlobal
import pigpio


class RaspberryPiController:
    def __init__(self, root):
        self.pinDataHandler = sensorGlobal.PinDataManager()
        self.networkDataManager = sensorGlobal.NetworkDataManager(self.pinDataHandler)
        self.mainWindow = sensorGUI.MainGUI(root, self)
        self.pi = pigpio.pi()
        self.callbacks = []

        for pin, bounce in self.pinDataHandler.get_pin_and_bounce_list():
            RaspberryPiController.pin_setup(self, pin, bounce)

        self.mainWindow.start_gui()

    def pin_triggered(self, pin, level, tick):
        _id = self.pinDataHandler.get_id_from_pin(pin)
        self.pinDataHandler.countDict.update([_id])
        self.mainWindow.count[_id].set(self.pinDataHandler.countDict[_id])

    def remove_detections(self):
        for callback in self.callbacks:
            callback.cancel()

    def reset_pins(self):
        self.remove_detections()
        for pin, bounce in self.pinDataHandler.get_pin_and_bounce_list():
            RaspberryPiController.pin_setup(self, pin, bounce)

    def pin_setup(self, pin, bounce=300):
        self.pi.set_mode(pin, pigpio.INPUT)
        self.pi.set_pull_up_down(pin, pigpio.PUD_DOWN)
        self.pi.set_glitch_filter(pin, (bounce * 1000))
        self.callbacks.append(self.pi.callback(pin, pigpio.RISING_EDGE, self.pin_triggered))
