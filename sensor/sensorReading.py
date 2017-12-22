import sensor.sensorGUI as sensorGUI
import sensor.sensorGlobal as sensorGlobal
import RPi.GPIO as GPIO


class RaspberryPiController:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        self.dataHandler = sensorGlobal.DataHandler()
        self.mainWindow = sensorGUI.MainWindow(self)

        for pin in self.dataHandler.get_pins():
            RaspberryPiController.pin_setup(self, pin)

        self.mainWindow.start_gui()

    def pin_triggered(self, pin):
        self.dataHandler.countDict[pin] = (self.dataHandler.countDict[pin] + 1)
        self.mainWindow.count[str(pin)].set(self.dataHandler.countDict[pin])

    @staticmethod
    def pin_setup(caller, pin):
        GPIO.setup(int(pin), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(int(pin), GPIO.RISING, callback=caller.pin_triggered, bouncetime=50)


if __name__ == '__main__':
    RaspberryPiController()
