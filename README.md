# MasterPi Control Core (SCADA Runtime System)

This project is the core control system of a modular SCADA-like architecture built on Raspberry Pi.

It represents the **hardware control layer (MasterPi)** responsible for system execution, safety mechanisms, and real-time device management.

---

## 🧠 Overview

The system is designed as part of a dual-architecture:

- **RemotePi (HMI Interface)** → User interface & command input  
- **MasterPi (Control Core)** → Hardware execution & system logic  

This repository contains the **MasterPi runtime**, which processes commands, manages devices, and ensures safe operation.

---

## 🚀 Features

- Real-time hardware control and command execution  
- Safety system with rule-based control blocking  
- Fault detection and system state management  
- Modular architecture for scalability  
- Designed for embedded & industrial environments  

---

## ⚙️ System Responsibilities

MasterPi handles:

- Processing incoming control commands (via MQTT or internal pipeline)  
- Executing hardware-level operations  
- Monitoring system state and safety conditions  
- Preventing unsafe actions using defined safety rules  
- Logging system events and snapshots for traceability  

---

## 🏗️ Architecture

```text
[ RemotePi (HMI) ]
        ↓
   MQTT / Command Pipeline
        ↓
[ MasterPi Control Core ]
        ↓
[ Hardware / Devices ]
```

---

## 🛠️ Technologies Used

- Python  
- Raspberry Pi  
- MQTT (paho-mqtt)  
- Custom runtime control architecture  

---

## 📂 Project Structure

- `masterpi/` → core control system  
- `masterpi_hardware_runtime_stack.py` → main runtime logic  

---

## 🎯 Purpose

This project was developed to simulate a real-world industrial control system using SCADA principles.

It focuses on:

- Safe system execution  
- Real-time responsiveness  
- Modular and scalable design  

---

## 🔗 Related Project

This system works together with the HMI interface:

👉 RemotePi (User Interface Layer)

---

## 👤 Author

Emre Miraç Çakır
