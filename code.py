import sys
import os

os.environ["QT_LOGGING_RULES"] = "qt.multimedia.*=false;qt.qpa.*=false"
os.environ["QT_DEBUG_PLUGINS"] = "0"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

import random
import pyzipper
import tempfile
import atexit
import time
import ctypes

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QUrl, QTimer, Signal
from PySide6.QtGui import QPixmap

TEMP_VIDEO_PATH = None

def cleanup_temp_file():
    if TEMP_VIDEO_PATH and os.path.exists(TEMP_VIDEO_PATH):
        try:
            os.remove(TEMP_VIDEO_PATH)
        except:
            pass
atexit.register(cleanup_temp_file)

def disable_cmd_close_button():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            hMenu = ctypes.windll.user32.GetSystemMenu(hwnd, False)
            if hMenu:
                ctypes.windll.user32.DeleteMenu(hMenu, 0xF060, 0x00000000)
                ctypes.windll.user32.DrawMenuBar(hwnd)
    except Exception:
        pass



class VideoPage(QWidget):
    def __init__(self, video_path):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)

        self.lbl_hint = QLabel("按 ESC 尝试解密文件", self)
        self.lbl_hint.setStyleSheet("color: rgba(255, 255, 255, 80); font-size: 14px; font-family: Consolas, 'Microsoft YaHei';")
        self.lbl_hint.setGeometry(0, 0, 200, 30)
        self.lbl_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.lbl_error = QLabel("", self)
        self.lbl_error.setStyleSheet("color: red; font-size: 24px; background-color: black;")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.hide()

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_widget)
        self.audio.setVolume(1.0)
        self.player.setLoops(QMediaPlayer.Infinite)
        
        self.player.errorOccurred.connect(self.on_error)
        self.player.setSource(QUrl.fromLocalFile(video_path))
        
        QTimer.singleShot(500, self.player.play)

    def on_error(self, error, error_string):
        self.lbl_error.setText(f"Decoder error:\n{error_string}\n\nRequires H.264 encoding.")
        self.lbl_error.resize(self.size())
        self.lbl_error.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.lbl_hint.move(self.width() - 220, self.height() - 40)
        self.lbl_error.resize(self.size())

    def pause(self):
        self.player.pause()


class MathPage(QWidget):
    solved = Signal()
    failed = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet("QWidget { background-color: #1a1a1a; }")
        self.error_count = 0

        self.questions = [
            ("∫(0→1) (3x² + 2x) dx = ?", "2"),
            ("∫(0→π) sin(x) dx = ?", "2"),
            ("∫(0→2) 2x dx = ?", "4"),
            ("lim(x→0) (sin x / x) = ?", "1"),
            ("∫(1→e) (1/x) dx = ?", "1"),
            ("∫(-1→1) x³ dx = ?", "0"),
            ("∫(0→1) 4x³ dx = ?", "1"),
            ("∫(1→2) 3x² dx = ?", "7"),
            ("∫(0→π/2) cos(x) dx = ?", "1"),
            ("∫(0→1) (2x + 1) dx = ?", "2"),
            ("lim(x→0) (tan x / x) = ?", "1"),
            ("∫(-π/2→π/2) cos(x) dx = ?", "2"),
            ("∫(1→2) (2x - 1) dx = ?", "2"),
            ("lim(x→∞) (1 + 1/x)ˣ = ?", "e")
        ]
        self.current_q, self.correct_ans = random.choice(self.questions)

        outer_layout = QHBoxLayout(self)
        container = QWidget()
        container.setFixedWidth(650)
        inner_layout = QVBoxLayout(container)
        inner_layout.setSpacing(20)
        
        outer_layout.addStretch()
        outer_layout.addWidget(container)
        outer_layout.addStretch()

        self.lbl_title = QLabel("⚠️ 您的文件已被 AES-256 强制加密")
        self.lbl_title.setStyleSheet("color: #ff3333; font-size: 24px; font-weight: bold; border: none;")
        self.lbl_title.setAlignment(Qt.AlignCenter)

        self.lbl_desc = QLabel("密钥已绑定至您的硬件。请解答以下微积分方程以恢复文件：")
        self.lbl_desc.setStyleSheet("font-size: 16px; color: #aaaaaa; border: none;")
        self.lbl_desc.setAlignment(Qt.AlignCenter)

        self.lbl_question = QLabel(self.current_q)
        self.lbl_question.setStyleSheet("font-size: 36px; font-family: 'Consolas', 'Courier New', monospace; color: #00ffcc; margin: 15px 0; border: none;")
        self.lbl_question.setAlignment(Qt.AlignCenter)

        self.input_answer = QLineEdit()
        self.input_answer.setStyleSheet("background-color: #fff; color: #000; border: none; padding: 12px; font-size: 18px; border-radius: 5px;")
        self.input_answer.setPlaceholderText("输入解密密钥（结果）...")
        self.input_answer.returnPressed.connect(self.check_answer)

        self.btn_submit = QPushButton("验证并恢复")
        self.btn_submit.setStyleSheet("background-color: #cc0000; color: white; border: none; padding: 12px; font-size: 18px; font-weight: bold; border-radius: 5px;")
        self.btn_submit.clicked.connect(self.check_answer)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #ffcc00; font-size: 16px; border: none;")
        self.lbl_error.setAlignment(Qt.AlignCenter)

        inner_layout.addWidget(self.lbl_title)
        inner_layout.addWidget(self.lbl_desc)
        inner_layout.addWidget(self.lbl_question)
        inner_layout.addWidget(self.input_answer)
        inner_layout.addWidget(self.btn_submit)
        inner_layout.addWidget(self.lbl_error)

    def check_answer(self):
        ans = self.input_answer.text().strip().lower()
        if ans == self.correct_ans or ans == self.correct_ans + ".0":
            self.solved.emit()
        else:
            self.error_count += 1
            if self.error_count >= 3:
                self.failed.emit()
            else:
                self.lbl_error.setText(f"密钥无效，系统即将触发自毁 ({self.error_count}/3)")
                self.input_answer.clear()
                self.input_answer.setFocus()

    def reset_focus(self):
        self.input_answer.setFocus()


