# 🔥 WiFire – Automated Wi-Fi Attack Tool

WiFire is a blazing-fast toolkit for Wi-Fi auditing and pentesting — designed for **CTFs, ethical hackers, and beginners**.  
No advanced Linux skills needed — everything installs and runs with a few simple commands!

## ✨ Features
- 🔍 **Automatic Wi-Fi scanning**
- 🎯 **Smart target/client detection**
- ☠️ **Deauthentication** to force handshake
- 📶 **Live handshake capture**
- 🔑 **Real-time password cracking**
- 🎨 Cool banners & animations
- 💡 Installs all dependencies for you!

---

## 🖥️ Requirements
- Linux (Kali, Ubuntu, Parrot, etc)
- Wi-Fi adapter supporting monitor mode & injection
- Run as **root** (`sudo`)
- Python 3 with **venv** installed

---

## 🚀 Quick Installation

**1. Clone the tool:**  
    
    git clone https://github.com/PranitThorat/WiFire.git

    cd WiFire


**2. Create and activate a virtual environment:**  
     
      python3 -m venv env
      
      source env/bin/activate


**3. Start the attack tool (installs requirements on first run!):**  
      
      sudo python3 WiFire.py


---

## 🔥 Usage

1. **Select your Wi-Fi interface**
2. **Scan starts in a new terminal, CTRL+C when you see your target**
3. **Pick a target**
4. **WiFire launches deauth attacks and captures the handshake**
5. **If handshake is captured, it cracks the password LIVE**
6. **When done, network will be restored automatically!**

---

## 📝 Notes
- WiFire uses `airmon-ng check kill` to stop network manager for attacks  
- At the end (or if you CTRL+C), normal Wi-Fi is restored  
- **Never** attack networks you don’t own or don’t have permission to test

---

## ⚠️ Legal

For **educational use only**.  
Unauthorized Wi-Fi hacking is illegal.

---

Made with ❤️ for learning and fun.

