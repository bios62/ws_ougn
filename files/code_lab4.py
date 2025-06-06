#
#  Code for Autonomous Workshop
#
# (c) 2025, Frode Pedersen Oracle, Inge Os Oracle
#
# Under Gnu GPL
#
import gc
import wifi  # should be first to reduce of memory issues
import time
import alarm
import time
import board
import neopixel
import ssl
import socketpool
import adafruit_requests
import adafruit_ahtx0
import supervisor
import microcontroller
import json
import os

#########################################################
#
#
# Globals 
#
config={}
#
#  Constants
#
REST_URI = "rest_uri"
ORDS_USER = 'ords_user'
ORDS_PASSWORD="ords_password"
SENSOR_API='sensor_API'
SPEED_API='speed_API'
DEBUG_LEVEL='debug_level'
MEMORY_THRESHOLD = 'memory_treshold'
MAX_ITERATIONS_BEFORE_RESTART = 'iterations'
POST_SLEEP_TIME = 'post_sleep_time'
NET_WIFI_SSID_BASE='netXXX_wifi_ssid'
NET_WIFI_PASSWORD_BASE='netXXX_wifi_password'
#
# Default values
#
config[REST_URI] = 'https://myadburl.adb.eu-frankfurt-1.oraclecloudapps.com'
config[ORDS_USER] = 'myordsuser'
config[SENSOR_API]='/sensorapi/'
config[SPEED_API]='/wsapi/V1/kmh'
config[DEBUG_LEVEL] = 1  #  Set to 1 to dump mem stats for each gc call
config[MEMORY_THRESHOLD] = 2006000
config[MAX_ITERATIONS_BEFORE_RESTART] = 1000
config[POST_SLEEP_TIME] = 5

pixel = None
VERSION = "060924 V2.0"

#########################################################
# Configuration
# Add your network and correct URL for the REST API
#########################################################

wifi_networks = {}


#########################################################
#
# cleanup_memory
#
# Calls garbage collector,
# if debug flag is set, prints
# memfree before and anter GC call
#
#########################################################
def cleanup_memory(text=None):
    global config

    if config[DEBUG_LEVEL] > 0:
        if not text is None:
            print("Memfree label: " + text, end=" ")
        pregc_freemem = gc.mem_free()
    gc.collect()
    postgc_freemem = gc.mem_free()
    if config[DEBUG_LEVEL] > 0:
        print(
            "Pre gc mem: " + str(pregc_freemem) + " post gc mem: " + str(postgc_freemem)
        )
    return postgc_freemem

#########################################################
#
# get_config
#
# Read config from settings.toml
#
# Throws exception if config is missing
# and turns on  AZURE Blink
#
# Globals:
#   pixel,  LED driver
#   config, DICT with current config
#   debug_level
#
#########################################################
def get_config():

    global pixel
    global config
    global wifi_networks
    #
    #  Read Wifi setting for mandatory WiFi 
    #
    wifi_networks={}
    #
    # Get network config , iterate and generate names. max 9 names
    #
    for i in range (1,9):
        wifi_ssid_label=NET_WIFI_SSID_BASE.replace('XXX',str(i))
        wifi_password_label=NET_WIFI_PASSWORD_BASE.replace('XXX',str(i))
        wifi_ssid = os.getenv(wifi_ssid_label)
        wifi_password = os.getenv(wifi_password_label)
        if wifi_ssid is None or wifi_password is None:
            break
        network_label='Net-'+str(i)
        wifi_networks[network_label]={"wifinamename": wifi_ssid, "ssid":wifi_password }
    if wifi_networks == {} :
        print("Wifi SSID and Password not found in settings.toml")
        raise ValueError
    for key in config:
            config_parameter= os.getenv(key)
            if config_parameter is not None:
                if isinstance(config[key],bool):  # Bools is subclass of int, needs to go first
                    if config_parameter.upper() == 'TRUE':
                        config[key]=True
                    elif config_parameter.upper() == 'FALSE':
                        config[key]=False
                    else:
                        print("Illegal configuration value "+key+" permit TRUE, FALSE only")
                        raise ValueError
                elif isinstance(config[key],int):
                    try:
                        config[key]=int(config_parameter)
                    except:
                        print("Illegal configuration value "+key+" Should be int, integer conversion failed")
                        raise ValueError
                else:  # Always assume string)
                    config[key]=config_parameter



