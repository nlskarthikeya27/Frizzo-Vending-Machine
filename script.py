from flask import Flask, request
from flask_cors import CORS
import stripe
import RPi.GPIO as GPIO
from time import sleep
import threading
import board
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
pump = 26
valve = 27
ir = 16

GPIO.setup(valve, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(pump, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(ir, GPIO.IN)

cooling = True
dispensing = False
glass_present = False

columns = 16
rows = 2

rs = digitalio.DigitalInOut(board.D22)
en = digitalio.DigitalInOut(board.D17)
d4 = digitalio.DigitalInOut(board.D25)
d5 = digitalio.DigitalInOut(board.D24)
d6 = digitalio.DigitalInOut(board.D23)
d7 = digitalio.DigitalInOut(board.D18)

lcd = characterlcd.Character_LCD_Mono(rs, en, d4, d5, d6, d7, columns, rows)
lcd_lock = threading.Lock()
lcd.clear()

def coolingProcess():
    global cooling
    global dispensing

    while True:
        if cooling and not dispensing:
          with lcd_lock:
            GPIO.output(pump,1)
            lcd.message = " Frizzo Vending \n    Machine"
            print("Cooling: pump ON")
            sleep(5)
            lcd.clear()
            sleep(0.5)
          with lcd_lock:
            GPIO.output(pump,0)
            lcd.message = "  Scan The QR : \n     To Pay     "
            print("Cooling: pump OFF")
            sleep(25)
          with lcd_lock:
            lcd.clear()
            sleep(0.5)

def startCooling():
    global cooling
    cooling = True

def stopCooling():
    global cooling
    cooling = False

def isGlassPresent():
    global glass_present
    if(GPIO.input(ir) == 0):
        glass_present = True
    elif(GPIO.input(ir) == 1):
        glass_present = False

def startDispensing(duration, type):
  global dispensing
  global glass_present
  dispensing = True
  while(glass_present == False):
    with lcd_lock:
      lcd.clear()
      sleep(0.25)
      lcd.message = "Put Glass below!"
    sleep(1.5)
    isGlassPresent()

  with lcd_lock:
    lcd.clear()
    sleep(0.5)
  #with lcd_lock:
    msg = "  Dispensing...\n  Type: "+type
    lcd.message = msg
    print("Dispensing: pump ON")
    GPIO.output(pump,1)
    GPIO.output(valve,1)
    sleep(duration)
    GPIO.output(pump,0)
    GPIO.output(valve,0)
    print("Dispensing Stopped: pump OFF")
  #with lcd_lock:
    lcd.clear()
    sleep(0.25)
  dispensing = False
  glass_present = False
  startCooling()

stripe.api_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

endpoint_secret = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

app = Flask(name)
CORS(app)

@app.route('/')
def FrizzoHome():
    return 'Frizzo Vending Machine Home Page ??'

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe_Signature', None)

    if not sig_header:
        return 'No Signature Header!', 400

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
      session = stripe.checkout.Session.retrieve(
      event['data']['object']['id'],
      expand=['line_items'],
      )
      stopCooling()
      with lcd_lock:
        lcd.clear()
        sleep(0.5)
        lcd.message = "   Transaction\n   Successful..."
      sleep(1)
      line_items = session.line_items
      # print(line_items)
      if(line_items.data[0].description == "Rasna Large"):
          print("Rasna Large : Payment Successful ??")
          #dispense("Large")
          threading.Thread(target=startDispensing, args=(30,"Large")).start()
      elif(line_items.data[0].description == "Rasna Medium"):
          print("Rasna Medium : Payment Successful ??")
          #dispense("Medium")
          threading.Thread(target=startDispensing, args=(20,"Medium")).start()
    else:
        return 'Unexpected event type', 400

    return '', 200

#def main():
#    try:
#        app.debug = True
#        app.run(debug=True)
#    finally:
#        lcd.clear()
#        sleep(0.3)
#        lcd.message = " Shutting Down "
#        sleep(2)
#        lcd.clear()
#        GPIO.cleanup()


if name == 'main':

	threading.Thread(target=coolingProcess).start()
	try:
            #app.debug = True
            app.run()
	finally:
            lcd.clear()
            sleep(0.2)
            lcd.message = "Shutting Down..."
            sleep(2)
            lcd.clear()
            GPIO.cleanup()
