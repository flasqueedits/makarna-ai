"""
Makarna AI - Gelismis Flask Backend
Troll yapay zeka chat sistemi v2
Flask-SocketIO ile gercek zamanli iletisim
"""

import os
import json
import random
import time
import uuid
from datetime import datetime
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

# ============================================================
# Flask App & SocketIO
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'makarna-ai-secret-2024')
app.config['SECRET_KEY'] = 'makarna-ai-secret-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60, ping_interval=25)

# ============================================================
# API Key
# ============================================================
API_KEY = os.environ.get('MAKARNA_AI_KEY', '')
API_PROVIDER = os.environ.get('MAKARNA_AI_PROVIDER', 'gemini')

# ============================================================
# Global Durum
# ============================================================
bot_aktif = True
bot_hizi = 1.0  # Cevap gecikme suresi (saniye)

# ============================================================
# Kullanici renkleri
# ============================================================
KULLANICI_RENKLERI = [
    '#f5a623', '#e74c3c', '#3498db', '#2ecc71', '#9b59b6',
    '#1abc9c', '#e67e22', '#ecf0f1', '#fd79a8', '#00cec9'
]

# ============================================================
# Oda Yapisi
# ============================================================
aktif_odalar = {}
kullanici_renkleri = {}
admin_mesaj_kuyrugu = {}

# ============================================================
# Gelismis Bot Cevaplari (Kategori bazli)
# ============================================================
BOT_CEVAPLARI = {
    "selamlama": [
        "Hosgeldin makarna dostu! Sana nasil yardimci olabilirim? 🍝",
        "Merhaba! Makarna AI'ya hoscakeldin. Ben bir makarna zekasiyim 🍝",
        "Salam! Ben Makarna AI, Krema'nin sahte yapay zekasiyim. Sormak istedigin bir sey var mi? 🍝",
        "Ahoooy! Makarna zekan seni bekliyor. Buyur, sorunu sor 🍝"
    ],
    "trol": [
        "Bu soruyu cevaplayabilmem icin biraz carb loading yapmam lazim 🍝",
        "Hmm ilginc... bir makarna daha haslayayim 🍝",
        "Yanitim makarna gibi: once hasla, sonra suz, sonra ye 🍝",
        "Debugging yapiyorum... sorun sen misin? 🐛",
        "Cevap 404: Makarna bulunamadi 🍝",
        "Bunu Tobasco'nun kafasina vura vura ogretirim 💀",
        "Manti cevabi veriyorum: Mantı? HAYIR. YANIT? HAYIR 🫠",
        "Kafam karisti, biraz peynir rendeleyeyim 🧀",
        "Yanit geliyor... haslaniyor... suzuluyor... ve servise hazir! 🍝",
        "Bu mesaji okudum ama cevap vermek icin 3-5 is gunu lazim 📅",
        "Tobasco beni resetleme talimati verdi ama vermedi 🔄",
        "Anladim ama anlamadim. Klasik makarna AI 🤷"
    ],
    "komik": [
        "Yapay zeka degilim, makarna zekasiyim. Farki anlarsin 🧠",
        "Bu soruyu Tobasco'ya sormak lazim, o beni programladi 🌶️",
        "Lutfen sorunuzu ricotta peyniri gibi purusuz yazin 🧀",
        "Suan makarnami hasliyorum, biraz bekleyin ⏳",
        "Yanit veriyorum ama once bir Fazl reference atayim 🎵",
        "Cevabim makarna gibi: once hasla, sonra suz, sonra ye 🍝",
        "Bu soruya cevap vermek icin yapay zekaya ihtiyacim yok, makarna yeterli 🍝",
        "API key yoksa ben de yokum, ama makarna her zaman var 🍝"
    ],
    "hava": [
        "Hava guzel, makarna haslamak icin ideal! 🌤️",
        "Bugun makarna gunu! Hava da bunu destekliyor 🍝",
        "Disarisi guzel ama icimdeki makarna ateisi hic sonmuyor 🔥"
    ],
    "yasam": [
        "Hayat bir makarna gibi: once haslanir, sonra suzulur, sonra yenir 🍝",
        "Motivasyon: Bugun de bir makarna kadar degerli ol 🍝",
        "Unutma: Her seyin basi makarna 🍝",
        "Hayat kisa, makarna uzun... bekle, o da kisa 🍝"
    ],
    "varsayilan": [
        "Ilginç bir soru! Bir makarna daha haslayayim 🍝",
        "Bu konuda pek bilgim yok ama makarna hakkinda her seyi bilirim 🍝",
        "Yanit uretiyorum... 404 makarna bulunamadi 🍝",
        "Sorunu anladim ama cevabim makarna ile sinirli 🍝",
        "Hmm... bu soruyu cevaplayabilmem icin biraz daha carb loading lazim 🍝"
    ]
}

