import RPi.GPIO as GPIO
import time

#iç sensör limiti(cm), değeri değişebilir
#iç mesafe ilk limitden büyük olursa, yeşil ışık yanar
#iç mesafe ilk limitden az olursa, sarı ışık yanar
#iç mesafe ikinci limitden de az olursa, kırmızı ışık yanar
inner_limit_1 = 20
inner_limit_2 = 5 

#dış sensör limiti(cm), değeri değişebilir
#dış mesafe limitden az olursa kapar açılır.
outer_limit = 30

#kapının bulunduğu durumlar ve motorun çalışma dereceleri
DOOR_CLOSED_DEGREE = 0
DOOR_OPEN_DEGREE = 90

#kapının açık olup olmadığı tutulur.
IS_DOOR_OPEN = False

# O = Yeşil, 1 = Sarı, 2 = Kırmızı
LED_COLOR = -1


# led pin tanımlamaları
RED_PIN = 11
GREEN_PIN = 13
BLUE_PIN = 15

#iç sensör pin tanımlamaları
INNER_TRIGGER_PIN = 29
INNER_ECHO_PIN = 31

#dış sensör pin tanımlamaları
OUTER_TRIGGER_PIN = 16
OUTER_ECHO_PIN = 18

#servo motor pini tanımlama
SERVO_PIN = 32


def setup():
    #dizilim ve io tanımlamaları
    GPIO.setmode(GPIO.BOARD)
    
    GPIO.setup(RED_PIN, GPIO.OUT)
    GPIO.setup(GREEN_PIN, GPIO.OUT)
    GPIO.setup(BLUE_PIN, GPIO.OUT)
    
    GPIO.setup(INNER_TRIGGER_PIN, GPIO.OUT)
    GPIO.setup(INNER_ECHO_PIN, GPIO.IN)
    
    GPIO.setup(OUTER_TRIGGER_PIN, GPIO.OUT)
    GPIO.setup(OUTER_ECHO_PIN, GPIO.IN)
    
    GPIO.setup(SERVO_PIN, GPIO.OUT)
   
    #servo motor için pwm objesi olşturma
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(0)
   
    return pwm
   
def set_color(red, green, blue):
    """LED rengini ayarlar"""
    GPIO.output(RED_PIN, red)
    GPIO.output(GREEN_PIN, green)
    GPIO.output(BLUE_PIN, blue)    
   

def set_servo_angle(angle, pwm):
    """Servo motorun açısını ayarlar (0-180 derece)"""
    if angle < 0:
        angle = 0
    elif angle > 180:
        angle = 180
    
    #servo motor dönüş açıları
    ORIGIN_ANGLE = 2.5 # 0 derece için duty cycle
    MAX_ANGLE = 12.5 # 180 derece için duty cycle
    
    # Duty cycle hesaplama
    duty_cycle = ORIGIN_ANGLE + (angle / 180.0) * (MAX_ANGLE - ORIGIN_ANGLE)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5) # Servonun hareketi tamamlaması için bekle
    pwm.ChangeDutyCycle(0) # Titreşimi önlemek için PWM'i durdur


def find_distance(TRIGGER_PIN, ECHO_PIN):
    # cm cinsinden hesaplama yapılır
    # hangi trigger ve echonun kullanılacağı belirtilmeli.
    pulse_start = time.time()
    pulse_end = time.time()
    
    # Trig pinini temizle ve 10μs bekle
    GPIO.output(TRIGGER_PIN, False)
    time.sleep(0.06)
    
    # 10μs'lik sinyal gönder
    GPIO.output(TRIGGER_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIGGER_PIN, False)
    
    # Timeout süresi (100ms)
    timeout = time.time() + 0.1
    
    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()
        if pulse_start > timeout:
            return -1  # Timeout durumunda -1 döndür
    
    # Timeout'u resetle
    timeout = time.time() + 0.1
    
    # Echo pininin düşmesini bekle (timeout ile)
    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()
        if pulse_end > timeout:
            return -1  # Timeout durumunda -1 döndür
        
    # Pulse süresini hesapla
    pulse_duration = pulse_end - pulse_start
    
    # Mesafeyi hesapla (ses hızı = 343 m/s = 34300 cm/s)
    # Mesafe = (süre × ses hızı) / 2 (gidiş-dönüş)
    distance = (pulse_duration * 34300) / 2
    
    # Anormal değerleri filtrele (2cm - 400cm arası geçerli)
    if distance < 2 or distance > 400:
        return -1
    
    return distance
    

def run_led():
    #ledi çalıştıran fonksiyon
    #LED_COLOR değerleri O = Yeşil, 1 = Sarı, 2 = Kırmızı
    global LED_COLOR
    
    distance = find_distance(INNER_TRIGGER_PIN, INNER_ECHO_PIN)    
    
    if distance == -1:
        # Hata durumunda tüm LED'leri kapat.
        set_color(False, False, False)
        return
    
    if distance > inner_limit_1 :
        if LED_COLOR != 0 :
            LED_COLOR = 0
            set_color(False, True, False)#yeşil yanar            
    elif distance < inner_limit_2:
        if LED_COLOR != 2 :
            LED_COLOR = 2    
            set_color(True, False, False)#kırmızı yanar
    else : 
        if LED_COLOR != 1 :
            LED_COLOR = 1 
            set_color(True, True, False)#sarı yanar
    
    
def run_servo(pwm):
    #servo motoru çalıştıran fonksiyon
    global IS_DOOR_OPEN
    
    distance = find_distance(OUTER_TRIGGER_PIN, OUTER_ECHO_PIN)
    
    if distance == -1:
        # Hata durumunda kapıyı kapalı konumda tut (güvenli durum)
        if IS_DOOR_OPEN != False:
            IS_DOOR_OPEN = False
            set_servo_angle(DOOR_CLOSED_DEGREE, pwm)
        return
    
    if distance > outer_limit:
        if IS_DOOR_OPEN != False:
            IS_DOOR_OPEN = False
            set_servo_angle(DOOR_CLOSED_DEGREE, pwm)
    else : 
        if IS_DOOR_OPEN != True:
            IS_DOOR_OPEN = True
            set_servo_angle(DOOR_OPEN_DEGREE, pwm)


try:    
    pwm = setup()
    while True:
        run_led()
        run_servo(pwm)
        time.sleep(0.1)  # 100ms bekleme süresi ekle
    
except KeyboardInterrupt:
    print("\nProgram durduruldu")
    
finally:
    set_color(False, False, False)
    pwm.stop()
    GPIO.cleanup()
    print("GPIO temizlendi")