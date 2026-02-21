import flet as ft
import yt_dlp
import os
import threading
import sys
import re
from pathlib import Path



# --- دالة الوصول للملفات المدمجة داخل الـ EXE ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# --- كلاس ذكي لربط عمليات الـ Backend بالسجل الخاص بك ---
class SmartLogger:
    def __init__(self, app):
        self.app = app

    def debug(self, msg):
        # التقاط بداية تحميل ملف جديد في القائمة ليعرف المستخدم أين وصل
        if "[download] Downloading item" in msg:
            match = re.search(r"item (\d+) of (\d+)", msg)
            if match:
                self.app.log_message(
                    f"📥 بدء معالجة الملف رقم ({match.group(1)} من {match.group(2)})..."
                )
        # التقاط اسم الملف الجاري تحميله حالياً
        elif "[download] Destination:" in msg:
            filename = os.path.basename(msg.split("Destination: ")[1])
            self.app.log_message(f"📝 جاري حفظ: {filename}")

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class YouTubeDownloader:
    def __init__(self, page):
        self.page = page
        self.downloading = False

        # 1. طلب صلاحيات التخزين للأندرويد فور تشغيل التطبيق
        self.request_storage_permission()

        self.file_picker = ft.FilePicker(on_result=self.on_dialog_result)
        self.page.overlay.append(self.file_picker)

        # 2. تحديد المسار بناءً على نظام التشغيل
        if os.name == 'nt':  # ويندوز
            self.download_folder = str(Path.home() / "Downloads" / "YouTube Downloads")
        else:  # أندرويد
            self.download_folder = "/storage/emulated/0/Download/YouTube_Downloads"

        # 3. محاولة إنشاء المجلد
        try:
            if not os.path.exists(self.download_folder):
                os.makedirs(self.download_folder, exist_ok=True)
        except Exception:
            self.download_folder = "./downloads"
            os.makedirs(self.download_folder, exist_ok=True)
        self.create_ui()

    # دالة طلب الصلاحيات
    def request_storage_permission(self):
        if self.page.platform == ft.PagePlatform.ANDROID:
            # طلب صلاحية الوصول للملفات
            self.page.request_permission(ft.PermissionType.STORAGE)

    def create_ui(self):
        self.url_input = ft.TextField(
            label="رابط YouTube",
            hint_text="أدخل رابط الفيديو أو قائمة التشغيل",
            width=600,
            border_color=ft.colors.BLUE_400,
            prefix_icon=ft.icons.LINK,
            rtl=True,
        )

        # الجودات المكتوبة يدوياً كما طلبت [حذفنا "best" و "worst"]
        self.video_qualities = [
            ft.dropdown.Option("2160", "4K (2160p)"),
            ft.dropdown.Option("1440", "2K (1440p)"),
            ft.dropdown.Option("1080", "1080p (Full HD)"),
            ft.dropdown.Option("720", "720p (HD)"),
            ft.dropdown.Option("480", "480p"),
            ft.dropdown.Option("360", "360p"),
            ft.dropdown.Option("240", "240p"),
            ft.dropdown.Option("144", "144p"),
        ]

        self.audio_qualities = [
            ft.dropdown.Option("320", "320 kbps (ممتازة)"),
            ft.dropdown.Option("192", "192 kbps (عالية)"),
            ft.dropdown.Option("128", "128 kbps (متوسطة)"),
        ]

        self.quality_selector = ft.Dropdown(
            label="الجودة", width=250, value="1080", options=self.video_qualities
        )

        def on_format_change(e):
            if self.format_selector.value == "audio":
                self.quality_selector.options = self.audio_qualities
                self.quality_selector.value = "192"
                self.log_message("🎵 تم تبديل القائمة لجودات الصوت")
            else:
                self.quality_selector.options = self.video_qualities
                self.quality_selector.value = "1080"
                self.log_message("🎥 تم تبديل القائمة لجودات الفيديو")
            self.page.update()

        self.format_selector = ft.RadioGroup(
            content=ft.Column(
                [
                    ft.Radio(value="video", label="فيديو (فيديو + صوت)"),
                    ft.Radio(value="audio", label="صوت فقط (MP3)"),
                ]
            ),
            value="video",
            on_change=on_format_change,
        )

        self.folder_path = ft.Text(
            f"المجلد: {self.download_folder}", size=14, color=ft.colors.GREY_700
        )
        self.folder_selector = ft.ElevatedButton(
            "اختر مجلد التحميل",
            icon=ft.icons.FOLDER_OPEN,
            on_click=lambda _: self.file_picker.get_directory_path(),
        )

        self.progress_bar = ft.ProgressBar(
            width=400, value=0, visible=False, color=ft.colors.BLUE_400
        )
        self.progress_text = ft.Text("", size=14)

        self.download_button = ft.ElevatedButton(
            "بدء التحميل",
            icon=ft.icons.DOWNLOAD,
            on_click=self.start_download,
            style=ft.ButtonStyle(bgcolor=ft.colors.BLUE_400, color=ft.colors.WHITE),
            width=200,
        )

        self.status_text = ft.Text("", size=16, weight=ft.FontWeight.BOLD, rtl=True)
        self.log_text = ft.Text("", size=12, selectable=True, rtl=True)
        self.log_container = ft.Container(
            content=ft.Column([self.log_text], scroll=ft.ScrollMode.ALWAYS),
            width=600,
            height=200,
            padding=10,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5,
        )

        self.clear_log_button = ft.TextButton(
            "مسح السجل", icon=ft.icons.CLEAR, on_click=lambda _: self.clear_log()
        )

    def on_dialog_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.download_folder = e.path
            self.folder_path.value = f"المجلد: {self.download_folder}"
            self.page.update()

    def log_message(self, message):
        self.log_text.value = f"{message}\n{self.log_text.value}"
        self.page.update()

    def update_progress(self, d):
        if d["status"] == "downloading":
            try:
                if d.get("total_bytes"):
                    percent = d["downloaded_bytes"] / d["total_bytes"]
                    self.progress_bar.value = percent
                    self.progress_text.value = f"{percent:.1%}"
                else:
                    self.progress_text.value = f"{d.get('_percent_str', '0%')}"
                self.page.update()
            except:
                pass
        elif d["status"] == "finished":
            self.progress_bar.value = 1
            self.page.update()

    def download_media(self):
        try:
            url = self.url_input.value.strip()
            if not url:
                self.log_message("⚠️ الرجاء إدخال رابط")
                return

            self.status_text.value = "⏳ جاري البدء..."
            self.progress_bar.visible = True
            self.download_button.disabled = True
            self.page.update()

            if os.name == "nt":  # إذا كان ويندوز
                ffmpeg_path = resource_path("ffmpeg")
            else:  # إذا كان أندرويد
                # المكتبة ستقوم بإرجاع المسار الصحيح لملف الـ binary داخل الموبايل
                ffmpeg_path = flet_ffmpeg.get_ffmpeg_path()

            ydl_opts = {
                "ffmpeg_location": ffmpeg_path,
                # باقي الإعدادات كما هي
            }
            q = self.quality_selector.value

            ydl_opts = {
                "outtmpl": os.path.join(self.download_folder, "%(title)s.%(ext)s"),
                "progress_hooks": [self.update_progress],
                "ffmpeg_location": ffmpeg_path,
                "logger": SmartLogger(self),  # ربط السجل بالمحرك لعرض تفاصيل القائمة
                "merge_output_format": "mp4",
                "ignoreerrors": True,  # حل مشكلة الفيديوهات غير المتاحة
                "quiet": False,
            }

            if self.format_selector.value == "audio":
                ydl_opts.update(
                    {
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": q,
                            }
                        ],
                    }
                )
            else:
                # ضبط الجودة يدوياً بناءً على الارتفاع المختار
                ydl_opts["format"] = (
                    f"bestvideo[height<={q}]+bestaudio/best/best[height<={q}]"
                )

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log_message(f"🔍 تحليل الرابط: {url}")
                ydl.download([url])

            self.status_text.value = "✅ اكتمل التحميل!"
            self.log_message("✅ انتهت العملية بنجاح.")

        except Exception as e:
            self.status_text.value = "❌ فشل التحميل"
            self.log_message(f"❌ خطأ: الرابط غير صحيح أو انقطع الإنترنت.")
        finally:
            self.progress_bar.visible = False
            self.download_button.disabled = False
            self.page.update()

    def start_download(self, e):
        threading.Thread(target=self.download_media, daemon=True).start()

    def get_ui(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "YouTube Downloader",
                        size=32,
                        weight="bold",
                        color=ft.colors.BLUE_700,
                    ),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("إعدادات التحميل", size=20, weight="bold"),
                                    ft.Divider(),
                                    self.url_input,
                                    ft.Row(
                                        [
                                            ft.Column(
                                                [
                                                    ft.Text("نوع الملف:"),
                                                    self.format_selector,
                                                ],
                                                width=250,
                                            ),
                                            ft.Column(
                                                [
                                                    ft.Text("الجودة:"),
                                                    self.quality_selector,
                                                ],
                                                width=250,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                    ft.Divider(),
                                    self.folder_selector,
                                    self.folder_path,
                                    ft.Divider(),
                                    ft.Row(
                                        [
                                            self.download_button,
                                            self.progress_bar,
                                            self.progress_text,
                                        ],
                                        wrap=True,
                                    ),
                                    self.status_text,
                                ],
                                spacing=15,
                            ),
                            padding=20,
                        ),
                        width=650,
                    ),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(
                                                "سجل التحميلات", size=18, weight="bold"
                                            ),
                                            ft.Container(expand=True),
                                            self.clear_log_button,
                                        ]
                                    ),
                                    ft.Divider(),
                                    self.log_container,
                                ]
                            ),
                            padding=20,
                        ),
                        width=650,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
                scroll=ft.ScrollMode.AUTO,
            ),
            alignment=ft.alignment.center,
            expand=True,
        )

    def clear_log(self):
        self.log_text.value = ""
        self.page.update()


def main(page: ft.Page):
    page.title = "YouTube Downloader Pro"
    page.window.width = 750
    page.window.height = 900
    page.rtl = True
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    downloader = YouTubeDownloader(page)
    page.add(downloader.get_ui())
    downloader.log_message("مرحبًا! النظام جاهز للتحميل.")


if __name__ == "__main__":
    ft.app(target=main)