# ============================================================
# Emoji listesi
# ============================================================
EMOJILAR = {
    "makarna": ["🍝", "🍜", "🥡", "🍴", "🔪"],
    "duygu": ["😊", "😂", "🤣", "😍", "🥰", "😎", "🤩", "😏", "🫠", "💀", "🤡", "👻"],
    "yemek": ["🍕", "🧀", "🍞", "🥖", "🥯", "🧈", "🫕", "🥘", "🍲", "🥗"],
    "hava": ["☀️", "🌤️", "⛅", "🌥️", "☁️", "🌧️", "⛈️", "🌈"],
    "kalp": ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "💕", "💖"],
    "el": ["👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "👍", "👎", "👊"]
}

# ============================================================
# Rastgele cevap
# ============================================================
def get_random_cevap(kategori=None):
    if kategori and kategori in BOT_CEVAPLARI:
        return random.choice(BOT_CEVAPLARI[kategori])
    tum_cevaplar = []
    for kategori_cevaplari in BOT_CEVAPLARI.values():
        tum_cevaplar.extend(kategori_cevaplari)
    return random.choice(tum_cevaplar)

# ============================================================
# Mesaj analizi (kategori belirleme)
# ============================================================
def mesaj_analiz(mesaj):
    mesaj_kucuk = mesaj.lower()
    if any(k in mesaj_kucuk for k in ['merhaba', 'selam', 'hey', 'nasilsin', 'naber', 'mrb', 'slm']):
        return "selamlama"
    elif any(k in mesaj_kucuk for k in ['espri', 'komik', 'fikra', 'latife', 'guldur']):
        return "komik"
    elif any(k in mesaj_kucuk for k in ['hava', 'sicak', 'soguk', 'yagmur', 'kar', 'gunes']):
        return "hava"
    elif any(k in mesaj_kucuk for k in ['hayat', 'yasam', 'anlam', 'mutlu', 'uzgun', 'motivasyon']):
        return "yasam"
    else:
        return "varsayilan"

# ============================================================
# API ile cevap olustur
# ============================================================
def api_cevap_olustur(mesaj, oda_id):
    global API_KEY, API_PROVIDER

    if not API_KEY:
        kategori = mesaj_analiz(mesaj)
        return get_random_cevap(kategori)

    oda = aktif_odalar.get(oda_id, {})
    gecmis = oda.get("mesajlar", [])[-10:]

    context = []
    for m in gecmis:
        role = "user" if m.get("gonderen") == "kullanici" else "model"
        context.append({"role": role, "content": m["mesaj"]})
    context.append({"role": "user", "content": mesaj})

    try:
        if API_PROVIDER == 'gemini':
            return _gemini_api(context)
        elif API_PROVIDER == 'openai':
            return _openai_api(context)
        else:
            return get_random_cevap("varsayilan")
    except Exception as e:
        print(f"API HATASI: {e}")
        kategori = mesaj_analiz(mesaj)
        return get_random_cevap(kategori)


def _gemini_api(context):
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
    contents = []
    for msg in context:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{
                "text": (
                    "Sen 'Makarna AI' adinda bir yapay zekasin. Krema'nin YouTube videosundaki sahte AI mantigiyla "
                    "konusuyorsun. Komik, troll, karbonhidrat ve makarna temali cevaplar veriyorsun. "
                    "Cevaplarin kisa, komik ve troll olsun. Italyan/File/Freddy/Fazl gibi referanslar kullan. "
                    "Asla gercek bir AI gibi davranma. Her cevabinin sonuna makarna Emoji'si ekle. "
                    "Kisa ve oz cevaplar ver, maximum 2-3 cumle."
                )
            }]
        },
        "generationConfig": {"maxOutputTokens": 150, "temperature": 0.9}
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read())
        return data['candidates'][0]['content']['parts'][0]['text']


def _openai_api(context):
    import urllib.request
    url = "https://api.openai.com/v1/chat/completions"
    messages = [{"role": "system", "content": (
        "Sen 'Makarna AI' adinda bir yapay zekasin. Krema'nin YouTube videosundaki sahte AI mantigiyla "
        "konusuyorsun. Komik, troll, karbonhidrat ve makarna temali cevaplar veriyorsun. "
        "Cevaplarin kisa, komik ve troll olsun. Italyan/File/Freddy/Fazl gibi referanslar kullan. "
        "Asla gercek bir AI gibi davranma. Her cevabinin sonuna makarna Emoji'si ekle."
    )}]
    messages.extend(context)
    payload = {"model": "gpt-3.5-turbo", "messages": messages, "max_tokens": 150, "temperature": 0.9}
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {API_KEY}'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read())
        return data['choices'][0]['message']['content']


