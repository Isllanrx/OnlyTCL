# Step-by-Step Guide: Optimization and App Setup for TCL Smart TV

This guide provides end-to-end instructions for installing the optimized application suite on compatible TCL Smart TVs.

---

## 1. Prerequisites

1. TCL Smart TV connected to the same Wi-Fi or Ethernet network as your computer.
2. PC running Windows, macOS, or Linux.
3. Android Debug Bridge (ADB) installed on your computer.

---

## 2. Enabling Developer Options and USB Debugging on the TV

1. On your TV remote, open **Settings** (gear icon).
2. Navigate to **Device Preferences** (or **System**) -> **About**.
3. Scroll to **Build Number** (or **OS Build**).
4. Press the **OK / Center** button on your remote **7 consecutive times** until the message appears: *"You are now a developer!"*.
5. Return to the previous screen and open the new **Developer Options** menu.
6. Enable **USB Debugging**.
7. Confirm with **OK** on the prompt dialog.

---

## 3. Connecting via ADB over Local Network

1. On the TV, go to **Settings** -> **Network & Internet** -> select your connected network.
2. Note the **IPv4 Address** (e.g., `192.168.1.150`).
3. On your computer terminal, run:
   ```bash
   adb connect <TV_IP_ADDRESS>:5555
   ```
4. Look at the TV screen. When prompted with *"Allow USB debugging?"*, check *"Always allow from this computer"* and select **Allow**.
5. Verify connection:
   ```bash
   adb devices
   ```

---

## 4. System Debloating (Recommended)

To disable 31 background services and free up to 400 MB of RAM:

* **Windows:** Run `system\debloat\tv_debloat.bat`.
* **Linux / macOS:** Run `./system/debloat/tv_debloat.sh`.

*(To revert debloating in the future, run `system/debloat/tv_restore.sh`).*

---

## 5. Installing the Application Suite

1. Download all 5 APKs from the official release:
   **https://github.com/Isllanrx/OnlyTCL/releases/tag/v1.0.0**
2. Place them in an `apks` directory at the project root.
3. Run the automated installer:
   * **Windows:** `scripts\install_all.bat`
   * **Linux / macOS:** `./scripts/install_all.sh`

The script automatically handles package installation, permission grants (`WRITE_SECURE_SETTINGS`, microphone, accessibility), and Ahead-of-Time compilation (`dex2oat speed`).

---

## 6. Pairing an Xbox Wireless Controller via Bluetooth

1. Put your Xbox controller into pairing mode (hold the top sync button until the Xbox logo flashes rapidly).
2. On your TV, navigate to **Settings** -> **Remotes & Accessories** -> **Add Accessory**.
3. Select *"Xbox Wireless Controller"* and confirm pairing.
4. Launch the installed **Xbox Game Pass** app; the controller is mapped natively.
