import alsaaudio as aa
import wave
from struct import unpack
import numpy as np
from board import SCL, SDA
import busio
import time
from adafruit_pca9685 import PCA9685
from threading import Timer

### Setup ###
# Motor
num_of_motors = 8
i2c_bus = busio.I2C(SCL, SDA) # Create the I2C bus interface.
pca = PCA9685(i2c_bus) # Create a simple PCA9685 class instance.
pca.frequency = 60 # Set the PWM frequency to 60hz.

# Audio
wavfile = wave.open('Bulls.wav','r')
sample_rate = wavfile.getframerate()
no_channels = wavfile.getnchannels()
chunk       = 512 # Use a multiple of 8

# ALSA
output = aa.PCM(type=aa.PCM_PLAYBACK, mode=aa.PCM_NORMAL)
output.setchannels(no_channels)
output.setrate(sample_rate)
output.setformat(aa.PCM_FORMAT_S16_LE)
output.setperiodsize(chunk)

# For calculation
matrix    = [0]
power     = []
weighting = [8] # Why 8? Not sure

# Bass amplitude for vibration
# Decided base on experiment
threshold = 25


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

# Start reading audio file  
data = wavfile.readframes(chunk)

# Loop while audio data present
while True:
    output.write(data)

    # End of audio file
    if data == b'':
        break
	
    # Get bass level and power motor if above threshold
    matrix=calculate_levels(data, chunk,sample_rate)
    if matrix[0] > threshold:
        timer = Timer(0.01, runMotor) # 0.01 is from experience
        timer.start()

    data = wavfile.readframes(chunk)