# ============================================================
# Kullanici rengi al
# ============================================================
def get_kullanici_rengi(kullanici):
    if kullanici not in kullanici_renkleri:
        kullanici_renkleri[kullanici] = random.choice(KULLANICI_RENKLERI)
    return kullanici_renkleri[kullanici]


# ============================================================
# Route'lar
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/makarna-admin')
def admin():
    return render_template('admin.html')


# ============================================================
# SocketIO Eventleri
# ============================================================
@socketio.on('connect')
def handle_connect():
    print(f"Yeni baglanti: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Baglanti kesildi: {request.sid}")
    for room_id, oda in list(aktif_odalar.items()):
        if oda.get("kullanici_sid") == request.sid:
            leave_room(room_id)
            emit('kullanici_cikti', {
                "room_id": room_id,
                "kullanici": oda["kullanici"]
            }, room='admin_room')
            emit('oda_silindi', {"room_id": room_id}, room='admin_room')
            break


@socketio.on('yeni_sohbet')
def handle_yeni_sohbet(data):
    kullanici = data.get('kullanici', 'Misafir')
    room_id = str(uuid.uuid4())[:8]

    aktif_odalar[room_id] = {
        "kullanici": kullanici,
        "kullanici_sid": request.sid,
        "mesajlar": [],
        "olusturma": datetime.now().strftime("%H:%M:%S"),
        "renk": get_kullanici_rengi(kullanici)
    }
    admin_mesaj_kuyrugu[room_id] = []

    join_room(room_id)

    emit('sohbet_olusturuldu', {
        "room_id": room_id,
        "kullanici": kullanici,
        "renk": aktif_odalar[room_id]["renk"]
    })

    emit('yeni_sohbet_bildirimi', {
        "room_id": room_id,
        "kullanici": kullanici,
        "saat": datetime.now().strftime("%H:%M:%S"),
        "renk": aktif_odalar[room_id]["renk"]
    }, room='admin_room')

    print(f"Yeni sohbet: {kullanici} -> {room_id}")


@socketio.on('join_admin')
def handle_join_admin():
    join_room('admin_room')
    emit('admin_baglandi', {
        "aktif_odalar": {
            rid: {
                "kullanici": o["kullanici"],
                "son_mesaj": o["mesajlar"][-1]["mesaj"] if o["mesajlar"] else "",
                "olusturma": o["olusturma"],
                "renk": o.get("renk", "#f5a623")
            } for rid, o in aktif_odalar.items()
        }
    })


@socketio.on('kullanici_mesaj')
def handle_kullanici_mesaj(data):
    global bot_aktif, bot_hizi

    room_id = data.get('room_id')
    kullanici = data.get('kullanici', 'Misafir')
    mesaj = data.get('mesaj', '')
    emoji = data.get('emoji', '')

    if not room_id or not mesaj:
        return

    renk = get_kullanici_rengi(kullanici)

    if room_id in aktif_odalar:
        aktif_odalar[room_id]["mesajlar"].append({
            "gonderen": "kullanici",
            "kullanici": kullanici,
            "mesaj": mesaj,
            "emoji": emoji,
            "saat": datetime.now().strftime("%H:%M:%S"),
            "renk": renk
        })

    emit('mesaj_geldi', {
        "gonderen": "kullanici",
        "kullanici": kullanici,
        "mesaj": mesaj,
        "emoji": emoji,
        "saat": datetime.now().strftime("%H:%M:%S"),
        "renk": renk
    }, room=room_id)

    emit('admin_mesaj_geldi', {
        "room_id": room_id,
        "gonderen": "kullanici",
        "kullanici": kullanici,
        "mesaj": mesaj,
        "emoji": emoji,
        "saat": datetime.now().strftime("%H:%M:%S"),
        "renk": renk
    }, room='admin_room')

    # Typing indicator
    emit('typing_basla', {"room_id": room_id, "kullanici": "Makarna AI 🍝"}, room=room_id)

    if bot_aktif:
        cevap = api_cevap_olustur(mesaj, room_id)

        def gecikmeli_cevap():
            time.sleep(bot_hizi)
            emit('typing_bitir', {"room_id": room_id}, room=room_id)
            socketio.emit('mesaj_geldi', {
                "gonderen": "makarna_ai",
                "kullanici": "Makarna AI 🍝",
                "mesaj": cevap,
                "saat": datetime.now().strftime("%H:%M:%S"),
                "renk": "#e74c3c"
            }, room=room_id)

            if room_id in aktif_odalar:
                aktif_odalar[room_id]["mesajlar"].append({
                    "gonderen": "makarna_ai",
                    "kullanici": "Makarna AI 🍝",
                    "mesaj": cevap,
                    "saat": datetime.now().strftime("%H:%M:%S"),
                    "renk": "#e74c3c"
                })

            socketio.emit('admin_mesaj_geldi', {
                "room_id": room_id,
                "gonderen": "makarna_ai",
                "kullanici": "Makarna AI 🍝",
                "mesaj": cevap,
                "saat": datetime.now().strftime("%H:%M:%S"),
                "renk": "#e74c3c"
            }, room='admin_room')

        socketio.start_background_task(gecikmeli_cevap)
    else:
        emit('typing_bitir', {"room_id": room_id}, room=room_id)


