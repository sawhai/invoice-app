import os
import io
import re
import uuid
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = '2BNTHT4AE8J8T4ZXUCKLWRNQ'  # required for flash messages

# --- Twilio Configuration ---
TWILIO_ACCOUNT_SID = "ACb1b0a5619dbb2a7905d111187b5a6805"          # update this
TWILIO_AUTH_TOKEN = "194718afc9d3ccb7caf3fff9755b9aa0"            # update this
TWILIO_WHATSAPP_FROM = "+14155238886"     # your Twilio WhatsApp sender (sandbox)
TO_WHATSAPP_NUMBER = "+96599965133"       # your number (in international format)

# PUBLIC_URL_BASE must be the publicly accessible base URL for your app.
PUBLIC_URL_BASE = "https://invoice-app-78jh.onrender.com"          # update this with your actual domain

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
    "Dish Wool (شماغ صوف)": 10.0,
    "Dishd C (ثوب قطن)": 10.0,
    "Gotra Red/White (شماغ)": 8.0,
    "Cap (طاقية)": 5.0,
    "Pajama (بيجامة)": 7.0,
    "Vest (سديري)": 5.0,
    "Underwear (ملابس داخلية)": 3.0,
    "Army Suit (بدلة عسكرية)": 12.0,
    "Shirt (قميص)": 5.0,
    "Trousers (بنطلون)": 6.0,
    "Jackets (جاكيت)": 8.0,
    "Large Coat (بالطو)": 12.0,
    "Ladies Dress (فستان حريمي)": 10.0,
    "Abaya (عباية)": 10.0,
    "Hezab (حجاب)": 3.0,
    "Skirt (تنورة)": 5.0,
    "Blouse (بلوزة)": 5.0,
    "Bath Towel (منشفة حمام)": 4.0,
    "Blanket/Dibaz (بطانية / دثار)": 15.0,
    "Bed Sheet (شرشف سرير)": 8.0,
    "Pillow Case (كيس مخدة)": 3.0,
    "Curtain (ستارة)": 15.0
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
        # Process form data
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

        # Send WhatsApp message with the invoice via Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body="Your laundry invoice is ready. Please check the attached invoice.",
            to=TO_WHATSAPP_NUMBER,
            media_url=[public_url]
        )

        flash("Invoice generated and sent via WhatsApp!", "success")
        return redirect(url_for('index'))

    return render_template('index.html', items=items, service_options=service_options)

if __name__ == '__main__':
    app.run(debug=True)