#########################################################
#
# get_current_speed
#
# Calls ORDS rest API hosted at Autonomous
# Using HTTPS GET, fetch  last record in current_speed table
#
#
#########################################################
def get_current_speed():

    global pixel
    global config

    apiURL=config[REST_URI].rstrip('/')+'/ords/'+config[ORDS_USER]+config[SPEED_API]
    print("\nHTTP GET current_speed from Autonomous, URL: " + apiURL)
    #
    # Clean memory before allocating socket resources
    #
    cleanup_memory()
    try:
        pool = socketpool.SocketPool(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl.create_default_context())

    except:
        print("\nrequests error - exception - 101")
        return -1
    #
    # Execute GET if request was successfully allocated
    print ("Ready2get")
    #
    # Two types of error may occur, either a exception is thrown (network error)
    # or HTTP Error (HTTP-400 - HTTP-500)
    #
    current_speed=0
    headers = {"Content-Type": "application/json"}
    print("-" * 40)
    response = requests.get(apiURL, headers=headers)
    if response.status_code <=201:
        print('Current speed:'+response.text)
        current_speed=json.loads(response.text)['items'][0]['kmh']

    else:
        print('GET Failed status code:'+str(response.status_code))
    try:
        # application/json
        current_speed=0
        headers = {"Content-Type": "application/json"}
        print("-" * 40)
        response = requests.get(apiURL, headers=headers)
        if response.status_code <=201:
            print('Current speed:'+response.text)
            current_speed=json.loads(response.text)['items'][0]['kmh']

        else:
            print('GET Failed status code:'+str(response.status_code))
    except Exception as e:
        print("\n HTTPS GET Exception")
        print(e)
        return -1
    print ("return from get_current_speed")
    return current_speed

#########################################################
#
# post_to_rest
#
# Calls ORDS rest API hosted at Autonomous
# Using HTTPS POST, postin JSON payload
# The circiut python API has limited header support,
# Header Content-Type is not set
# The POST will not work if Content-Type application/JSON is required
#
# temperature value is in millicelcius from the device
#
#########################################################
def post_to_rest(millicelsius,hum,kmh):

    global pixel
    global config

    #
    # Create JSON payload
    #
    apiURL=config[REST_URI].rstrip('/')+'/ords/'+config[ORDS_USER]+config[SENSOR_API]
    #
    #  Format {"temp":"actual temp"}
    #  Convert millicelcius to celcius
    #
    # millicelsius=1000
    #payload = '{"objecttag":' + "{:.2f}".format(millicelsius / 1000) + "}"
    payload = '{ "objecttag" :  "ESP32:Feather:031" , "sensors" : [ { "sensortag" : "mC", "sensorvalue" : "' + str(millicelsius) + '" }, { "sensortag" : "Humidity", "sensorvalue" : "' + str(hum) + '"}, { "sensortag" : "KMH", "sensorvalue" : "' + str(kmh) + '"} ] }'

    print("\nHTTP POST to Autonomous, payload " + payload)
    #
    # Clean memory before allocating socket resources
    #
    cleanup_memory()
    try:
        pool = socketpool.SocketPool(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl.create_default_context())

    except:
        print("\nrequests error - exception - 101")
        return -1
    #
    # Execute POST if request was successfully allocated
    print ("Ready2post")
    #
    # Two types of error may occur, eiter a exception is thrown (network error)
    # or HTTP Error (HTTP-400 - HTTP-500)
    #
    print('Posting to: '+ apiURL)
    print (payload)
    try:
        # application/json
        headers = {"Content-Type": "application/json"}
        print("-" * 40)
        response = requests.post(apiURL, headers=headers, data=payload)
        if response.status_code <=201:
            print('Posted sucsessfully')
    except Exception as e:
        print("\n HTTPS POST Exception")
        print('POST Failed status code:'+str(response.status_code))
        print(e)
        return -1
    print ("return from post")
    return response.status_code


