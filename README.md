# 🌾 Smart Kisan AI — Digital Agriculture Platform

Smart Kisan AI is a full-stack, AI-powered agricultural platform built for Indian farmers.
It provides real-time weather forecasts, AI crop disease diagnosis, agronomy advisory, yield prediction, and a farmer marketplace — all in one place.

---

## 🚀 Features

| Feature | Description |
|---|---|
| 🔬 Crop Diagnostics | Camera/gallery upload with two-stage AI disease detection (Stage A: validation, Stage B: diagnosis) |
| 🤖 AgriExpert Chatbot | Context-aware farming assistant with Hindi, English & Marathi support |
| 🌤️ Weather Forecast | 7-day agricultural forecast via Open-Meteo API with GPS auto-detection |
| 📈 Yield Prediction | ML-driven crop yield estimation based on N, P, K, pH, rainfall & season |
| 🛒 Marketplace | Farmer-to-buyer listings, buy requests & regional mandi rate tracking |
| 📋 Crop Calendar | Personalized sowing & harvesting schedule management |
| 🏛️ Govt. Schemes | Browse and apply for agriculture-related government schemes |
| 👥 Community Forum | Farmer discussion board and knowledge sharing |

---

## 🛠️ Tech Stack

**Frontend:** React 18 · Vite · Lucide Icons · PWA  
**Backend (Node.js):** Express.js · MongoDB · Redis · JWT · Anthropic SDK · OpenAI SDK  
**Backend (Python):** FastAPI · PyTorch · Google Gemini AI · SQLite / SQLAlchemy  
**APIs:** Open-Meteo · Nominatim Reverse Geocoding · Razorpay Payments  

---

## 📦 Getting Started

### Prerequisites
- Node.js v18+
- Python 3.10+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Krishna8208863439/Smart-Kisan-FInal.git
cd Smart-Kisan-FInal
```

### 2. Backend — Node.js
```bash
cd backend
npm install
cp .env.example .env        # Add your API keys
node server.js              # Runs on http://localhost:5000
```

### 3. Backend — Python (AI Services)
```bash
cd backend_python
pip install -r requirements.txt
uvicorn app:app --reload    # Runs on http://localhost:8000
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev                 # Runs on http://localhost:5173
```

---

## 🌐 Deployment

Deploy the full stack to **PythonAnywhere** in one command:
```bash
python deploy_all_to_pythonanywhere.py
```

Or use **Docker**:
```bash
docker-compose up --build
```

---

## 📁 Project Structure

```
Smart-Kisan/
├── backend/          # Node.js Express API
├── backend_python/   # FastAPI Python AI services
├── frontend/         # React + Vite PWA
├── datasets/         # ML training datasets
├── docker/           # Docker configs
└── nginx/            # Nginx reverse proxy config
```

---

## 🔑 Environment Variables

Create a `.env` file inside `backend/` using `.env.example` as reference:

```env
MONGODB_URI=your_mongodb_uri
JWT_SECRET=your_jwt_secret
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret
```

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 🙌 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

> Built with ❤️ for Indian Farmers 🇮🇳
