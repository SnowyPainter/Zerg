import threading
import pyautogui
import numpy as np
import cv2
from PIL import ImageGrab
import time
from pynput import keyboard
from datetime import datetime

width, height = pyautogui.size()

print("*"*50)
print(" "*15, "Welcome to Shila Zerg")
print("*"*50)
print("")

print("="*21, "SYSTEM", "="*21)
print(f"Your screen system consists of : {width} x {height}")
print("="*50)
print("시스템 배율을 선택하세요. (컴퓨터 100%, 노트북 125% 권장, 노트북 안될 시 150%)")
mag = {
    1 : "100%",
    2 : "125%",
    3 : "150%"
}
for n, s in mag.items():
    print(f"{n}. {s}")
magnification = int(input("번호 : "))
for i in range(10):
    print(f"{10-i}초 후에 시작됩니다.")
    time.sleep(1)

def convert_binary(image):    
    cvt_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, cvt_image = cv2.threshold(cvt_image, 127, 255, cv2.THRESH_BINARY)
    return cvt_image

next_icon_100 = cv2.imread("./next.png")
next_icon_150 = cv2.imread("./next_lt.png")
next_icon_125 = cv2.imread("./next_125.png")
after_learn_icon_100 = cv2.imread("./after_learn.png")
after_learn_icon_150 = cv2.imread("./after_learn_lt.png")
after_learn_icon_125 = cv2.imread("./after_learn_125.png")

next_icon_100 = convert_binary(next_icon_100)
next_icon_150 = convert_binary(next_icon_150)
next_icon_125 = convert_binary(next_icon_125)
after_learn_icon_100 = convert_binary(after_learn_icon_100)
after_learn_icon_125 = convert_binary(after_learn_icon_125)
after_learn_icon_150 = convert_binary(after_learn_icon_150)

def get_center_of_top_left(image, top_left):
    image_height, image_width = image.shape[:2]
    bottom_right = (top_left[0] + image_width, top_left[1] + image_height)
    
    center_x = (top_left[0] + bottom_right[0]) // 2
    center_y = (top_left[1] + bottom_right[1]) // 2
    return (center_x, center_y)

prev_max_val_next = 0
prev_max_val_afl = 0

def is_image_exist(frame, image, threshold, debug_log=""):
    result = cv2.matchTemplate(frame, image, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    print(f"DEBUG:\t{debug_log} {max_val} | {next_button_threshold}, {afl_button_threshold}")
    if max_val >= threshold:
        print(f"DEBUG:\tThreshold {threshold}, detected image {max_val}")
        return get_center_of_top_left(image, max_loc)
    else:
        None
def click_to(x, y, title=""):
    print(f"DEBUG:\t{title}\tClicked - {datetime.now()}")
    pyautogui.moveTo(x, y, duration=0.3)
    pyautogui.click()

def on_release(key):
    global stop_flag, next_button_threshold, afl_button_threshold
    
    if key == keyboard.Key.up:
        next_button_threshold += 0.05
        afl_button_threshold += 0.05
        print("DEBUG:\tNEXT,AFL BTN SENS += 0.5")
    if key == keyboard.Key.down:
        next_button_threshold -= 0.05
        afl_button_threshold -= 0.05
        print("DEBUG:\tNEXT,AFL BTN SENS -= 0.5")
    
    if key == keyboard.Key.esc:
        stop_flag = True
        return False

def listen_keyboard():
    with keyboard.Listener(on_release=on_release) as listener:
        listener.join()
keyboard_thread = threading.Thread(target=listen_keyboard)
keyboard_thread.start()

next_button_threshold = 0.8
afl_button_threshold = 0.75
stop_flag = False
side_to_side_flag = False

if magnification == 1:
    next_icon = next_icon_100
    after_learn_icon = after_learn_icon_100
elif magnification == 2:
    next_icon = next_icon_125
    after_learn_icon = after_learn_icon_125
else:
    next_icon = next_icon_150
    after_learn_icon = after_learn_icon_150

while not stop_flag:
    img = ImageGrab.grab(bbox=(width/2-width/2, height/2-height/2, width/2 + width/2, height/2 + height/2)) #x, y, w, h
    img_np = np.array(img)
    frame = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    _, darker_frame = cv2.threshold(frame, 200, 255, cv2.THRESH_BINARY)
    
    next_central_xy = is_image_exist(darker_frame, next_icon, threshold=next_button_threshold, debug_log="next")
    exit_learn_central_xy = is_image_exist(darker_frame, after_learn_icon, threshold=afl_button_threshold, debug_log="afl")

    # PC
    if next_central_xy != None:
        click_to(next_central_xy[0], next_central_xy[1], "Next Button")
    elif exit_learn_central_xy != None:
        click_to(exit_learn_central_xy[0], exit_learn_central_xy[1], "Done of Learning")
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