#########################################################
#
# connect_to_wifi
#
# Loops throug dictionary with list of possible
# Wifis and try them, If noone connects, returns False
#
#########################################################
def connect_to_wifi():

    global pixel
    global wifi_found

    wifi_found = False
    for wifi_net in wifi_networks:
        print(
            f"\n Trying to connect to Wi Fi network  {wifi_networks[wifi_net]['wifinamename']} {wifi_networks[wifi_net]['ssid']}"
        )
        try:
            wifi.radio.connect(
                wifi_networks[wifi_net]["wifinamename"], wifi_networks[wifi_net]["ssid"]
            )
            print(f"\n Successfully connected to : {wifi_net}")
            print(f" Allocated IP address: {wifi.radio.ipv4_address}")
            pixel.fill((255, 0, 255))
            time.sleep(2.0)
            wifi_found = True
            break
        except Exception as e:
            print("\n Connect to network - failed")
            print(" Wifi Connect error:", end="\n ")
            print(e)
            cleanup_memory()
    if not wifi_found:
        print(" No able to connect to any Wifi\n Available WiFi networks:")
        printWifi()

    return wifi_found


#########################################################
#
# printWifi
#
# Prints visible SSIDs
#
#########################################################
def printWifi():
    for network in wifi.radio.start_scanning_networks():
        print(
            "\t%s\t\tRSSI: %d\tChannel: %d"
            % (str(network.ssid, "utf-8"), network.rssi, network.channel)
        )
    wifi.radio.stop_scanning_networks()


