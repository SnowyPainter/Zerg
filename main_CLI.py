import threading
import pyautogui
import numpy as np
import cv2
from PIL import ImageGrab
import time
from pynput import keyboard
import os
from datetime import datetime
import ctypes

# 기본 설정값
DEFAULT_MOVE_DURATION = 1.0  # 마우스 이동 속도
DEFAULT_CLICK_DELAY = 1.0    # 클릭 간 대기 시간
DEFAULT_SCAN_DELAY = 1.5     # 스캔 간 대기 시간

class Debugger:
    def __init__(self):
        self.log_folder = os.path.join(os.getcwd(), 'logs')
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)
        self.log_file = self.create_log_file(self.log_folder)

    def create_log_file(self, log_folder):
        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{log_folder}/CLI_{current_datetime}.txt"
        log_file_path = os.path.join(os.getcwd(), file_name)
        open(log_file_path, 'a').close()
        return log_file_path

    def log(self, title, content):
        with open(self.log_file, 'a') as file:
            file.write(f"[{datetime.now()}] {title}:\t{content}\n")

class ImageProcessor:
    @staticmethod
    def convert_binary(image):    
        cvt_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, cvt_image = cv2.threshold(cvt_image, 127, 255, cv2.THRESH_BINARY)
        return cvt_image

    @staticmethod
    def get_center_of_top_left(image, top_left):
        image_height, image_width = image.shape[:2]
        bottom_right = (top_left[0] + image_width, top_left[1] + image_height)
        
        center_x = (top_left[0] + bottom_right[0]) // 2
        center_y = (top_left[1] + bottom_right[1]) // 2
        return (center_x, center_y)

