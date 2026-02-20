# Flet YouTube Downloader (Android & Windows)

An advanced YouTube downloader application built with **Python** and **Flet**, designed to work seamlessly on both Windows and Android devices. This project utilizes **GitHub Actions** to automate the build process and generate an APK file for mobile use.

## 🚀 Features
* **Format Selection**: Download content as high-quality Video (MP4) or extract Audio (MP3).
* **Resolution Control**: Supports multiple resolutions ranging from **144p** to **4K (2160p)**.
* **High-Bitrate Audio**: Extract audio with bitrates up to **320 kbps**.
* **Integrated FFmpeg**: Includes `flet-ffmpeg` support for high-resolution merging and audio encoding on Android.
* **Smart Logging**: Real-time progress updates and status logs during the download process.
* **RTL Support**: Full Arabic language support with Right-to-Left (RTL) interface.

## 🛠️ Technology Stack
* **Language**: Python 3.10.
* **UI Framework**: Flet (v0.23.2).
* **Engine**: yt-dlp.
* **Automation**: GitHub Actions (CI/CD) for APK building.

## 📱 How to Get the Android App (APK)
You don't need to install Flutter or Android Studio. This repository is configured to build the app automatically:
1. Fork or push your code to this repository.
2. Navigate to the **"Actions"** tab on GitHub.
3. Select the latest **"Build Mobile App"** workflow run.
4. Download the **"YouTube-Downloader-APK"** artifact from the bottom of the page.
5. Install the APK on your Android device (ensure you grant storage permissions in app settings).

## 📂 Project Structure
```text
Youtube_Downloader/
├── .github/workflows/
│   └── build.yml          # CI/CD configuration for Android Build
├── main.py                # Core application logic
└── requirements.txt       # Project dependencies