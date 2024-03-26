import threading
import pyautogui
import numpy as np
import cv2
from PIL import ImageGrab
import time
from pynput import keyboard

width = 1920
height = 1024

next_icon = cv2.imread("./next.png")
next_icon = cv2.cvtColor(next_icon, cv2.COLOR_BGR2GRAY)
_, next_icon = cv2.threshold(next_icon, 127, 255, cv2.THRESH_BINARY)

def is_time_to_next(frame, next_icon=next_icon):
    result = cv2.matchTemplate(frame, next_icon, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    threshold = 0.8  # 임계값
    if max_val >= threshold:
        image_height, image_width = next_icon.shape[:2]
        top_left = max_loc
        bottom_right = (top_left[0] + image_width, top_left[1] + image_height)
        
        center_x = (top_left[0] + bottom_right[0]) // 2
        center_y = (top_left[1] + bottom_right[1]) // 2
        return (center_x, center_y)
    else:
        None

def on_release(key):
    if key == keyboard.Key.esc:
        global stop_flag
        stop_flag = True
        return False
def listen_keyboard():
    with keyboard.Listener(on_release=on_release) as listener:
        listener.join()
keyboard_thread = threading.Thread(target=listen_keyboard)
keyboard_thread.start()

stop_flag = False
side_to_side_flag = False

while not stop_flag:
    img = ImageGrab.grab(bbox=(1920/2-width/2, 1024/2-height/2, 1920/2 + width/2, 1024/2 + height/2)) #x, y, w, h
    img_np = np.array(img)
    frame = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    
    central_xy = is_time_to_next(frame)
    
    if central_xy != None:
        pyautogui.moveTo(central_xy[0], central_xy[1], duration=0.3)
        pyautogui.click()

    else:
        if side_to_side_flag:
            pyautogui.moveTo(50, 50, duration=0.5)
        else:
            pyautogui.moveTo(1920/2, 1024/2, duration=0.5)
        side_to_side_flag = not side_to_side_flag
        time.sleep(1)
        
    if cv2.waitKey(1) & 0Xff == ord('q'):
        break
        
cv2.destroyAllWindows()

keyboard_thread.join()