#########################################################
#
# main
#
# Main procedure
# Endles loop, but runs until MAX_ITERATIONS_BEFORE_RESTART
# is reached. Reboot device when this threshold is met
#########################################################
def main():

    global pixel
    global config

    print(f"\nStart: Program version {VERSION} Microcontroller Device: ", end=" ")
    hostname = "QTPY" + str(int.from_bytes(microcontroller.cpu.uid, "little") >> 29)
    print(f"{hostname}")
    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
    cleanup_memory()
    print("\nStart - white->green")
    for x in range(255):
        pixel.fill((255 - x, 255, 255 - x))
        time.sleep(0.025)
    restartCnt = 0
    time.sleep(5.0)
    #
    # Collect and prtint board MAC address, if set
    #
    MACaddress = [hex(i) for i in wifi.radio.mac_address]
    print(f"Device MAC address: {MACaddress}")
    #
    #  get configuration
    #
    get_config()
    #
    #  Connect to wifi, reload if it fails
    #
    print(f"Connecting to WiFi")
    connectWiFi = connect_to_wifi()
    pixel.fill((255, 255, 0))
    time.sleep(2.0)
    if not connectWiFi:
        #
        # No Wifi Connection
        #
        print("Connect to Wifi Network failed, review WiFi configuration")
        # The device will be relaoded
        # Show available WiFi network
        #
        printWifi()
        #
        # Switch led and reload
        #
        print("\nNo Wifi Connection - no IP - Blue - Sleep 10 sec and reboot")
        cleanup_memory()
        pixel.fill((0, 0, 255))
        time.sleep(10)
        print("\nEnter deep Sleep for 10 sec")
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 10)
        alarm.exit_and_deep_sleep_until_alarms(time_alarm)
        print("\nDeep Sleep complete, reload")
        supervisor.reload()
    #
    # Loop until reload
    #
    while True:
        current_memory = cleanup_memory()

        #
        # If Current memory is below memor Threashold, continue
        # Otherwise reboot
        #
        if current_memory < config[MEMORY_THRESHOLD]:
            print(f"\nMemory restart -Green->Red")
            for x in range(255):
                pixel.fill((x, 255 - x, 0))
                time.sleep(0.025)
            #
            # Restart device
            #
            supervisor.reload()
        #
        #  If max number of iterations is reached, reboot
        #
        restartCnt = restartCnt + 1
        print(f"restartCnt: {restartCnt} ")
        if restartCnt > config[MAX_ITERATIONS_BEFORE_RESTART]:
            print("Max iterations reached, restart - restartCnt - white 20 sec")
            cleanup_memory()
            pixel.fill((255, 255, 255))
            time.sleep(20.0)
            supervisor.reload()
        #
        # No reboot continue
        #
        print("\nLoop Start - white 2 sec")
        pixel.fill((255, 255, 255))
        time.sleep(2.0)
        pixel.fill((0, 255, 255))
        time.sleep(2.0)
        #
        # Connect to Wifi
        #

        #
        #  If there is no WiFi just report tem locally to serial monitor
        #
        kmh=3.14
        hum=0
        try:
            i2c = board.STEMMA_I2C()
            aht20 = adafruit_ahtx0.AHTx0(i2c)
            # data = [aht20.temperature, aht20.relative_humidity]
            print("\nTemperature: %0.1f " % aht20.temperature, end=" ")
            print("Humidity: %0.1f %%\n" % aht20.relative_humidity)
            # print(data)
            mc = int(aht20.temperature * 1000)
            # print("\nTemperature mc: %0.1f C" % mc)
            hum = int(aht20.relative_humidity)

        except:
            mc = 31300  # Default value
            print("\nNo sensor - default temperature:%0.1f C" % mc)
            print("Yellow/Red - Blink")
            pixel.fill((255, 255, 0))
            time.sleep(1.5)
            pixel.fill((255, 0, 0))
            time.sleep(1.5)
            pixel.fill((255, 255, 0))
            time.sleep(1.5)
            pixel.fill((255, 0, 0))
            time.sleep(1.5)
        pixel.fill((255, 255, 0))
        print("Yellow")
        time.sleep(1.5)

        #
        # Post result over REST to Autonmous
        #
        cleanup_memory("\nBefore Post To REST")
        kmh=get_current_speed()
        post_status = post_to_rest(mc,hum,kmh)

        cleanup_memory("\nAfter Post to REST")
        print("-" * 40)
        print("Post status code: " + str(post_status))
        print("-" * 40)

        #
        #  Prosess POST status
        #
        if post_status == -1:  #  Generates relaod
            #
            #  Post generated Exception
            #
            print("\nPost Autonomous - Exception - Red")
            cleanup_memory()
            pixel.fill((255, 0, 0))
            time.sleep(30)
            print("\n Enter Deep Sleep")
            time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 5)
            alarm.exit_and_deep_sleep_until_alarms(time_alarm)
            print("\n Deep Sleep complete")
            supervisor.reload()
        if post_status == 201 or post_status == 200:
            #
            # Post Successfull
            #
            print(f"\nPost Autonomus - OK - Green {config[POST_SLEEP_TIME]} sec")
            cleanup_memory()
            pixel.fill((0, 255, 0))
            #
            #  Wait for next iteration
            #
            time.sleep(config[POST_SLEEP_TIME])
        else:
            #
            #  REST HTTP_STATUS != 200 or 201
            #
            print("\nPost Autonomus - ERROR - Orange 30 sec")

            cleanup_memory()
            pixel.fill((255, 64, 0))
            time.sleep(config[POST_SLEEP_TIME])
            print("\nPost Autonomous -  - : Green -> blue")

        for x in range(255):
            pixel.fill((0, 255 - x, x))
            time.sleep(0.025)
        cleanup_memory()
    # End While


##########################################
#  Main Entrypoint
#
##########################################
if __name__ == "__main__":
    main()
