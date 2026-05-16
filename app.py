import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "influencerhub_verify")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER")

GRAPH_URL = "https://graph.facebook.com/v20.0"

OFFERS = [
    {"id": "1", "name": "1GB Data", "price": 105, "normal": 110},
    {"id": "2", "name": "2GB Data", "price": 200, "normal": 220},
    {"id": "3", "name": "5GB Data", "price": 480, "normal": 500},
]

orders = {}


def send_whatsapp(to, message):
    url = f"{GRAPH_URL}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    response = requests.post(url, headers=headers, json=payload)

    print(response.status_code)
    print(response.text)

    return response


def main_menu():
    return (
        "👋 Welcome to INFLUENCERHUB WhatsApp Bot\n\n"
        "Reply with:\n"
        "1. View Offers\n"
        "2. Buy Bundles\n"
        "3. Order History\n"
        "4. Help"
    )


def offers_text():
    text = "🔥 AVAILABLE OFFERS 🔥\n\n"

    for offer in OFFERS:
        text += (
            f"{offer['id']}. {offer['name']}\n"
            f"Was KSh {offer['normal']} ❌\n"
            f"Now KSh {offer['price']} ✅\n\n"
        )

    text += (
        "To buy:\n"
        "buy offer_id phone_number\n\n"
        "Example:\n"
        "buy 1 0746975939"
    )

    return text


def handle_message(from_number, text):
    text = text.lower().strip()

    if text in ["hi", "hello", "start", "/start", "menu"]:
        send_whatsapp(from_number, main_menu())
        return

    if text == "1":
        send_whatsapp(from_number, offers_text())
        return

    if text == "2":
        send_whatsapp(
            from_number,
            "To buy bundles send:\n\n"
            "buy offer_id phone_number\n\n"
            "Example:\n"
            "buy 1 0746975939"
        )
        return

    if text == "3":
        user_orders = [
            (oid, order)
            for oid, order in orders.items()
            if order["customer"] == from_number
        ]

        if not user_orders:
            send_whatsapp(from_number, "❌ No orders found.")
            return

        msg = "📜 YOUR ORDERS\n\n"

        for oid, order in user_orders:
            msg += (
                f"Order ID: {oid}\n"
                f"Offer: {order['offer']['name']}\n"
                f"Number: {order['buyer_phone']}\n"
                f"Status: {order['status']}\n\n"
            )

        send_whatsapp(from_number, msg)
        return

    if text.startswith("buy"):
        parts = text.split()

        if len(parts) < 3:
            send_whatsapp(
                from_number,
                "❌ Wrong format.\n\n"
                "Example:\n"
                "buy 1 0746975939"
            )
            return

        offer_id = parts[1]
        buyer_phone = parts[2]

        offer = next((o for o in OFFERS if o["id"] == offer_id), None)

        if not offer:
            send_whatsapp(from_number, "❌ Offer not found.")
            return

        order_id = str(len(orders) + 1)

        orders[order_id] = {
            "customer": from_number,
            "buyer_phone": buyer_phone,
            "offer": offer,
            "status": "PENDING",
        }

        send_whatsapp(
            from_number,
            f"✅ ORDER RECEIVED\n\n"
            f"Order ID: {order_id}\n"
            f"Offer: {offer['name']}\n"
            f"Phone: {buyer_phone}\n"
            f"Amount: KSh {offer['price']}\n\n"
            f"M-Pesa payment integration coming next."
        )

        if ADMIN_NUMBER:
            send_whatsapp(
                ADMIN_NUMBER,
                f"📦 NEW ORDER\n\n"
                f"Order ID: {order_id}\n"
                f"Customer: {from_number}\n"
                f"Bundle Number: {buyer_phone}\n"
                f"Offer: {offer['name']}\n"
                f"Amount: KSh {offer['price']}\n\n"
                f"After delivery reply:\n"
                f"delivered {order_id}"
            )

        return

    if text.startswith("delivered"):
        if from_number != ADMIN_NUMBER:
            send_whatsapp(from_number, "❌ Admin only command.")
            return

        parts = text.split()

        if len(parts) < 2:
            send_whatsapp(from_number, "Use:\ndelivered order_id")
            return

        order_id = parts[1]

        if order_id not in orders:
            send_whatsapp(from_number, "❌ Order not found.")
            return

        orders[order_id]["status"] = "DELIVERED"

        customer = orders[order_id]["customer"]

        send_whatsapp(
            customer,
            f"✅ Your bundles were delivered successfully.\n\n"
            f"Order ID: {order_id}"
        )

        send_whatsapp(
            from_number,
            f"✅ Order {order_id} marked as delivered."
        )

        return

    send_whatsapp(
        from_number,
        "❌ Unknown command.\nSend menu to continue."
    )


@app.route("/", methods=["GET"])
def home():
    return "WhatsApp Bot Running ✅"


@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    print(data)

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]

            if message["type"] == "text":
                text = message["text"]["body"]

                handle_message(from_number, text)

    except Exception as e:
        print("ERROR:", e)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True)
