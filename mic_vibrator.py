import sys
import pyaudio
from struct import unpack
import numpy as np
from board import SCL, SDA
import busio
import time
from adafruit_pca9685 import PCA9685
from threading import Timer

### Reference
# https://www.rototron.info/raspberry-pi-spectrum-analyzer/

### Setup ###
# Motor
num_of_motors = 8
i2c_bus = busio.I2C(SCL, SDA) # Create the I2C bus interface.
pca = PCA9685(i2c_bus) # Create a simple PCA9685 class instance.
pca.frequency = 60 # Set the PWM frequency to 60hz.

# Audio setup
no_channels = 1
sample_rate = 44100
# Chunk must be a multiple of 8
# NOTE: If chunk size is too small the program will crash
# with error message: [Errno Input overflowed]
chunk = 512

p = pyaudio.PyAudio()
stream = p.open(format = pyaudio.paInt16,
                channels = no_channels,
                rate = sample_rate,
                input = True,
                frames_per_buffer = chunk)

# For calculation
matrix    = [0]
power     = []
weighting = [64] # for the sake of easy calculation

# Bass amplitude for vibration
# Decided base on experiment
threshold = 50


### Functions ###
# Return power array index corresponding to a particular frequency
def piff(val):
    return int(2*chunk*val/sample_rate)
   
def calculate_levels(data, chunk,sample_rate):
    global matrix

    # Convert raw data (ASCII string) to numpy array
    data = unpack("%dh"%(len(data)/2),data)
    data = np.array(data, dtype='h')

    # Apply FFT - real data
    fourier=np.fft.rfft(data)
    # Remove last element in array to make it the same size as chunk
    fourier=np.delete(fourier,len(fourier)-1)
    # Find average 'amplitude' for specific frequency ranges in Hz
    # In this case 0 - 200 Hz since only interested in bass
    power = np.abs(fourier)   
    matrix = int(np.mean(power[piff(0):piff(200):1]))
    
    # Tidy up column values for the LED matrix
    # Why 1000000? Not sure.
    matrix = np.divide(np.multiply(matrix,weighting),1000000)

    return matrix

def runMotor():
    #t = time.time()
    for x in range(num_of_motors):
        pca.channels[x].duty_cycle = 0xFFFF

    time.sleep(0.1) # 0.1 is from experience

    for x in range(num_of_motors):
        pca.channels[x].duty_cycle = 0x0000
    #print((time.time() - t))

# Main loop
while 1:
    try:
        # Get microphone data
        data = stream.read(chunk, exception_on_overflow = False)
        matrix=calculate_levels(data, chunk,sample_rate)
        #print(matrix[0])
        
        if matrix[0] > threshold:
            #print("a")
            timer = Timer(0, runMotor) # 0.01 is from experience
            timer.start()
        
    except KeyboardInterrupt:
        print("Ctrl-C Terminating...")
        stream.stop_stream()
        stream.close()
        p.terminate()
        sys.exit(1)

    except Exception as e:
        print(e)
        print("ERROR Terminating...")
        stream.stop_stream()
        stream.close()
        p.terminate()
        sys.exit(1)
