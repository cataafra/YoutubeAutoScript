from multiprocessing.connection import wait
import sys
import time
import logging
import threading

# needed for video rec
import cv2
import numpy as np
import pyautogui

# needed for audio rec
import pyaudio
import wave

# needed for navigating a browser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

# needed for joining the two
from moviepy.editor import *

# to compute sound level
from analyze_wav import measure_wav_db_level


def wait_for(ELEM_XPATH):
    wait = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, ELEM_XPATH)))
    wait = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.XPATH, ELEM_XPATH)))
    wait = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, ELEM_XPATH)))


# configuring the logging
LOG_FORMAT = "[%(levelname)s] %(asctime)s - %(message)s"
logging.basicConfig(level=logging.INFO,
                    format=LOG_FORMAT,
                    handlers=[
                        logging.FileHandler("logfile.log"),
                        logging.StreamHandler(sys.stdout)
                    ])
logger = logging.getLogger()

logger.info(15*"-")
logger.info("STARTING SCRIPT")
logger.info(15*"-")

# configuring the driver
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument("--start-maximized")  # to start in fullscreen

# getting the search query from command line/defaut
SEARCH_TEXT = ""
if len(sys.argv) > 1:
    for i in range(1, len(sys.argv)):
        SEARCH_TEXT += str(sys.argv[i]) + "+"
    logger.info("Searching for: %s", SEARCH_TEXT)
else:
    SEARCH_TEXT = "Funny+Videos"
    logger.info("Searching for: %s (default)", SEARCH_TEXT)
URL = 'https://www.youtube.com/results?search_query=' + SEARCH_TEXT

# starting the driver
try:
    driver = webdriver.Chrome(options=options)
    logger.info("Driver sucessfully started")
except:
    logger.error("Driver start failed! Program will close!")
    exit()

# opening youtube to the searched video
try:
    driver.get(URL)
    logger.info("Youtube sucessfully opened")
except:
    logger.info("Youtube open failed, check internet! Program will close!")

# accepting the cookies popup, if one appears
try:
    accept_cookies = driver.find_element(
        By.XPATH, '/html/body/ytd-app/ytd-consent-bump-v2-lightbox/tp-yt-paper-dialog/div[4]/div[2]/div[6]/div[1]/ytd-button-renderer[2]/a/tp-yt-paper-button')
    logger.info("Cookies pop-up shown")
    accept_cookies.click()
    logger.info("Cookies Pop-up Succesfully Accepted")
except NoSuchElementException:
    logger.info("Cookies pop-up not shown")

wait_for('//*[@id="dismissible"]')

video_thumbnail = driver.find_element(
    By.XPATH, '//*[@id="dismissible"]')
video_thumbnail.click()

wait_for(
    '/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[1]/div/div/div/ytd-player/div/div')

youtube_video = driver.find_element(
    By.XPATH, '/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[1]/div/div/div/ytd-player/div/div')

# ad handling
while 'ad-showing' in youtube_video.get_attribute('class').split():
    logger.info('Ad is showing')
    time.sleep(0.5)
    try:
        adDuration = driver.find_element(
            By.XPATH, '/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[1]/div/div/div/ytd-player/div/div/div[17]/div/div[3]/div/div[1]/span/div').text
        logger.info('Skippable Ad after %ss', adDuration)
        time.sleep(int(adDuration) + 0.5)
        skipButton = driver.find_element(
            By.XPATH, '/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[1]/div/div/div/ytd-player/div/div/div[17]/div/div[3]/div/div[2]/span/button')
        skipButton.click()
        logger.info('Ad Skipped')
    except NoSuchElementException:
        adDuration = driver.find_element(
            By.XPATH, '/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[1]/div/div/div/ytd-player/div/div/div[17]/div/div[2]/span[2]/div').text.split(":")[1]
        logger.info('Unskippable Ad of %ss', adDuration)
        time.sleep(int(adDuration) + 1)

# Video recording


def video_record(RECORD_TIME):
    # Setting up the video recording process
    SCREEN_SIZE = tuple(pyautogui.size())
    codec = cv2.VideoWriter_fourcc(*"XVID")
    FILENAME = "output.avi"
    FPS = 24.0
    out = cv2.VideoWriter(FILENAME, codec, FPS, SCREEN_SIZE)

    timer = 0
    logger.info("Video recording started")
    while timer <= RECORD_TIME*FPS:
        img = pyautogui.screenshot()
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        out.write(frame)

        timer += 1

    out.release()
    cv2.destroyAllWindows()

# Audio recording


def audio_record(RECORD_SECONDS):
    # Setting up the audio recording process
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 48000
    RECORD_SECONDS = 5
    WAVE_OUTPUT_FILENAME = 'output.wav'

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=5,
                    as_loopback=True)

    frames = []

    timer = 0
    logger.info("Audio recording started")
    while timer <= int(RATE / CHUNK * RECORD_SECONDS):
        data = stream.read(CHUNK)
        frames.append(data)

        timer += 1

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()


RECORD_TIME = 5

logger.info("Recording Started")

thread1 = threading.Thread(target=video_record, args=(RECORD_TIME,))
thread2 = threading.Thread(target=audio_record, args=(RECORD_TIME,))
thread1.start()
thread2.start()

thread1.join()
thread2.join()

logger.info("Recording ended")

driver.quit()  # closes the window and ends chromedriver

logger.info("Audio level: %s dBFS", str(measure_wav_db_level("output.wav")))

# merging the 2 recordings
logger.info("Merging videos...")
video = VideoFileClip('output.avi')
audio = AudioFileClip('output.wav')

video = video.set_audio(audio)
video.write_videofile('final.mp4', logger=None)
logger.info("Recordings succesfully merged into final.mp4")
