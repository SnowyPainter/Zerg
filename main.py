import threading
import pyautogui
import numpy as np
import cv2
from PIL import ImageGrab
import time
from pynput import keyboard

width, height = pyautogui.size()
print(width, height)

threshold = 0.8
#for i in range(10):
#    print(f"{10-i}")
#    time.sleep(1)

next_icon = cv2.imread("./next.png")
after_learn_icon = cv2.imread("./after_learn.png")

next_icon = cv2.cvtColor(next_icon, cv2.COLOR_BGR2GRAY)
after_learn_icon = cv2.cvtColor(after_learn_icon, cv2.COLOR_BGR2GRAY)
_, next_icon = cv2.threshold(next_icon, 127, 255, cv2.THRESH_BINARY)
_, after_learn_icon = cv2.threshold(after_learn_icon, 127, 255, cv2.THRESH_BINARY)

def get_center_of_top_left(image, top_left):
    image_height, image_width = image.shape[:2]
    bottom_right = (top_left[0] + image_width, top_left[1] + image_height)
    
    center_x = (top_left[0] + bottom_right[0]) // 2
    center_y = (top_left[1] + bottom_right[1]) // 2
    return (center_x, center_y)

def is_image_exist(frame, image, threshold):
    result = cv2.matchTemplate(frame, image, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        return get_center_of_top_left(image, max_loc)
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
    _, darker_frame = cv2.threshold(frame, 200, 255, cv2.THRESH_BINARY)
    next_central_xy = is_image_exist(darker_frame, next_icon, threshold=0.8)
    exit_learn_central_xy = is_image_exist(darker_frame, after_learn_icon, threshold=0.75)
    
    if next_central_xy != None:
        pyautogui.moveTo(next_central_xy[0], next_central_xy[1], duration=0.3)
        pyautogui.click()
    elif exit_learn_central_xy != None:
        pyautogui.moveTo(exit_learn_central_xy[0], exit_learn_central_xy[1], duration=0.3)
        pyautogui.click()
    else:
        if side_to_side_flag:
            pyautogui.moveTo(50, 50, duration=0.5)
        else:
            pyautogui.moveTo(1920/2, 1024/2, duration=0.5)
        side_to_side_flag = not side_to_side_flag
        time.sleep(1)
    
    #cv2.imshow("d", darker_frame)
    
    if cv2.waitKey(1) & 0Xff == ord('q'):
        break
        
cv2.destroyAllWindows()

keyboard_thread.join()