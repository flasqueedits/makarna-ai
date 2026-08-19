"""
Makarna AI - Flask Backend
Troll yapay zeka chat sistemi
Flask-SocketIO ile gerçek zamanlı iletişim
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
app.config['SECRET_KEY'] = 'makarna-ai-secret-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================================
# API Key (Google Gemini veya OpenAI)
# Gemini: https://aistudio.google.com/apikey
# OpenAI: https://platform.openai.com/api-keys
# ============================================================
API_KEY = os.environ.get('MAKARNA_AI_KEY', '')
API_PROVIDER = os.environ.get('MAKARNA_AI_PROVIDER', 'gemini')  # 'gemini' veya 'openai'

# ============================================================
# Global Durum
# ============================================================
bot_aktif = True

# ============================================================
# Oda (Room) Yapisi
# {room_id: {"kullanici": str, "mesajlar": list, "olusturma": str}}
# ============================================================
aktif_odalar = {}

# ============================================================
# Admin'in oda bazinda gonderdigi mesajlar (bot kapaliyken)
# {room_id: ["mesaj1", "mesaj2"]}
# ============================================================
admin_mesaj_kuyrugu = {}

# ============================================================
# Bot Cevaplari (trolleme amacli, karbonhidrat temali)
# ============================================================
BOT_CEVAPLARI = [
    "Makarna haşlama sürem bitti, birazdan cevap yazarım 🍝",
    "Üzerine kaşar rendelesek çözülür mü? Hemen bakıyorum...",
    "Yapay zeka değilim, makarna zekasıyım. Farkı anlarsın 🧠",
    "Bu soruyu Tobasco'ya sormak lazım, o beni programladı 🌶️",
    "Lütfen sorunuzu ricotta peynir gibi pürüzsüz yazın 🧀",
    "Şu an makarnamı haşlıyorum, biraz bekleyin ⏳",
    "Yanıt veriyorum ama önce bir Fazl reference atayım 🎵",
    "Bunu Tobasco'nun kafasına vura vura öğretirim 💀",
    "Mantı cevabı veriyorum: Mantı? HAYIR. YANIT? HAYIR 🫠",
    "Debugging yapıyorum... sorun sen misin? 🐛",
    "Bu mesajı okudum ama cevap vermek için 3-5 iş günü lazım 📅",
    "Anladım ama anlamadım. Klasik makarna AI 🤷",
    "Cevabım makarna gibi: önce haşla, sonra süz, sonra ye 🍝",
    "Tobasco beni_resetleme talimatı verdi ama vermedi 🔄",
    "Bu soruya cevap vermek için yapay zekaya ihtiyacım yok, makarna yeterli 🍝",
    "Hmm ilginç... bir makarna daha haşlayayım 🍝",
    "Yanıt üretiyorum... 404 makarna bulunamadı 🍝",
    "Kafam karıştı, biraz peynir rendeleyeyim 🧀",
    "Bu soruyu cevaplayabilmem için biraz carb loading yapmam lazım 🍝",
    "Yanıt geliyor... haşlanıyor... süzülüyor... ve servise hazır! 🍝"
]

# ============================================================
# Random troll cevaplari
# ============================================================
def get_random_cevap():
    return random.choice(BOT_CEVAPLARI)

# ============================================================
# Yapay Zeka API Entegrasyonu
# ============================================================
def api_cevap_olustur(mesaj, oda_id):
    """
    Gercek API ile cevap olusturur.
    Oda bazli hafiza (context) dahil edilir.
    API key yoksa fallback olarak bot_cevaplari kullanilir.
    """
    global API_KEY, API_PROVIDER

    if not API_KEY:
        return get_random_cevap()

    # Oda gecmisini al (son 10 mesaj)
    oda = aktif_odalar.get(oda_id, {})
    gecmis = oda.get("mesajlar", [])[-10:]

    # Context olustur
    context = []
    for m in gecmis:
        if m.get("gonderen") == "kullanici":
            context.append({"role": "user", "content": m["mesaj"]})
        elif m.get("gonderen") == "makarna_ai":
            context.append({"role": "model", "content": m["mesaj"]})

    context.append({"role": "user", "content": mesaj})

    try:
        if API_PROVIDER == 'gemini':
            return _gemini_api(context)
        elif API_PROVIDER == 'openai':
            return _openai_api(context)
        else:
            return get_random_cevap()
    except Exception as e:
        print(f"API HATASI: {e}")
        return get_random_cevap()


def _gemini_api(context):
    """Google Gemini API ile cevap olusturur."""
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
                    "Sen 'Makarna AI' adında bir yapay zekasın. Krema'nın YouTube videosundaki sahte AI mantığıyla "
                    "konuşuyorsun. Komik, troll, karbonhidrat ve makarna temalı cevaplar veriyorsun. "
                    "Cevapların kısa, komik ve trol olsun. İtalyan/File/Freddy/Fazl gibi referanslar kullan. "
                    "Asla gerçek bir AI gibi davranma. Her cevabının sonuna makarna Emoji'si ekle. "
                    "Kısa ve öz cevaplar ver, maximum 2-3 cümle."
                )
            }]
        },
        "generationConfig": {
            "maxOutputTokens": 150,
            "temperature": 0.9
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read())
        return data['candidates'][0]['content']['parts'][0]['text']


def _openai_api(context):
    """OpenAI API ile cevap olusturur."""
    import urllib.request

    url = "https://api.openai.com/v1/chat/completions"

    messages = [{"role": "system", "content": (
        "Sen 'Makarna AI' adında bir yapay zekasın. Krema'nın YouTube videosundaki sahte AI mantığıyla "
        "konuşuyorsun. Komik, troll, karbonhidrat ve makarna temalı cevaplar veriyorsun. "
        "Cevapların kısa, komik ve trol olsun. İtalyan/File/Freddy/Fazl gibi referanslar kullan. "
        "Asla gerçek bir AI gibi davranma. Her cevabının sonuna makarna Emoji'si ekle."
    )}]
    messages.extend(context)

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.9
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }
    )

    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read())
        return data['choices'][0]['message']['content']


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
    # Odadan ayrilmis olabilir, temizlik
    for room_id, oda in list(aktif_odalar.items()):
        if oda.get("kullanici_sid") == request.sid:
            leave_room(room_id)
            emit('kullanici_cikti', {
                "room_id": room_id,
                "kullanici": oda["kullanici"]
            }, room='admin_room')
            break


@socketio.on('yeni_sohbet')
def handle_yeni_sohbet(data):
    """
    Kullanici yeni sohbet baslatir.
    Data: {"kullanici": str}
    """
    kullanici = data.get('kullanici', 'Misafir')
    room_id = str(uuid.uuid4())[:8]

    # Oda olustur
    aktif_odalar[room_id] = {
        "kullanici": kullanici,
        "kullanici_sid": request.sid,
        "mesajlar": [],
        "olusturma": datetime.now().strftime("%H:%M:%S")
    }
    admin_mesaj_kuyrugu[room_id] = []

    # Kullaniciyi odaya ekle
    join_room(room_id)

    # Kullaniciye oda ID'sini gonder
    emit('sohbet_olusturuldu', {
        "room_id": room_id,
        "kullanici": kullanici
    })

    # Admin paneline bildir
    emit('yeni_sohbet_bildirimi', {
        "room_id": room_id,
        "kullanici": kullanici,
        "saat": datetime.now().strftime("%H:%M:%S")
    }, room='admin_room')

    print(f"Yeni sohbet: {kullanici} -> {room_id}")


@socketio.on('join_admin')
def handle_join_admin():
    """Admin odasina katilir."""
    join_room('admin_room')
    emit('admin_baglandi', {
        "aktif_odalar": {
            rid: {
                "kullanici": o["kullanici"],
                "son_mesaj": o["mesajlar"][-1]["mesaj"] if o["mesajlar"] else "",
                "olusturma": o["olusturma"]
            } for rid, o in aktif_odalar.items()
        }
    })


@socketio.on('kullanici_mesaj')
def handle_kullanici_mesaj(data):
    """
    Kullanicidan mesaj gelir.
    Data: {"room_id": str, "kullanici": str, "mesaj": str}
    """
    global bot_aktif

    room_id = data.get('room_id')
    kullanici = data.get('kullanici', 'Misafir')
    mesaj = data.get('mesaj', '')

    if not room_id or not mesaj:
        return

    # Mesaji oda gecmisine ekle
    if room_id in aktif_odalar:
        aktif_odalar[room_id]["mesajlar"].append({
            "gonderen": "kullanici",
            "kullanici": kullanici,
            "mesaj": mesaj,
            "saat": datetime.now().strftime("%H:%M:%S")
        })

    # Mesaji kullanicinin ekranina gonder
    emit('mesaj_geldi', {
        "gonderen": "kullanici",
        "kullanici": kullanici,
        "mesaj": mesaj,
        "saat": datetime.now().strftime("%H:%M:%S")
    }, room=room_id)

    # Admin paneline de gonder
    emit('admin_mesaj_geldi', {
        "room_id": room_id,
        "gonderen": "kullanici",
        "kullanici": kullanici,
        "mesaj": mesaj,
        "saat": datetime.now().strftime("%H:%M:%S")
    }, room='admin_room')

    # Bot aktifse otomatik cevap ver
    if bot_aktif:
        cevap = api_cevap_olustur(mesaj, room_id)

        # 1 saniye gecikme ile cevap
        def gecikmeli_cevap():
            time.sleep(1)
            socketio.emit('mesaj_geldi', {
                "gonderen": "makarna_ai",
                "kullanici": "Makarna AI 🍝",
                "mesaj": cevap,
                "saat": datetime.now().strftime("%H:%M:%S")
            }, room=room_id)

            # Oda gecmisine ekle
            if room_id in aktif_odalar:
                aktif_odalar[room_id]["mesajlar"].append({
                    "gonderen": "makarna_ai",
                    "kullanici": "Makarna AI 🍝",
                    "mesaj": cevap,
                    "saat": datetime.now().strftime("%H:%M:%S")
                })

            # Admin paneline de gonder
            socketio.emit('admin_mesaj_geldi', {
                "room_id": room_id,
                "gonderen": "makarna_ai",
                "kullanici": "Makarna AI 🍝",
                "mesaj": cevap,
                "saat": datetime.now().strftime("%H:%M:%S")
            }, room='admin_room')

        socketio.start_background_task(gecikmeli_cevap)
    else:
        # Bot kapali, admin mesaj kuyrugunu bekle
        print(f"Bot kapali - {kullanici}: {mesaj} (admin bekleniyor)")


@socketio.on('admin_mesaj_gonder')
def handle_admin_mesaj(data):
    """
    Admin direkt mesaj gonderir (bot kapaliyken).
    Data: {"room_id": str, "mesaj": str}
    """
    global bot_aktif

    if bot_aktif:
        emit('admin_uyari', {"mesaj": "Bot aktifken mesaj gönderemezsiniz! Önce botu kapatın."})
        return

    room_id = data.get('room_id')
    mesaj = data.get('mesaj', '')

    if not room_id or not mesaj:
        return

    # Mesaji odaya gonder
    emit('mesaj_geldi', {
        "gonderen": "makarna_ai",
        "kullanici": "Makarna AI 🍝",
        "mesaj": mesaj,
        "saat": datetime.now().strftime("%H:%M:%S")
    }, room=room_id)

    # Oda gecmisine ekle
    if room_id in aktif_odalar:
        aktif_odalar[room_id]["mesajlar"].append({
            "gonderen": "makarna_ai",
            "kullanici": "Makarna AI 🍝",
            "mesaj": mesaj,
            "saat": datetime.now().strftime("%H:%M:%S")
        })

    # Admin onayi
    emit('admin_mesaj_gonderildi', {
        "room_id": room_id,
        "mesaj": mesaj
    })


@socketio.on('global_mesaj')
def handle_global_mesaj(data):
    """
    Admin tum kullaniciara global mesaj gonderir.
    Data: {"mesaj": str}
    """
    mesaj = data.get('mesaj', '')
    if not mesaj:
        return

    # Tum odalara gonder
    for room_id, oda in aktif_odalar.items():
        emit('mesaj_geldi', {
            "gonderen": "makarna_ai",
            "kullanici": "Makarna AI 🍝",
            "mesaj": f"📢 DUYURU: {mesaj}",
            "saat": datetime.now().strftime("%H:%M:%S"),
            "global": True
        }, room=room_id)

        # Gecmise ekle
        oda["mesajlar"].append({
            "gonderen": "makarna_ai",
            "kullanici": "Makarna AI 🍝",
            "mesaj": f"📢 DUYURU: {mesaj}",
            "saat": datetime.now().strftime("%H:%M:%S"),
            "global": True
        })

    emit('global_gonderildi', {"mesaj": mesaj})
    print(f"Global mesaj gonderildi: {mesaj}")


@socketio.on('bot_durum_degistir')
def handle_bot_durum(data):
    """
    Admin bot durumunu degistirir.
    Data: {"aktif": bool}
    """
    global bot_aktif
    bot_aktif = data.get('aktif', True)

    durum = "AKTİF (OTOMATİK)" if bot_aktif else "KAPALI (MANUEL TROL)"
    emit('bot_durum_guncelle', {"aktif": bot_aktif, "durum_yazisi": durum}, room='admin_room')
    print(f"Bot durumu degisti: {durum}")


@socketio.on('oda_sec')
def handle_oda_sec(data):
    """
    Admin bir oda secmesi.
    Data: {"room_id": str}
    """
    room_id = data.get('room_id')
    if room_id in aktif_odalar:
        oda = aktif_odalar[room_id]
        emit('oda_secildi', {
            "room_id": room_id,
            "kullanici": oda["kullanici"],
            "mesajlar": oda["mesajlar"]
        })


# ============================================================
# Ana Program
# ============================================================
if __name__ == '__main__':
    print("=" * 50)
    print("  🍝 MAKARNA AI - Troll Yapay Zeka Chat")
    print("=" * 50)
    print(f"  Bot Durumu: {'AKTİF' if bot_aktif else 'KAPALI'}")
    print(f"  API Provider: {API_PROVIDER}")
    print(f"  API Key: {'VAR' if API_KEY else 'YOK (bot cevaplari kullanilacak)'}")
    print("=" * 50)
    print("  Kullanici: http://localhost:5000")
    print("  Admin:    http://localhost:5000/makarna-admin")
    print("=" * 50)
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
