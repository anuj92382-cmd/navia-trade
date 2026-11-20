# 🚀 Navia Algorithmic Trading Framework (Python)

यह एक संपूर्ण, मॉड्यूलर और प्रोडक्शन-रेडी **Python Algo Trading Framework** है, जिसे [Navia Trading API](https://navia.co.in/api) के साथ अल्गो ट्रेडिंग (Algorithmic Trading) करने के लिए बनाया गया है।

---

## 📌 Navia API की मुख्य विशेषताएं (Key Features)

* **₹0 ब्रोकरेज (Zero Brokerage):** Navia के API ट्रेड्स पर लाइफटाइम ₹0 ब्रोकरेज मॉडल लागू है।
* **REST & WebSocket Architecture:** ऑर्डर मैनेजमेंट के लिए फास्ट REST HTTP एंडपॉइंट्स और रियल-टाइम टिक्स के लिए WebSocket स्ट्रीमिंग।
* **हाई थ्रूपुट (Throughput):** 10 ऑर्डर्स/सेकंड और 3,000 ऑर्डर्स/दिन तक की क्षमता।
* **मल्टी-एसेट सपोर्ट:** Equity (NSE/BSE), F&O (Futures & Options), और Commodities (MCX)।
* **पेपर ट्रेडिंग (Paper Trading Mode):** बिना असली पैसे जोखिम में डाले स्ट्रैटेजी को टेस्ट करने के लिए वर्चुअल सिमुलेशन इंजन।

---

## 📁 प्रोजेक्ट स्ट्रक्चर (Project Structure)

```text
d:\navia-trade\
├── navia/
│   ├── __init__.py
│   ├── constants.py          # एक्सचेंज, ऑर्डर प्रकार और एंडपॉइंट कॉन्सटेंट्स
│   ├── client.py             # Navia REST API Client (Auth, Orders, Portfolio)
│   └── websocket_client.py   # रियल-टाइम मार्केट टिक स्ट्रीमिंग और सिम्युलेटर
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py      # बेस क्लास (रिस्क मैनेजमेंट, SL, टारगेट, P&L)
│   ├── ma_crossover.py       # 9/21 Moving Average Crossover स्ट्रैटेजी
│   └── rsi_strategy.py       # RSI Momentum Scalping स्ट्रैटेजी
├── config.py                 # एनवायरनमेंट सेटिंग्स लोडर
├── .env.example              # क्रेडेंशियल्स कॉन्फ़िगरेशन टेम्पलेट
├── test_connection.py        # कनेक्शन और क्रेडेंशियल्स टेस्ट स्क्रिप्ट
├── main.py                   # अल्गो ट्रेडिंग रनर स्क्रिप्ट
├── requirements.txt          # आवश्यक Python लाइब्रेरीज़
└── README.md                 # डॉक्यूमेंटेशन
```

---

## ⚙️ 1. सेटअप और इंस्टॉलेशन (Setup & Installation)

### Python लाइब्रेरीज़ चेक करें
यह प्रोजेक्ट `requests`, `websocket-client`, और `pandas` का उपयोग करता है:
```bash
pip install -r requirements.txt
```

### क्रेडेंशियल्स कॉन्फ़िगर करें
`.env.example` को कॉपी करके `.env` फाइल बनाएं:
```bash
cp .env.example .env
```

अब `.env` फाइल में अपनी डिटेल्स दर्ज करें:
```env
# Navia Login Credentials
NAVIA_CLIENT_CODE=YOUR_CLIENT_UCC
NAVIA_PASSWORD=YOUR_LOGIN_PASSWORD
NAVIA_API_KEY=YOUR_API_KEY
NAVIA_AUTH_TOKEN=DEFAULT

# सर्वर गेटवे
NAVIA_BASE_URL=https://naviaapt.navia.co.in:9003
NAVIA_WS_URL=wss://naviaapt.navia.co.in:9003/ws

# ट्रेडिंग मोड:
# true = पेपर ट्रेडिंग (सुरक्षित टेस्टिंग, कोई असली पैसा नहीं)
# false = लाइव ट्रेडिंग (असली पैसा)
PAPER_TRADING=true

# डिफ़ॉल्ट रिस्क सेटिंग्स
DEFAULT_SYMBOL=RELIANCE-EQ
DEFAULT_EXCHANGE=NSE
DEFAULT_QUANTITY=1
STOP_LOSS_PCT=1.0        # 1.0% स्टॉप लॉस
TAKE_PROFIT_PCT=2.0      # 2.0% टारगेट प्रॉफिट
MAX_DAILY_LOSS=5000.0    # ₹5,000 अधिकतम दैनिक नुकसान सीमा
```

---

## 🧪 2. कनेक्शन टेस्ट करना (Test Connection)

सबसे पहले यह सुनिश्चित करने के लिए कि सब कुछ ठीक से काम कर रहा है, टेस्ट स्क्रिप्ट चलाएं:

```bash
python test_connection.py
```

* **Paper Trading Mode में:** यह वर्चुअल ऑर्डर, पोजीशन्स और लिमिट्स को तुरंत टेस्ट करेगा।
* **Live Mode में:** यह Navia सर्वर को `SendOTP` भेजेगा और आपका सत्र सत्यापित करेगा।

---

## 📈 3. अल्गो ट्रेडिंग स्ट्रैटेजी रन करना (Running Strategies)

### 🔹 रणनीति 1: Moving Average Crossover (EMA 9 & 21)
यह स्ट्रैटेजी 9-पीरियड और 21-पीरियड EMA का उपयोग करती है:
- **BUY:** जब Fast EMA (9) Slow EMA (21) को ऊपर क्रॉस करता है (Golden Cross).
- **SELL:** जब Fast EMA (9) Slow EMA (21) को नीचे क्रॉस करता है (Death Cross).

```bash
# पेपर ट्रेडिंग मोड में चलाएं
python main.py --strategy ma --symbol RELIANCE-EQ --qty 1

# मार्केट बंद होने के बाद सिमुलेशन टिक के साथ टेस्ट करने के लिए:
python main.py --strategy ma --simulate-feed
```

---

### 🔹 रणनीति 2: RSI Scalper (14 Period)
यह स्ट्रैटेजी ओवरसोल्ड और ओवरबॉट ज़ोन पर आधारित है:
- **BUY:** जब RSI 30 (Oversold) से ऊपर रिकवर होता है।
- **SELL:** जब RSI 70 (Overbought) से नीचे गिरता है।

```bash
python main.py --strategy rsi --symbol INFY-EQ --qty 2 --simulate-feed
```

---

### 🔴 लाइव ट्रेडिंग (Real Money Live Mode)
जब आप अपनी स्ट्रैटेजी से पूरी तरह संतुष्ट हों और असली मार्केट में ट्रेड करना चाहें:
```bash
python main.py --strategy ma --symbol RELIANCE-EQ --qty 1 --live
```
*(नोट: लाइव ट्रेडिंग के लिए `.env` में `NAVIA_CLIENT_CODE` और पासवर्ड होना अनिवार्य है)*

---

## 🛡️ रिस्क मैनेजमेंट और सेफ़्टी फीचर्स (Risk Controls)

1. **ऑटो स्टॉप लॉस (Stop Loss):** डिफ़ॉल्ट 1.0% नुकसान होने पर पोजीशन अपने आप कट जाती है।
2. **प्रॉफिट टारगेट (Take Profit):** डिफ़ॉल्ट 2.0% लाभ होने पर पोजीशन ऑटोमैटिकली स्क्वायर-ऑफ हो जाती है।
3. **मैक्स डेली लॉस सर्किट ब्रेकर:** यदि दिन का कुल नुकसान ₹5,000 से अधिक होता है, तो अल्गो ट्रेडिंग तुरंत रुक जाती है।
4. **सुरक्षित निकास (Graceful Shutdown):** जब आप टर्मिनल में `Ctrl + C` दबाते हैं, तो अल्गो खुली हुई पोजीशन्स को ऑटो-स्क्वेयरऑफ करके सुरक्षित बंद होता है।

---

## 📡 Navia API एंडपॉइंट्स रेफरेंस (Endpoints Reference)

| Activity Name | Method | विवरण |
|---|---|---|
| `SendOTP` | POST | लॉगिन का पहला चरण (मोबाइल/ईमेल पर OTP भेजना) |
| `VerifyOTP` | POST | OTP सत्यापित करके AuthToken प्राप्त करना |
| `PlaceOrder` | POST | नया ऑर्डर लगाना (Equity, F&O, MCX) |
| `ModifyOrder` | POST | पेंडिंग ऑर्डर में मूल्य या मात्रा बदलना |
| `CancelOrder` | POST | पेंडिंग ऑर्डर रद्द करना |
| `OrderBook` | POST/GET | आज के सभी ऑर्डर्स की स्थिति देखना |
| `Positions` | POST/GET | खुली हुई इंट्राडे और नेट पोजीशन्स देखना |
| `Holdings` | POST/GET | लॉन्ग-टर्म डिमैट होल्डिंग्स प्राप्त करना |
| `Limits` | POST/GET | उपलब्ध फंड्स और मार्जिन लिमिट्स देखना |
| `GetQuote` | POST | किसी सिंबल का लाइव मार्केट स्नैपशॉट लेना |
