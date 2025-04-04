import io
import re
from flask import Flask, render_template, request, send_file
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)

# --- Helper Functions for Arabic Shaping ---

def fix_arabic_text(text):
    """
    Reshape Arabic letters and apply bidi transformations so text
    is displayed in the correct right-to-left form.
    """
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def shape_arabic_in_parentheses(label):
    """
    Finds the text between parentheses in `label`, reshapes only that Arabic text,
    and returns the combined string with the correct parentheses orientation.
    For example, "Dish Wool (شماغ صوف)" becomes "Dish Wool (reshaped Arabic text)".
    """
    pattern = r'\(([^)]*)\)'  # capture text inside parentheses

    def replace_arabic(match):
        arabic_substring = match.group(1)
        shaped = fix_arabic_text(arabic_substring)
        # Return the reshaped text enclosed in unchanged parentheses.
        return f"({shaped})"

    return re.sub(pattern, replace_arabic, label)

# --- Items and Service Options ---

# Items with both English and Arabic names and their base prices
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


# Service options with multipliers
service_options = {
    'wash': 1.0,
    'iron': 1.2,
    'wash_and_iron': 1.5,
}

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        order = {}
        total = 0
        # Process each item from the form.
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

        # Add an Arabic-capable font (Amiri-Regular.ttf must be in your project folder)
        pdf.add_font(fname="Amiri-Regular.ttf", family="Amiri", uni=True)
        pdf.set_font("Amiri", size=14)

        # Title (English only; no reshaping needed)
        pdf.cell(0, 10, txt="Laundry Invoice", ln=True, align='C')
        pdf.ln(10)

        # Add each order item to the PDF
        for label, details in order.items():
            # Shape only the Arabic text inside parentheses in the label.
            shaped_label = shape_arabic_in_parentheses(label)
            line = (
                f"{shaped_label}: {details['quantity']} x {details['final_price']:.2f} "
                f"= {details['subtotal']:.2f} "
                f"(Service: {details['service']}, Comment: {details['comment']})"
            )
            pdf.multi_cell(0, 10, txt=line)
            pdf.ln(2)

        pdf.cell(0, 10, txt=f"Total: {total:.2f}", ln=True)

        # Output the PDF as a downloadable file.
        pdf_bytes = pdf.output(dest="S")
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_file.seek(0)
        return send_file(pdf_file, download_name="invoice.pdf", as_attachment=True)

    # GET request: Render the form.
    return render_template('index.html', items=items, service_options=service_options)

if __name__ == '__main__':
    app.run(debug=True)