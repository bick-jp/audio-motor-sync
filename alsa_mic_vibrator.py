#!/usr/bin/python

import alsaaudio
import time
import audioop
from struct import unpack
import numpy as np
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from threading import Timer

### Reference
#https://ubuntuforums.org/showthread.php?t=500337&p=6505818#post6505818
#https://www.rototron.info/raspberry-pi-spectrum-analyzer/

# Motor
num_of_motors = 8
i2c_bus = busio.I2C(SCL, SDA) # Create the I2C bus interface.
pca = PCA9685(i2c_bus) # Create a simple PCA9685 class instance.
pca.frequency = 60 # Set the PWM frequency to 60hz.


# Open the device in nonblocking capture mode. The last argument could
# just as well have been zero for blocking mode. Then we could have
# left out the sleep call in the bottom of the loop
inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,alsaaudio.PCM_NONBLOCK)

# Set attributes
inp.setchannels(2)
sample_rate = 8000
inp.setrate(sample_rate)
inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

# The period size controls the internal number of frames per period.
# The significance of this parameter is documented in the ALSA api.
# For our purposes, it is suficcient to know that reads from the device
# will return this many frames. Each frame being 2 bytes long.
# This means that the reads below will return either 320 bytes of data
# or 0 bytes of data. The latter is possible because we are in nonblocking
# mode.
#inp.setperiodsize(160)
chunk = 160
inp.setperiodsize(chunk)

# For calculation
matrix    = [0]
power     = []
weighting = [128] # Why 8? Not sure

# Bass amplitude for vibration
# Decided base on experiment
threshold = 40

### Functions ###
# Return power array index corresponding to a particular frequency
def piff(val):
    return int(2*chunk*val/sample_rate)
   
def calculate_levels(data):
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

while True:
    # Read data from device
    l,data = inp.read()
    if l:
        # Get bass level and power motor if above threshold
        matrix=calculate_levels(data)
        #print(matrix[0])
        if matrix[0] > threshold:
            #print("detect")
            timer = Timer(0, runMotor) # 0.01 is from experience
            timer.start()