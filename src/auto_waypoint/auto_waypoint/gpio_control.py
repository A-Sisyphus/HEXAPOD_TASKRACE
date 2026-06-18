import Jetson.GPIO as GPIO
import time
import os

os.system('sudo busybox devmem 0x2434088 w 0x1006')
os.system('sudo busybox devmem 0x243D020 w 0x5')

pump_pin = 18  #气泵控制引脚  BCM 18 对应物理引脚12
valve_pin = 23  #阀门控制引脚  BCM 23 对应物理引脚16

GPIO.setmode(GPIO.BCM)
GPIO.setup(pump_pin, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(valve_pin, GPIO.OUT, initial=GPIO.LOW)

def pick_up():
    GPIO.output(pump_pin, GPIO.HIGH)
    GPIO.output(valve_pin, GPIO.LOW)

def put_down():
    GPIO.output(pump_pin, GPIO.LOW)
    GPIO.output(valve_pin, GPIO.HIGH) 

if __name__ == "__main__":
    try:
        pick_up()
        time.sleep(5) 
        put_down()
        time.sleep(5)

    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()

