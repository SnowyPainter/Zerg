import os
import sys
import shutil
import subprocess
import argparse
from datetime import datetime

def create_directory(directory_path):
    """지정된 경로에 디렉토리 생성"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"디렉토리 생성: {directory_path}")

def build_executable(build_file, output_name, windowed):
    """PyInstaller를 사용하여 실행 파일 빌드"""
    try:
        print(f"실행 파일 빌드 시작... ({output_name})")
        
        # PyInstaller 명령어 설정
        pyinstaller_cmd = [
            "pyinstaller",
            "--onefile",
            "--name", output_name,
            build_file
        ]

        # GUI 모드일 경우 --windowed 추가
        if windowed:
            pyinstaller_cmd.append("--windowed")
        
        # 아이콘 파일이 있으면 추가
        if os.path.exists("icon.ico"):
            pyinstaller_cmd.append("--icon=icon.ico")
            
        # 빌드 실행
        subprocess.run(pyinstaller_cmd, check=True)
        print(f"실행 파일 빌드 완료: {output_name}")
        return True
    except Exception as e:
        print(f"실행 파일 빌드 오류: {e}")
        return False

def create_distribution_package(exe_name, mode):
    """배포 패키지 생성"""
    try:
        # 배포 폴더 생성 (GUI 또는 CLI 구분)
        dist_folder = f"ShilaZerg_{mode.upper()} 배포_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_directory(dist_folder)
        
        # 리소스 폴더 복사
        if os.path.exists("resource"):
            shutil.copytree("resource", os.path.join(dist_folder, "resource"))
        
        print(f"배포 패키지가 생성되었습니다: {dist_folder}")
        return dist_folder
    except Exception as e:
        print(f"배포 패키지 생성 오류: {e}")
        return None

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Shila Zerg 패키징 및 배포 스크립트")
    parser.add_argument("--mode", choices=["gui", "cli"], default="gui",
                        help="빌드 모드 선택 (gui 또는 cli)")
    args = parser.parse_args()

    mode = args.mode
    build_file = "main_GUI.py" if mode == "gui" else "main_CLI.py"
    exe_name = "ShilaZerg_GUI.exe" if mode == "gui" else "ShilaZerg_CLI.exe"
    windowed = mode == "gui"  # GUI 모드일 경우 --windowed 옵션 사용

    print(f"Shila Zerg 패키징 및 배포 스크립트 시작 ({mode.upper()} 모드)")
    
    if build_executable(build_file, exe_name, windowed):
        # 배포 패키지 생성
        dist_package = create_distribution_package(exe_name, mode)
        if dist_package:
            print(f"배포 준비가 완료되었습니다. 배포 패키지: {dist_package}")
    
    print("Shila Zerg 패키징 및 배포 스크립트 종료")

if __name__ == "__main__":
    main()