class AutoClicker:
    def __init__(self):
        self.debugger = Debugger()
        self.width, self.height = pyautogui.size()
        self.stop_flag = False
        self.side_to_side_flag = False
        self.setup_thresholds()
        self.load_icons()

    def get_windows_scaling(self):
        """Windows 시스템의 디스플레이 배율을 가져옴"""
        try:
            user32 = ctypes.windll.user32
            dpi = user32.GetDpiForSystem()
            scaling = dpi / 96 * 100
            return scaling
        except:
            return 100  # 기본값 반환

    def setup_thresholds(self):
        # 버튼별 개별 임계값 설정
        self.thresholds = {
            'next': 0.8,
            'after_learn': 0.75,
            'cancel': 0.8,
            'start': 0.8
        }
        # 클릭 딜레이 초기값 설정
        self.click_delay = 1.0

    def load_icons(self, resource_path='./resource'):
        # 시스템 배율 자동 감지
        scaling = self.get_windows_scaling()
        print(f"감지된 시스템 배율: {scaling}%")
        
        # 배율에 따른 이미지 선택
        if scaling <= 100:
            suffix = ''
        elif scaling <= 125:
            suffix = '_125'
        else:
            suffix = '_150'
            
        print(f"선택된 이미지 배율: {suffix if suffix else '100'}%")
        
        # 이미지 로드
        self.next_icon = ImageProcessor.convert_binary(cv2.imread(f"{resource_path}/next{suffix}.png"))
        self.after_learn_icon = ImageProcessor.convert_binary(cv2.imread(f"{resource_path}/after_learn{suffix}.png"))
        self.cancel_icon = ImageProcessor.convert_binary(cv2.imread(f"{resource_path}/cancel{suffix}.png"))
        self.start_icon = ImageProcessor.convert_binary(cv2.imread(f"{resource_path}/start{suffix}.png"))

    def click_to(self, x, y, title=""):
        self.debugger.log("click_to func", f"\t{title}\tClicked")
        pyautogui.moveTo(x, y, duration=DEFAULT_MOVE_DURATION)
        pyautogui.click()
        time.sleep(self.click_delay)  # 동적 클릭 딜레이 사용

    def is_image_exist(self, frame, image, button_type, debug_log=""):
        result = cv2.matchTemplate(frame, image, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        threshold = self.thresholds.get(button_type, 0.8)  # 기본값 0.8
        
        self.debugger.log("is_image_exist func", f"{debug_log} {max_val} | threshold: {threshold}")
        
        if max_val >= threshold:
            self.debugger.log("is_image_exist func", f"Threshold {threshold}, detected image {max_val}")
            return ImageProcessor.get_center_of_top_left(image, max_loc)
        return None

    def check_and_click_start(self):
        """취소 버튼 클릭 후 1초 동안 start 버튼을 찾아서 클릭"""
        start_check_time = time.time()
        while time.time() - start_check_time < 1.0:  # 1초 동안 검사
            img = ImageGrab.grab(bbox=(0, 0, self.width, self.height))
            img_np = np.array(img)
            frame = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            _, darker_frame = cv2.threshold(frame, 200, 255, cv2.THRESH_BINARY)
            
            start_central_xy = self.is_image_exist(darker_frame, self.start_icon,
                                                 button_type='start', debug_log="start")
            if start_central_xy:
                self.click_to(start_central_xy[0], start_central_xy[1], "Start Button")
                return True
        return False

    def setup_keyboard_listener(self):
        def on_release(key):
            if key == keyboard.Key.up:
                self.thresholds['next'] += 0.05
                self.thresholds['after_learn'] += 0.05
                print("DEBUG:\tNEXT,AFL BTN SENS += 0.05")
            if key == keyboard.Key.down:
                self.thresholds['next'] -= 0.05
                self.thresholds['after_learn'] -= 0.05
                print("DEBUG:\tNEXT,AFL BTN SENS -= 0.05")
            if key == keyboard.Key.left:
                self.click_delay = max(0.1, self.click_delay - 0.1)
                print(f"DEBUG:\tCLICK DELAY -= 0.1 (현재: {self.click_delay:.1f}초)")
            if key == keyboard.Key.right:
                self.click_delay = min(2.0, self.click_delay + 0.1)
                print(f"DEBUG:\tCLICK DELAY += 0.1 (현재: {self.click_delay:.1f}초)")
            if key == keyboard.Key.esc:
                self.stop_flag = True
                return False

        listener = keyboard.Listener(on_release=on_release)
        listener.daemon = True
        listener.start()
        return listener

    def run(self):
        print("*** ESC를 눌러 종료합니다. ***")
        print("*** 방향키로 조절: 위/아래=감도, 좌/우=클릭 딜레이 ***")
        print(f"현재 클릭 딜레이: {self.click_delay:.1f}초")
        click_time = time.time()
        keyboard_thread = self.setup_keyboard_listener()

        while not self.stop_flag:
            img = ImageGrab.grab(bbox=(0, 0, self.width, self.height))
            img_np = np.array(img)
            frame = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            _, darker_frame = cv2.threshold(frame, 200, 255, cv2.THRESH_BINARY)

            next_central_xy = self.is_image_exist(darker_frame, self.next_icon, 
                                                button_type='next', debug_log="next")
            exit_learn_central_xy = self.is_image_exist(darker_frame, self.after_learn_icon, 
                                                       button_type='after_learn', debug_log="afl")
            cancel_central_xy = self.is_image_exist(darker_frame, self.cancel_icon,
                                                  button_type='cancel', debug_log="cancel")

            if next_central_xy:
                clicked = time.time()
                if clicked - click_time > self.click_delay:
                    self.click_to(next_central_xy[0], next_central_xy[1], "Next Button")
                    click_time = clicked
                    continue  # 클릭 후 바로 다음 루프로 이동
            elif exit_learn_central_xy:
                self.click_to(exit_learn_central_xy[0], exit_learn_central_xy[1], "Done of Learning")
                continue  # 클릭 후 바로 다음 루프로 이동
            elif cancel_central_xy:
                self.click_to(cancel_central_xy[0], cancel_central_xy[1], "Cancel Button")
                self.check_and_click_start()
                continue  # 클릭 후 바로 다음 루프로 이동

            # 버튼이 감지되지 않았을 때만 마우스 이동
            if self.side_to_side_flag:
                pyautogui.moveTo(50, 50, duration=DEFAULT_MOVE_DURATION)
            else:
                pyautogui.moveTo(self.width/2, self.height/2, duration=DEFAULT_MOVE_DURATION)
            self.side_to_side_flag = not self.side_to_side_flag
            time.sleep(DEFAULT_SCAN_DELAY)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()
        keyboard_thread.join()

if __name__ == "__main__":
    print("*"*50)
    print(" "*15, "Welcome to Shila Zerg")
    print("*"*50)
    print("")

    auto_clicker = AutoClicker()
    auto_clicker.run()