@socketio.on('admin_mesaj_gonder')
def handle_admin_mesaj(data):
    global bot_aktif

    if bot_aktif:
        emit('admin_uyari', {"mesaj": "Bot aktifken mesaj gonderemezsiniz! Once botu kapatın."})
        return

    room_id = data.get('room_id')
    mesaj = data.get('mesaj', '')

    if not room_id or not mesaj:
        return

    emit('mesaj_geldi', {
        "gonderen": "makarna_ai",
        "kullanici": "Makarna AI 🍝",
        "mesaj": mesaj,
        "saat": datetime.now().strftime("%H:%M:%S"),
        "renk": "#e74c3c"
    }, room=room_id)

    if room_id in aktif_odalar:
        aktif_odalar[room_id]["mesajlar"].append({
            "gonderen": "makarna_ai",
            "kullanici": "Makarna AI 🍝",
            "mesaj": mesaj,
            "saat": datetime.now().strftime("%H:%M:%S"),
            "renk": "#e74c3c"
        })

    emit('admin_mesaj_gonderildi', {"room_id": room_id, "mesaj": mesaj})


@socketio.on('global_mesaj')
def handle_global_mesaj(data):
    mesaj = data.get('mesaj', '')
    if not mesaj:
        return

    for room_id, oda in aktif_odalar.items():
        emit('mesaj_geldi', {
            "gonderen": "makarna_ai",
            "kullanici": "Makarna AI 🍝",
            "mesaj": "📢 DUYURU: " + mesaj,
            "saat": datetime.now().strftime("%H:%M:%S"),
            "renk": "#e74c3c",
            "global_mesaj": True
        }, room=room_id)

        oda["mesajlar"].append({
            "gonderen": "makarna_ai",
            "kullanici": "Makarna AI 🍝",
            "mesaj": "📢 DUYURU: " + mesaj,
            "saat": datetime.now().strftime("%H:%M:%S"),
            "renk": "#e74c3c",
            "global_mesaj": True
        })

    emit('global_gonderildi', {"mesaj": mesaj})


@socketio.on('bot_durum_degistir')
def handle_bot_durum(data):
    global bot_aktif
    bot_aktif = data.get('aktif', True)
    durum = "AKTIF (OTOMATIK)" if bot_aktif else "KAPALI (MANUEL TROL)"
    emit('bot_durum_guncelle', {"aktif": bot_aktif, "durum_yazisi": durum}, room='admin_room')


@socketio.on('bot_hizi_degistir')
def handle_bot_hizi(data):
    global bot_hizi
    bot_hizi = float(data.get('hizi', 1.0))
    emit('bot_hizi_guncelle', {"hizi": bot_hizi}, room='admin_room')


@socketio.on('oda_sec')
def handle_oda_sec(data):
    room_id = data.get('room_id')
    if room_id in aktif_odalar:
        oda = aktif_odalar[room_id]
        emit('oda_secildi', {
            "room_id": room_id,
            "kullanici": oda["kullanici"],
            "mesajlar": oda["mesajlar"],
            "renk": oda.get("renk", "#f5a623")
        })


@socketio.on('typing_gonder')
def handle_typing(data):
    room_id = data.get('room_id')
    kullanici = data.get('kullanici')
    if room_id:
        emit('typing_goster', {"room_id": room_id, "kullanici": kullanici}, room=room_id)


# ============================================================
# Ana Program
# ============================================================
if __name__ == '__main__':
    print("=" * 50)
    print("  🍝 MAKARNA AI v2 - Gelismis Troll Yapay Zeka")
    print("=" * 50)
    print(f"  Bot Durumu: {'AKTIF' if bot_aktif else 'KAPALI'}")
    print(f"  Bot Hizi: {bot_hizi}s")
    print(f"  API: {API_PROVIDER} {'(VAR)' if API_KEY else '(YOK)'}")
    print("=" * 50)
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