class BSODPage(QWidget):
    def __init__(self, pixmap_data):
        super().__init__()
        self.setStyleSheet("background-color: black;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_image = QLabel(self)
        self.lbl_image.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_image)
        
        self.pixmap = pixmap_data
        if self.pixmap.isNull():
            self.lbl_image.setText("FATAL SYSTEM ERROR")
            self.lbl_image.setStyleSheet("color: white; font-size: 60px; font-family: Consolas;")
        else:
            self.lbl_image.setPixmap(self.pixmap)

    def resizeEvent(self, event):
        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.FastTransformation)
            self.lbl_image.setPixmap(scaled)
        super().resizeEvent(event)


class PasswordPage(QWidget):
    verified = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet("QWidget { background-color: #000; }")
        outer_layout = QHBoxLayout(self)
        container = QWidget()
        container.setFixedWidth(450)
        inner_layout = QVBoxLayout(container)
        inner_layout.setSpacing(20)
        
        outer_layout.addStretch()
        outer_layout.addWidget(container)
        outer_layout.addStretch()

        self.lbl = QLabel("⚠️ \n请输入开发者主密钥：")
        self.lbl.setStyleSheet("color: #00ffcc; font-size: 22px; font-weight: bold; border: none;")
        self.lbl.setAlignment(Qt.AlignCenter)

        self.input_pwd = QLineEdit()
        self.input_pwd.setStyleSheet("background-color: #111; color: #fff; border: 2px solid #00ffcc; padding: 15px; font-size: 20px; border-radius: 5px;")
        self.input_pwd.setPlaceholderText("Master Key...")
        self.input_pwd.setEchoMode(QLineEdit.Password)
        self.input_pwd.returnPressed.connect(self.check_pwd)

        inner_layout.addWidget(self.lbl)
        inner_layout.addWidget(self.input_pwd)

    def check_pwd(self):
        text = self.input_pwd.text().replace(" ", "").strip()
        if text == "一键三连":
            self.verified.emit()
        else:
            self.input_pwd.clear()
            self.lbl.setText("⚠️ 拒绝访问，密钥校验失败！")

    def reset_focus(self):
        self.input_pwd.setFocus()


class FakeVirusWindow(QMainWindow):
    def __init__(self, video_path, pixmap_data):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(Qt.BlankCursor)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.page_video = VideoPage(video_path)
        self.page_math = MathPage()
        self.page_bsod = BSODPage(pixmap_data)
        self.page_pwd = PasswordPage()

        self.stack.addWidget(self.page_video)
        self.stack.addWidget(self.page_math)
        self.stack.addWidget(self.page_bsod)
        self.stack.addWidget(self.page_pwd)

        self.page_math.solved.connect(self.safe_quit)
        self.page_math.failed.connect(self.show_bsod)
        self.page_pwd.verified.connect(self.safe_quit)

        self.key_buffer = ""

    def keyPressEvent(self, event):
        text = event.text()
        if text:
            self.key_buffer += text
            if len(self.key_buffer) > 20:
                self.key_buffer = self.key_buffer[-20:]
            if "666" in self.key_buffer:
                self.key_buffer = ""
                if self.stack.currentIndex() != 3:
                    self.show_password()

        if event.key() == Qt.Key_Escape:
            if self.stack.currentIndex() == 0:
                self.page_video.pause()
                self.stack.setCurrentIndex(1)
                self.setCursor(Qt.ArrowCursor)
                self.page_math.reset_focus()
            event.accept()
        else:
            super().keyPressEvent(event)

    def show_bsod(self):
        self.stack.setCurrentIndex(2)
        self.setCursor(Qt.BlankCursor)

    def show_password(self):
        self.page_video.pause()
        self.stack.setCurrentIndex(3)
        self.setCursor(Qt.ArrowCursor)
        self.page_pwd.reset_focus()

    def safe_quit(self):
        self.page_video.player.stop()
        self.hide()
        if TEMP_VIDEO_PATH and os.path.exists(TEMP_VIDEO_PATH):
            try:
                os.remove(TEMP_VIDEO_PATH)
            except:
                pass
        QTimer.singleShot(100, lambda: os._exit(0))



