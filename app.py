import os
import io
import re
import uuid
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

print("DEBUGGG")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret_key")

# --- Twilio Configuration (using environment variables) ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
# Default recipient if user input is missing
DEFAULT_TO_WHATSAPP_NUMBER = os.getenv("TO_WHATSAPP_NUMBER", "whatsapp:+96599965133")

# PUBLIC_URL_BASE must be the publicly accessible base URL for your app.
PUBLIC_URL_BASE = os.getenv("PUBLIC_URL_BASE", "https://your-app-domain.com")

# Ensure invoices directory exists under the static folder.
invoices_dir = os.path.join("static", "invoices")
if not os.path.exists(invoices_dir):
    os.makedirs(invoices_dir)

# --- Helper Functions for Arabic Shaping ---
def fix_arabic_text(text):
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def shape_arabic_in_parentheses(label):
    pattern = r'\(([^)]*)\)'
    def replace_arabic(match):
        arabic_substring = match.group(1)
        shaped = fix_arabic_text(arabic_substring)
        return f"({shaped})"
    return re.sub(pattern, replace_arabic, label)

# --- Items and Service Options ---
items = {
    "Dish Wool (شماغ صوف)": 0.25,
    "Dishd C (ثوب قطن)": 0.25,
    "Gotra Red/White (شماغ)": 0.25,
    "Cap (طاقية)": 0.15,
    "Pajama (بيجامة)": 0.5,
    "Vest (سديري)": 0.75,
    "Underwear (ملابس داخلية)": 0.25,
    "Army Suit (بدلة عسكرية)": 1.5,
    "Shirt (قميص)": 1.0,
    "Trousers (بنطلون)": 1.0,
    "Jackets (جاكيت)": 1.25,
    "Large Coat (بالطو)": 2.5,
    "Ladies Dress (فستان حريمي)": 2.0,
    "Abaya (عباية)": 1.75,
    "Hezab (حجاب)": 0.5,
    "Skirt (تنورة)": 0.75,
    "Blouse (بلوزة)": 0.5,
    "Bath Towel (منشفة حمام)": 0.5,
    "Blanket/Dibaz (بطانية / دثار)": 3.5,
    "Bed Sheet (شرشف سرير)": 2.5,
    "Pillow Case (كيس مخدة)": 0.5,
    "Curtain (ستارة)": 4.0
}

service_options = {
    'wash': 1.0,
    'iron': 1.2,
    'wash_and_iron': 1.5,
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        order = {}
        total = 0
        # Process form data for invoice items
        for item_label, base_price in items.items():
            quantity = int(request.form.get(f'{item_label}_quantity', 0))
            comment = request.form.get(f'{item_label}_comment', '')
            service = request.form.get(f'{item_label}_service', 'wash')
            multiplier = service_options.get(service, 1.0)
            final_price = base_price * multiplier

            if quantity > 0:
                subtotal = quantity * final_price
                order[item_label] = {
                    'quantity': quantity,
                    'comment': comment,
                    'service': service,
                    'final_price': final_price,
                    'subtotal': subtotal
                }
                total += subtotal

        # Create PDF invoice using fpdf2
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font(fname="Amiri-Regular.ttf", family="Amiri", uni=True)
        pdf.set_font("Amiri", size=14)
        pdf.cell(0, 10, txt="Laundry Invoice", ln=True, align='C')
        pdf.ln(10)
        for label, details in order.items():
            shaped_label = shape_arabic_in_parentheses(label)
            line = (
                f"{shaped_label}: {details['quantity']} x {details['final_price']:.2f} "
                f"= {details['subtotal']:.2f} "
                f"(Service: {details['service']}, Comment: {details['comment']})"
            )
            pdf.multi_cell(0, 10, txt=line)
            pdf.ln(2)
        pdf.cell(0, 10, txt=f"Total: {total:.2f}", ln=True)
        pdf_bytes = pdf.output(dest="S")

        # Save the PDF to a unique file in the static/invoices folder.
        filename = f"invoice_{uuid.uuid4().hex}.pdf"
        filepath = os.path.join(invoices_dir, filename)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        # Construct the public URL to the PDF (must be accessible by Twilio)
        public_url = f"{PUBLIC_URL_BASE}/static/invoices/{filename}"

        # Get recipient WhatsApp number from form input
        recipient_number = request.form.get("recipient_number", "").strip()
        print("DEBUG: recipient_number =", repr(recipient_number))  # Debug line

        if not recipient_number:
            recipient_number = DEFAULT_TO_WHATSAPP_NUMBER
        # Ensure the number is prefixed with "whatsapp:"
        if not recipient_number.startswith("whatsapp:"):
            recipient_number = "whatsapp:" + recipient_number

        # Send WhatsApp message with the invoice via Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body="Your laundry invoice is ready. Please check the attached invoice.",
            to=recipient_number,
            media_url=[public_url]
        )

        flash("Invoice generated and sent via WhatsApp!", "success")
        return redirect(url_for('index'))

    return render_template('index.html', items=items, service_options=service_options)

if __name__ == '__main__':
    app.run(debug=True)