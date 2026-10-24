# AI-Enabled Remote Temperature Controller - Backend 🌡️🧠

This repository contains the backend infrastructure for a smart environmental monitoring and fan control system. Built with **Python** and **FastAPI**, it is designed to ingest sensor telemetry, calculate intelligent cooling responses, and host a conversational AI assistant capable of reasoning about the room's conditions.

While this system is designed to eventually connect to an Arduino hardware unit and a React Native frontend, this repository focuses strictly on the core API, database models, and artificial intelligence logic.

### 🌟 Key Features
* **Robust REST API:** Built with FastAPI to handle telemetry ingestion, fan state evaluation, and system reporting
* **Dynamic Fan Logic:** Automatically calculates fan on/off states and proportional fan speeds based on current temperatures. It even features a humidity-adjusted threshold to activate cooling earlier in stuffy environments.
* **Predictive Trend Analytics:** Calculates the current rate of temperature change (°C/min) from recent database readings to predict future temperatures and estimate when target temperatures will be reache.
* **Tool-Augmented AI Assistant:** Integrates the **Groq API** to host "Hatsune Devgn", a conversational AI. The AI is equipped with specific function-calling tools to securely query the PostgreSQL database for real-time status, predictions, and reports without hallucinating data.
* **Scope Gate Security:** Uses a dual-model LLM architecture. A lightweight model pre-filters user messages to block off-topic requests before they ever reach the main assistant or trigger database queries.
* **Critical Event Alerts:** Dedicated polling endpoints that monitor for dangerous temperature spikes and can trigger local server-side audio alerts.

### 🛠️ Tech Stack
* **Framework:** Python, FastAPI, Uvicorn
* **Database:** PostgreSQL, SQLAlchemy (ORM), Psycopg
* **Data Validation:** Pydantic
* **AI Integration:** Groq API (LLM Tool Calling / Function Execution)