if __name__ == "__main__":
    disable_cmd_close_button()
    os.system("title Windows PowerShell")
    os.system("color 0a")
    
    print("Microsoft Windows [Version 10.0.19045.3803]")
    print("(c) Microsoft Corporation. All rights reserved.\n")
    
    time.sleep(0.5)
    print("C:\\Windows\\System32> bcdedit /set {default} recoveryenabled No")
    time.sleep(0.6)
    print("The operation completed successfully.\n")

    time.sleep(0.5)
    print("C:\\Windows\\System32> vssadmin delete shadows /all /quiet")
    time.sleep(0.8)
    print("Error: No items found that satisfy the query.\n")

    time.sleep(0.5)
    print("C:\\Windows\\System32> certutil -decode payload.b64 core.py")
    time.sleep(0.9)
    print("CertUtil: -decode command completed successfully.\n")

    time.sleep(0.6)
    print("C:\\Windows\\System32> powershell -ep bypass -c \".\\core.py\"")
    time.sleep(0.8)
    
    print("[*] Initializing payload environment...")
    time.sleep(0.4)
    print("[*] Allocating virtual memory at 0x00007FFA3C2D0000")
    time.sleep(0.4)
    print("[!] API Hooking: ntdll.dll, kernel32.dll, user32.dll")
    time.sleep(0.5)
    print("[*] Generating AES-256 encryption keys...")
    time.sleep(0.4)
    print("[*] Key hash: 7b3a9f2c8d1e4b5a6f7c8d9e0a1b2c3d4e5f6a7b8c9d0e1f")
    time.sleep(0.6)
    print("[!] Bypassing Windows Defender real-time protection... [SUCCESS]")
    time.sleep(0.5)
    print("[*] Deploying display driver hook...")
    time.sleep(0.6)
    print("[*] Starting encryption engine...\n")
    time.sleep(0.8)

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)


    if getattr(sys, 'frozen', False):
        # 如果是 exe 运行，获取 exe 所在的绝对路径
        base = os.path.dirname(sys.executable)
    else:

        base = os.path.dirname(os.path.abspath(__file__))
    zip_path = None
    valid_exts = ['.sys', '.ino', '.zip', '.7z', '.dat', '.bin', '.rar']
    
    for file in os.listdir(base):
        if any(file.lower().endswith(ext) for ext in valid_exts) and file != "core.py" and file != "core.exe":
            zip_path = os.path.join(base, file)
            break
            
    if not zip_path:
        print(f"\n[FATAL] System cannot find the specified resource package in {base}")
        time.sleep(3)
        sys.exit(1)

    pixmap_data = QPixmap()

    try:
        with pyzipper.AESZipFile(zip_path, 'r') as zf:
            zf.setpassword(b"bilibili")
            
            img_list = [name for name in zf.namelist() if name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            if img_list:
                random_img = random.choice(img_list)
                img_bytes = zf.read(random_img)
                pixmap_data.loadFromData(img_bytes)
            
            video_list = [name for name in zf.namelist() if name.lower().endswith('.mp4')]
            if not video_list:
                raise FileNotFoundError("Resource Error: NO_MP4_FILE_FOUND")
            
            video_data = zf.read(video_list[0])
            if len(video_data) == 0:
                raise ValueError("Resource Error: EMPTY_VIDEO_DATA")
                
            temp_fd, TEMP_VIDEO_PATH = tempfile.mkstemp(suffix=".mp4")
            with os.fdopen(temp_fd, 'wb') as f:
                f.write(video_data)
                
    except Exception as e:
        print("\n[FATAL] Unhandled exception in native code.")
        time.sleep(2)
        print("[ERROR] Exception thrown at 0x00007FFA3C2D0000 (ntdll.dll) in core.py: 0xC0000005: Access violation reading location 0x0000000000000000.")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(1)

    print("[SYSTEM] Payload execution complete. Encryption successfully deployed.")
    time.sleep(0.6)
    print("[SYSTEM] Press ESC to initiate decryption protocol.\n")
    
    win = FakeVirusWindow(TEMP_VIDEO_PATH, pixmap_data)
    win.showFullScreen()
    
    sys.exit(app.exec())