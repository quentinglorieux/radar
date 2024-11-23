import serial  # For radar sensor communication
from picamera2 import Picamera2  # For camera control
from datetime import datetime  # For timestamping images
from time import sleep
import json

# Initialize Serial Communication with Radar
ser = serial.Serial(
    port='/dev/ttyACM0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1,
    writeTimeout=2
)
ser.flushInput()
ser.flushOutput()

# Function to Send Commands to the Radar
def send_serial_cmd(print_prefix, command):
    """
    function for sending serial commands to the OPS module
    """
    data_for_send_str = command
    data_for_send_bytes = str.encode(data_for_send_str)
    print(print_prefix, command)
    ser.write(data_for_send_bytes)
    # initialize message verify checking
    ser_message_start = '{'
    ser_write_verify = False
    # print out module response to command string
    while not ser_write_verify:
        data_rx_bytes = ser.readline()
        data_rx_length = len(data_rx_bytes)
        if data_rx_length != 0:
            data_rx_str = str(data_rx_bytes)
            if data_rx_str.find(ser_message_start):
                ser_write_verify = True

# constants for the OPS module
Ops_Speed_Output_Units = ['US', 'UK', 'UM', 'UC']
Ops_Speed_Output_Units_lbl = ['mph', 'km/h', 'm/s', 'cm/s']
Ops_Blanks_Pref_Zero = 'BZ'
Ops_Sampling_Frequency = 'SX'
Ops_Transmit_Power = 'PX'
Ops_Threshold_Control = 'MX'
Ops_Module_Information = '??'
Ops_Overlook_Buffer = 'OZ'
send_serial_cmd(ser, "OJ")    # Set output format to JSON

# initialize the OPS module
send_serial_cmd("\nOverlook buffer", Ops_Overlook_Buffer)
send_serial_cmd("\nSet Speed Output Units: ", Ops_Speed_Output_Units[1])
send_serial_cmd("\nSet Sampling Frequency: ", Ops_Sampling_Frequency)
send_serial_cmd("\nSet Transmit Power: ", Ops_Transmit_Power)
send_serial_cmd("\nSet Threshold Control: ", Ops_Threshold_Control)
send_serial_cmd("\nSet Blanks Preference: ", Ops_Blanks_Pref_Zero)
# send_serial_cmd("\nModule Information: ", Ops_Module_Information)

# Initialize Camera
camera = Picamera2()
camera.start()  # Start the camera for continuous use


# Define Speed Threshold for Capturing Image
speed_threshold = 3  # Speed threshold in km/h
log_file = "traffic_log.txt"  # Log file to store hourly data
last_upload_time = datetime.now()  # Track the last upload time

# Function to log data locally
def log_data_locally(timestamp, speed):
    """Append speed and timestamp data to a local log file."""
    with open(log_file, "a") as f:
        f.write(f"{timestamp},{speed}\n")
    print(f"Logged locally: {timestamp}, {speed} km/h")

# Main Loop to Read Radar Data and Capture Images
try:
    while True:
        sleep(0.1)
        speed_available = False  # Reset speed flag
        Ops_rx_bytes = ser.readline()  # Read from radar sensor
        Ops_rx_bytes_length = len(Ops_rx_bytes)
        
        # Check if data was received
        if Ops_rx_bytes_length != 0:
            Ops_rx_str = Ops_rx_bytes.decode().strip()  # Decode bytes to string

            # Attempt to parse JSON and extract speed
            try:
                data = json.loads(Ops_rx_str)  # Parse JSON
                if "speed" in data:
                    Ops_rx_float = float(data["speed"])
                    speed_available = True
                    print(Ops_rx_float)

            except (json.JSONDecodeError, ValueError) as e:
                print("Invalid data received:", Ops_rx_str)
                speed_available = False

        # If speed is available and above threshold, capture an image
        if speed_available and abs(Ops_rx_float) > speed_threshold:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            camera.capture_file(f'vehicle_{timestamp}.jpg')  # Capture image
            log_data_locally(timestamp, Ops_rx_float)
            print(f"Vehicle detected above threshold at {Ops_rx_float} km/h! Image captured.")
            print("wait.....")
            sleep(1)
            print("Ready")
            # Clear the radar buffer to discard piled-up data
            ser.reset_input_buffer()
            print("Radar buffer cleared.")


except KeyboardInterrupt:
    print("Exiting...")

finally:
    # Clean up
    camera.stop()  # Stop the camera
    ser.close()  # Close serial connection
    # pygame.quit()  # Quit Pygame
