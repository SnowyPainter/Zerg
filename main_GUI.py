import sys
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
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, 
                             QHBoxLayout, QWidget, QProgressBar, QSlider, QGroupBox, 
                             QMessageBox, QStatusBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont

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
        file_name = f"{log_folder}/GUI_{current_datetime}.txt"
        log_file_path = os.path.join(os.getcwd(), file_name)
        open(log_file_path, 'a').close()
        return log_file_path

    def log(self, title, content):
        with open(self.log_file, 'a') as file:
            file.write(f"[{datetime.now()}] {title}:\t{content}\n")

class ImageProcessor:
    @staticmethod
    def convert_binary(image):    
        if image is None:
            return None
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

class AutoClickerWorker(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    
    def __init__(self, auto_clicker):
        super().__init__()
        self.auto_clicker = auto_clicker
        self.running = False
        
    def run(self):
        self.running = True
        self.auto_clicker.stop_flag = False
        click_time = time.time()
        
        self.status_signal.emit("작동 중")
        
        while not self.auto_clicker.stop_flag and self.running:
            try:
                img = ImageGrab.grab(bbox=(0, 0, self.auto_clicker.width, self.auto_clicker.height))
                img_np = np.array(img)
                frame = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                _, darker_frame = cv2.threshold(frame, 200, 255, cv2.THRESH_BINARY)

                next_central_xy = self.auto_clicker.is_image_exist(darker_frame, self.auto_clicker.next_icon, 
                                                        button_type='next', debug_log="next")
                exit_learn_central_xy = self.auto_clicker.is_image_exist(darker_frame, self.auto_clicker.after_learn_icon, 
                                                               button_type='after_learn', debug_log="afl")
                cancel_central_xy = self.auto_clicker.is_image_exist(darker_frame, self.auto_clicker.cancel_icon,
                                                          button_type='cancel', debug_log="cancel")

                if next_central_xy:
                    clicked = time.time()
                    if clicked - click_time > self.auto_clicker.click_delay:
                        self.auto_clicker.click_to(next_central_xy[0], next_central_xy[1], "Next Button")
                        self.log_signal.emit("다음 버튼 클릭")
                        click_time = clicked
                elif exit_learn_central_xy:
                    self.auto_clicker.click_to(exit_learn_central_xy[0], exit_learn_central_xy[1], "Done of Learning")
                    self.log_signal.emit("학습종료 버튼 클릭")
                elif cancel_central_xy:
                    self.auto_clicker.click_to(cancel_central_xy[0], cancel_central_xy[1], "Cancel Button")
                    self.log_signal.emit("취소 버튼 클릭")
                    start_clicked = self.auto_clicker.check_and_click_start()
                    if start_clicked:
                        self.log_signal.emit("시작 버튼 클릭")
                else:
                    if self.auto_clicker.side_to_side_flag:
                        pyautogui.moveTo(50, 50, duration=self.auto_clicker.move_duration)
                    else:
                        pyautogui.moveTo(self.auto_clicker.width/2, self.auto_clicker.height/2, 
                                        duration=self.auto_clicker.move_duration)
                    self.auto_clicker.side_to_side_flag = not self.auto_clicker.side_to_side_flag
                    time.sleep(self.auto_clicker.scan_delay)
                
            except Exception as e:
                self.log_signal.emit(f"오류 발생: {str(e)}")
                
        self.status_signal.emit("중지됨")
            
    def stop(self):
        self.running = False
        self.auto_clicker.stop_flag = True
        self.wait()

class AutoClicker:
    def __init__(self):
        self.debugger = Debugger()
        self.width, self.height = pyautogui.size()
        self.stop_flag = False
        self.side_to_side_flag = False
        
        # 설정 초기화
        self.move_duration = DEFAULT_MOVE_DURATION
        self.click_delay = DEFAULT_CLICK_DELAY
        self.scan_delay = DEFAULT_SCAN_DELAY
        
        # 배율 감지
        self.scaling = self.get_windows_scaling()
        
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
        # 리소스 폴더가 없으면 경고 메시지만 표시하고 계속 진행
        if not os.path.exists(resource_path):
            print(f"경고: 리소스 폴더({resource_path})가 존재하지 않습니다.")
            self.next_icon = None
            self.after_learn_icon = None
            self.cancel_icon = None
            self.start_icon = None
            return False
            
        # 배율에 따른 이미지 선택
        if self.scaling <= 100:
            suffix = ''
        elif self.scaling <= 125:
            suffix = '_125'
        else:
            suffix = '_150'
            
        # 이미지 파일 경로
        next_path = f"{resource_path}/next{suffix}.png"
        after_learn_path = f"{resource_path}/after_learn{suffix}.png"
        cancel_path = f"{resource_path}/cancel{suffix}.png"
        start_path = f"{resource_path}/start{suffix}.png"
        
        # 이미지 파일 존재 확인 및 로드
        self.next_icon = None if not os.path.exists(next_path) else ImageProcessor.convert_binary(cv2.imread(next_path))
        self.after_learn_icon = None if not os.path.exists(after_learn_path) else ImageProcessor.convert_binary(cv2.imread(after_learn_path))
        self.cancel_icon = None if not os.path.exists(cancel_path) else ImageProcessor.convert_binary(cv2.imread(cancel_path))
        self.start_icon = None if not os.path.exists(start_path) else ImageProcessor.convert_binary(cv2.imread(start_path))
        
        # 이미지 로드 상태 반환
        return all([self.next_icon is not None, self.after_learn_icon is not None, 
                   self.cancel_icon is not None, self.start_icon is not None])

    def click_to(self, x, y, title=""):
        self.debugger.log("click_to func", f"\t{title}\tClicked")
        pyautogui.moveTo(x, y, duration=self.move_duration)
        pyautogui.click()
        time.sleep(self.click_delay)

    def is_image_exist(self, frame, image, button_type, debug_log=""):
        if image is None:
            return None
            
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

class ShilaZergGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.auto_clicker = AutoClicker()
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Shila Zerg - 자동 클릭 도우미')
        self.setGeometry(100, 100, 500, 400)
        
        # 메인 위젯 및 레이아웃
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # 제목 및 설명
        title_label = QLabel('명문 신라 Zerg')
        title_label.setFont(QFont('Arial', 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        description_label = QLabel('학습 프로그램 자동 클릭 도우미')
        description_label.setAlignment(Qt.AlignCenter)
        
        main_layout.addWidget(title_label)
        main_layout.addWidget(description_label)
        
        # 시스템 정보 그룹
        system_group = QGroupBox('시스템 정보')
        system_layout = QVBoxLayout()
        
        # 해상도 및 배율 표시
        resolution_label = QLabel(f'화면 해상도: {self.auto_clicker.width}x{self.auto_clicker.height}')
        scaling_label = QLabel(f'디스플레이 배율: {self.auto_clicker.scaling:.0f}%')
        
        system_layout.addWidget(resolution_label)
        system_layout.addWidget(scaling_label)
        
        # 리소스 상태 표시
        resource_status = "정상" if self.auto_clicker.load_icons() else "이미지 파일 없음"
        self.resource_status_label = QLabel(f'리소스 상태: {resource_status}')
        system_layout.addWidget(self.resource_status_label)
        
        system_group.setLayout(system_layout)
        main_layout.addWidget(system_group)
        
        # 설정 그룹
        settings_group = QGroupBox('설정')
        settings_layout = QVBoxLayout()
        
        sensitivity_group = QGroupBox('감지 민감도 설정')
        sensitivity_layout = QVBoxLayout()

        self.sensitivity_sliders = {}  # 슬라이더 저장용 딕셔너리
        self.sensitivity_labels = {}  # 감지 민감도 값 표시용 라벨

        sensitivity_items = {
            "next": "다음 영상",
            "after_learn": "학습 완료",
            "cancel": "계속 시청",
            "start": "계속 재생"
        }

        for key, label_text in sensitivity_items.items():
            layout = QHBoxLayout()
            label = QLabel(f'{label_text}:')
            layout.addWidget(label)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(50)
            slider.setMaximum(100)
            slider.setValue(int(self.auto_clicker.thresholds[key] * 100))
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(5)
            slider.valueChanged.connect(lambda value, k=key: self.update_sensitivity(k, value))
            layout.addWidget(slider)

            value_label = QLabel(f"{self.auto_clicker.thresholds[key]:.2f}")
            layout.addWidget(value_label)

            self.sensitivity_sliders[key] = slider
            self.sensitivity_labels[key] = value_label

            sensitivity_layout.addLayout(layout)

        sensitivity_group.setLayout(sensitivity_layout)
        main_layout.addWidget(sensitivity_group)
        
        # 타이밍 설정
        # 마우스 이동 속도
        move_speed_layout = QHBoxLayout()
        move_speed_label = QLabel('마우스 이동 속도:')
        move_speed_layout.addWidget(move_speed_label)
        
        self.move_speed_slider = QSlider(Qt.Horizontal)
        self.move_speed_slider.setMinimum(1)
        self.move_speed_slider.setMaximum(20)
        self.move_speed_slider.setValue(int(self.auto_clicker.move_duration * 10))
        self.move_speed_slider.valueChanged.connect(self.update_move_speed)
        move_speed_layout.addWidget(self.move_speed_slider)
        
        self.move_speed_value_label = QLabel(f"{self.auto_clicker.move_duration:.1f}초")
        move_speed_layout.addWidget(self.move_speed_value_label)
        
        settings_layout.addLayout(move_speed_layout)
        
        # 클릭 간 딜레이
        click_delay_layout = QHBoxLayout()
        click_delay_label = QLabel('클릭 간 딜레이 (초):')
        click_delay_layout.addWidget(click_delay_label)
        
        self.click_delay_slider = QSlider(Qt.Horizontal)
        self.click_delay_slider.setMinimum(1)  # 0.1초
        self.click_delay_slider.setMaximum(20)  # 2.0초
        self.click_delay_slider.setValue(int(self.auto_clicker.click_delay * 10))  # 초기값 설정
        self.click_delay_slider.valueChanged.connect(self.update_click_delay)
        click_delay_layout.addWidget(self.click_delay_slider)
        
        self.click_delay_value = QLabel(f"{self.auto_clicker.click_delay:.1f}")
        click_delay_layout.addWidget(self.click_delay_value)
        
        settings_layout.addLayout(click_delay_layout)
        
        # 스캔 간 딜레이
        scan_delay_layout = QHBoxLayout()
        scan_delay_label = QLabel('스캔 간 딜레이:')
        scan_delay_layout.addWidget(scan_delay_label)
        
        self.scan_delay_slider = QSlider(Qt.Horizontal)
        self.scan_delay_slider.setMinimum(5)
        self.scan_delay_slider.setMaximum(30)
        self.scan_delay_slider.setValue(int(self.auto_clicker.scan_delay * 10))
        self.scan_delay_slider.valueChanged.connect(self.update_scan_delay)
        scan_delay_layout.addWidget(self.scan_delay_slider)
        
        self.scan_delay_value_label = QLabel(f"{self.auto_clicker.scan_delay:.1f}초")
        scan_delay_layout.addWidget(self.scan_delay_value_label)
        
        settings_layout.addLayout(scan_delay_layout)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # 작동 버튼 그룹
        control_group = QGroupBox('작동')
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton('시작')
        self.start_btn.clicked.connect(self.start_auto_clicker)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton('중지')
        self.stop_btn.clicked.connect(self.stop_auto_clicker)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # 로그 창
        log_group = QGroupBox('로그')
        log_layout = QVBoxLayout()
        
        self.log_label = QLabel('준비됨')
        log_layout.addWidget(self.log_label)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # 상태 바
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('준비됨')
        
        # 레이아웃 완성
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 리소스 상태에 따라 시작 버튼 활성화 여부 결정
        self.start_btn.setEnabled(self.auto_clicker.load_icons())
        
        # 리소스가 없으면 경고 메시지 표시
        if not self.auto_clicker.load_icons():
            QMessageBox.warning(self, "리소스 경고", 
                               "리소스 폴더(./resource)가 없거나 이미지 파일이 없습니다.\n"
                               "프로그램 실행을 위해 리소스 폴더와 이미지 파일이 필요합니다.")
        
    def update_threshold(self):
        value = self.threshold_slider.value() / 100
        self.auto_clicker.thresholds['next'] = value
        self.auto_clicker.thresholds['after_learn'] = value - 0.05
        self.auto_clicker.thresholds['cancel'] = value
        self.auto_clicker.thresholds['start'] = value
        self.threshold_value_label.setText(f"{value:.2f}")
        
    def update_move_speed(self):
        value = self.move_speed_slider.value() / 10
        self.auto_clicker.move_duration = value
        self.move_speed_value_label.setText(f"{value:.1f}초")
        
    def update_click_delay(self, value):
        self.auto_clicker.click_delay = value / 10.0
        self.click_delay_value.setText(f"{self.auto_clicker.click_delay:.1f}")
        
    def update_scan_delay(self):
        value = self.scan_delay_slider.value() / 10
        self.auto_clicker.scan_delay = value
        self.scan_delay_value_label.setText(f"{value:.1f}초")
    
    def start_auto_clicker(self):
        if not self.worker or not self.worker.isRunning():
            self.worker = AutoClickerWorker(self.auto_clicker)
            self.worker.log_signal.connect(self.update_log)
            self.worker.status_signal.connect(self.update_status)
            self.worker.start()
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_bar.showMessage('실행 중')
    
    def stop_auto_clicker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_bar.showMessage('중지됨')
    
    def update_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_label.setText(f"[{timestamp}] {message}")
    
    def update_status(self, status):
        self.status_bar.showMessage(status)
        
    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = ShilaZergGUI()
    gui.show()
    sys.exit(app.exec_())