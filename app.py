import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "influencerhub_verify")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER")  # Example: 254746975939

GRAPH_URL = "https://graph.facebook.com/v20.0"

OFFERS = [
    {"id": "1", "name": "1GB Data", "price": 105, "normal": 110},
    {"id": "2", "name": "2GB Data", "price": 200, "normal": 220},
    {"id": "3", "name": "5GB Data", "price": 480, "normal": 500},
]

orders = {}


def send_whatsapp(to, message):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Missing WHATSAPP_TOKEN or PHONE_NUMBER_ID")
        return None

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

    response = requests.post(url, headers=headers, json=payload, timeout=15)
    print(response.status_code, response.text)
    return response


def main_menu():
    return (
        "👋 Welcome to INFLUENCERHUB WhatsApp Bot\n\n"
        "Reply with:\n"
        "1. View offers\n"
        "2. Order bundles\n"
        "3. My order history\n"
        "4. Help"
    )


def offers_text():
    text = "🔥 Available Offers\n\n"
    for offer in OFFERS:
        text += (
            f"{offer['id']}. {offer['name']}\n"
            f"Was KSh {offer['normal']} ❌ Now KSh {offer['price']}\n\n"
        )
    text += "To order, reply: buy offer_id phone_number\n"
    text += "Example: buy 1 0746975939"
    return text


def handle_message(from_number, text):
    text = text.strip().lower()

    if text in ["hi", "hello", "start", "/start", "menu"]:
        send_whatsapp(from_number, main_menu())
        return

    if text == "1" or "offer" in text:
        send_whatsapp(from_number, offers_text())
        return

    if text == "2":
        send_whatsapp(
            from_number,
            "To order, type:\nbuy offer_id phone_number\n\nExample:\nbuy 1 0746975939",
        )
        return

    if text.startswith("buy"):
        parts = text.split()

        if len(parts) < 3:
            send_whatsapp(from_number, "Wrong format. Example:\nbuy 1 0746975939")
            return

        offer_id = parts[1]
        buyer_phone = parts[2]

        offer = next((o for o in OFFERS if o["id"] == offer_id), None)

        if not offer:
            send_whatsapp(from_number, "Offer not found. Reply 1 to view offers.")
            return

        order_id = str(len(orders) + 1)

        orders[order_id] = {
            "customer": from_number,
            "buyer_phone": buyer_phone,
            "offer": offer,
            "status": "pending",
        }

        send_whatsapp(
            from_number,
            f"✅ Order received\n\n"
            f"Order ID: {order_id}\n"
            f"Offer: {offer['name']}\n"
            f"Number: {buyer_phone}\n"
            f"Amount: KSh {offer['price']}\n\n"
            f"Payment step will be added next with M-Pesa STK.",
        )

        if ADMIN_NUMBER:
            send_whatsapp(
                ADMIN_NUMBER,
                f"📦 New WhatsApp Order\n\n"
                f"Order ID: {order_id}\n"
                f"Customer WhatsApp: {from_number}\n"
                f"Bundle Number: {buyer_phone}\n"
                f"Offer: {offer['name']}\n"
                f"Amount: KSh {offer['price']}\n\n"
                f"After sending bundle, reply:\ndelivered {order_id}",
            )

        return

    if text.startswith("delivered"):
        parts = text.split()

        if from_number != ADMIN_NUMBER:
            send_whatsapp(from_number, "Only admin can mark orders as delivered.")
            return

        if len(parts) < 2:
            send_whatsapp(from_number, "Use: delivered order_id")
            return

        order_id = parts[1]

        if order_id not in orders:
            send_whatsapp(from_number, "Order not found.")
            return

        orders[order_id]["status"] = "delivered"
        customer = orders[order_id]["customer"]

        send_whatsapp(from_number, f"✅ Order {order_id} marked as delivered.")
        send_whatsapp(
            customer,
            f"✅ Your offer has been sent successfully.\n\nOrder ID: {order_id}",
        )
        return

    if text == "3" or "history" in text:
        user_orders = [
            (oid, order) for oid, order in orders.items()
            if order["customer"] == from_number
        ]

        if not user_orders:
            send_whatsapp(from_number, "You have no orders yet.")
            return

        msg = "📜 Your Order History\n\n"
        for oid, order in user_orders:
            msg += (
                f"Order {oid}: {order['offer']['name']}\n"
                f"Number: {order['buyer_phone']}\n"
                f"Status: {order['status']}\n\n"
            )

        send_whatsapp(from_number, msg)
        return

    send_whatsapp(from_number, "I didn’t understand. Reply menu to continue.")


@app.route("/", methods=["GET"])
def home():
    return "WhatsApp bot is running ✅"


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def receive_webhook():
    data = request.get_json()
    print(data)

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return jsonify({"status": "ignored"}), 200

        message = value["messages"][0]
        from_number = message["from"]

        if message.get("type") == "text":
            text = message["text"]["body"]
            handle_message(from_number, text)

    except Exception as e:
        print("Webhook error:", e)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True)