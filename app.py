from itertools import product
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for,session
import pandas as pd
import os
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures
import random

app = Flask(__name__)
app.secret_key = "your_super_secret_key_123" 

def validate_image_url(url):
    """Validate if a URL points to a valid image"""
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False

        response = requests.head(url, timeout=5)
        content_type = response.headers.get('content-type', '')
        return 'image' in content_type.lower()
    except:
        return False


def validate_urls_parallel(urls):
    """Validate multiple URLs in parallel"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(validate_image_url, urls)
        return list(results)

# Load laptop data from data/laptop_dataset_with_images.csv
import sqlite3

DB_PATH = os.path.join('data', 'laptop_dataset.db')   # Your DB file path
conn = sqlite3.connect(DB_PATH)

df = pd.read_sql("SELECT * FROM laptops", conn)  # Correct table name
conn.close()



# Clean and prepare data
df['Price_Rs'] = df['Price_Rs'].round(2)
df['Weight'] = df['Weight'].round(2)
df['Inches'] = df['Inches'].round(2)
df['CPU_freq'] = df['CPU_freq'].round(2)

# Add ID column
df['ID'] = range(1, len(df) + 1)

# Add default brand images for missing URLs
default_brand_images = {
    'HP': 'https://m.media-amazon.com/images/I/71gE7D4x3-L._SL1500_.jpg',
    'Dell': 'https://m.media-amazon.com/images/I/61gGtqfZFlL._SL1500_.jpg',
    'Acer': 'https://m.media-amazon.com/images/I/71CZcP2FRoL._SL1500_.jpg',
    'Asus': 'https://m.media-amazon.com/images/I/71S8U9VzLTL._SL1500_.jpg',
    'Lenovo': 'https://m.media-amazon.com/images/I/71eXNIDUGjL._SL1500_.jpg',
    'MSI': 'https://m.media-amazon.com/images/I/71tH6wz5jUL._SL1500_.jpg',
    'Apple': 'https://m.media-amazon.com/images/I/61L1ItFgFHL._SL1500_.jpg',
    'Microsoft': 'https://m.media-amazon.com/images/I/71y4JtEdWYL._SL1500_.jpg'
}
@app.route('/monitors')
def monitors():
    """Monitors page - shows external monitor recommendations"""
    return render_template('monitors.html')


# Fill missing image URLs with brand defaults and validate URLs
# First rename the Image_URL column if it exists
if 'Image_URL' in df.columns:
    # Get unique non-null URLs
    unique_urls = df['Image_URL'].dropna().unique()
    valid_urls = dict(zip(unique_urls, validate_urls_parallel(unique_urls)))
    
    # Update invalid URLs with brand defaults
    df['image_url'] = df.apply(lambda row: 
        row['Image_URL'] if pd.notna(row['Image_URL']) and valid_urls.get(row['Image_URL'], False)
        else default_brand_images.get(row['Company'], None), axis=1)
else:
    # If no Image_URL column, create image_url column with defaults
    df['image_url'] = df['Company'].map(default_brand_images)

# Rename columns for consistency
df = df.rename(columns={
    'Price_Rs': 'Price',
    'Company': 'Brand',
    'Ram': 'RAM_Size',
    'PrimaryStorage': 'Storage_Capacity',
    'Inches': 'Screen_Size',
    'CPU_freq': 'Processor_Speed',
    'CPU_model': 'Processor_Model',
    'CPU_company': 'Processor_Brand'
})


@app.route('/')
def home():
    categories = [
       {
            "name": "Laptops",
            "desc": "Gaming | Office | Students",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTjeQkkw7u63MYY8Z3HSh_pHA-XQafHvMDB7Q&s",
            "href": "/products?category=laptops"
        },
        {
            "name": "Antivirus Software",
            "desc": "Kaspersky | Norton | McAfee",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTPCAefBFCP6jr0eh5wJS-8kFJfm_lKDQ2Xjg&s",
            "href": "/antivirus"
        },
        {
            "name": "External Monitors",
            "desc": "4K UHD | Gaming | Portable",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQj3ZGbfqSapoW_U2JamvoboHM12G_Jqn0u4w&s",
            "href": "/monitors"
        },
        {
            "name": "Accessories",
            "desc": "Chargers | Cables | Covers",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRxbSLQWufLFI5o8SlDrCPivQudiX82dl3gAqdrpFtZlVI-PnLPPkdOegMfKGreEjojGss&usqp=CAU",
            "href": "/accessories"
        },
    ]
    return render_template("index.html", categories=categories)

@app.route('/gaming_laptop')
def gaming_laptop():
    return render_template('gaming_laptop.html')


@app.route('/products')
def products():
    brand = request.args.get('brand', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    ram = request.args.get('ram', type=int)
    storage = request.args.get('storage', type=int)

    filtered_df = df.copy()

    if brand and brand != 'all':
        filtered_df = filtered_df[filtered_df['Brand'] == brand]
    if min_price:
        filtered_df = filtered_df[filtered_df['Price'] >= min_price]
    if max_price:
        filtered_df = filtered_df[filtered_df['Price'] <= max_price]
    if ram:
        filtered_df = filtered_df[filtered_df['RAM_Size'] == ram]
    if storage:
        filtered_df = filtered_df[filtered_df['Storage_Capacity'] == storage]

    sort_by = request.args.get('sort', 'price_asc')
    if sort_by == 'price_asc':
        filtered_df = filtered_df.sort_values('Price')
    elif sort_by == 'price_desc':
        filtered_df = filtered_df.sort_values('Price', ascending=False)

    brands = sorted(df['Brand'].unique())
    ram_options = sorted(df['RAM_Size'].unique())
    storage_options = sorted(df['Storage_Capacity'].unique())
    laptops = filtered_df.to_dict('records')

    return render_template(
        'products.html',
        laptops=laptops,
        brands=brands,
        ram_options=ram_options,
        storage_options=storage_options,
        current_brand=brand,
        current_ram=ram,
        current_storage=storage
    )


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    laptop = df[df['ID'] == product_id].to_dict('records')
    if laptop:
        return render_template('product_detail.html', laptop=laptop[0])
    else:
        return "Product not found", 404


@app.route('/about')
def about():
    # Basic stats
    total_laptops = len(df)
    brands = sorted(df['Brand'].unique())
    avg_price = df['Price'].mean()
    
    # Brand distribution
    brand_counts = df['Brand'].value_counts()
    brand_labels = brand_counts.index.tolist()
    brand_counts = brand_counts.values.tolist()

    # Trending laptops (based on most common RAM and price range combinations)
    trending_models = df.groupby('Product')['Price'].count().sort_values(ascending=False).head(5)
    trending_labels = trending_models.index.tolist()
    trending_counts = trending_models.values.tolist()

    # Price range distribution
    price_ranges = [0, 30000, 50000, 80000, 100000, float('inf')]
    price_labels = ['Under ₹30K', '₹30K-50K', '₹50K-80K', '₹80K-100K', 'Above ₹100K']
    price_counts = []
    for i in range(len(price_ranges)-1):
        count = len(df[(df['Price'] >= price_ranges[i]) & (df['Price'] < price_ranges[i+1])])
        price_counts.append(count)

    # Stock status by brand (simulated data - you'll need to modify this based on your actual stock tracking)
    stock_labels = brands
    stock_available = [len(df[df['Brand'] == brand]) for brand in brands]
    stock_sold = [int(count * 0.3) for count in stock_available]  # Simulated 30% sold
    available_laptops = sum(stock_available)

    stats = {
        'total_laptops': total_laptops,
        'brands': brands,
        'avg_price': round(avg_price, 2),
        'num_brands': len(brands),
        'available_laptops': available_laptops,
        
        # Chart data
        'brand_labels': brand_labels,
        'brand_counts': brand_counts,
        'trending_labels': trending_labels,
        'trending_counts': trending_counts,
        'price_range_labels': price_labels,
        'price_range_counts': price_counts,
        'stock_labels': stock_labels,
        'stock_available': stock_available,
        'stock_sold': stock_sold
    }
    
    return render_template('about.html', stats=stats)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']

        with open("messages.txt", "a") as f:
            f.write(f"\n--- New Message ---\n"
                    f"Time: {datetime.now()}\n"
                    f"Name: {name}\n"
                    f"Email: {email}\n"
                    f"Subject: {subject}\n"
                    f"Message: {message}\n")

        flash('✅ Thank you! Your message has been sent successfully.', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')


@app.route("/warranty", methods=["GET", "POST"])
def warranty_page():
    warranty_result = None

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()   # accepted but not checked
        company = request.form.get("company", "").strip()
        product = request.form.get("product", "").strip()

        if not phone or not company or not product:
            flash("Please fill all fields", "danger")
            return render_template("warranty.html", warranty_result=None)

        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()

        cur.execute("""
            SELECT warranty_status FROM laptops
            WHERE Company = ? AND Product = ?
        """, (company, product))

        row = cur.fetchone()
        con.close()

        if row:
            warranty_result = row[0]
        else:
            flash("No warranty details found for this product.", "danger")

    return render_template("warranty.html", warranty_result=warranty_result)


@app.route('/accessories')
def accessories():
    """Accessories page"""
    return render_template('accessories.html')

# Antivirus products list
antivirus_list = [
    {
        "id": 1,
        "name": "Kaspersky Total Security",
        "price": 799,
        "validity": "1 Year - 1 Device",
        "features": ["Real-time protection", "Anti-phishing", "Parental controls"],
        "url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS9ilBrZ40fE0mwtP6YboP41IZ6bnBqmGUBvA&s"
    },
    {
        "id": 2,
        "name": "Quick Heal Total Security",
        "price": 699,
        "validity": "1 Year - 1 Device",
        "features": ["Ransomware protection", "Web security", "Performance optimizer"],
        "url": "https://images-eu.ssl-images-amazon.com/images/I/71U8ZqX6hPL._AC_UL210_SR210,210_.jpg"
    },
    {
        "id": 3,
        "name": "McAfee Antivirus Plus",
        "price": 899,
        "validity": "1 Year - 3 Devices",
        "features": ["VPN included", "Password manager", "Multi-device support"],
        "url": "https://5.imimg.com/data5/SELLER/Default/2023/3/296418100/LS/QN/QW/9971803/norton-360-deluxe-software-500x500.png"
    },
    {
        "id": 4,
        "name": "Norton 360 Deluxe",
        "price": 999,
        "validity": "1 Year - 5 Devices",
        "features": ["Cloud backup", "Smart firewall", "Dark web monitoring"],
        "url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSTlDA1GACboNR0X8c3iMtT_Lxm0N_4vO_Etir2Vvdcdq-ed8ihPNESMR-NWBEBN7ZexO8&usqp=CAU"
    }
]

@app.route('/antivirus')
def antivirus():
    """Antivirus page"""
    return render_template('antivirus.html', antiviruses=antivirus_list)


@app.route('/buy-antivirus/<int:av_id>')
def buy_antivirus(av_id):
    """Buy antivirus page"""
    # Find the antivirus by ID
    antivirus = next((av for av in antivirus_list if av['id'] == av_id), None)

    if antivirus:
        return render_template('buy_antivirus.html', antivirus=antivirus)
    else:
        return "Antivirus not found", 404

@app.route('/api/laptops')
def api_laptops():
    laptops = df.to_dict('records')
    return jsonify(laptops)


@app.route('/students_laptops')
def students_laptops():
    return render_template('students_laptops.html')

@app.route('/office_laptops')
def office_laptops():
    return render_template('office_laptops.html')

@app.route('/cheap_laptops')
def cheap_laptops():
    return render_template('cheap_laptops.html')



 #Convert to dictionary for faster use
laptops = df.to_dict(orient="records")

# ------------------------
# ⭐ Rating System Storage
# ------------------------
ratings = {}   # { laptop_id: [list of ratings] }



@app.route('/cart')
def cart_page():
    return render_template("cart.html", cart=session.get("cart", []), 
                           total_items=session.get("total_items", 0),
                           total_price=session.get("total_price", 0))

def initialize_cart():
    if "cart" not in session:
        session["cart"] = []
        session["total_items"] = 0
        session["total_price"] = 0

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    initialize_cart()

    product_id = request.form.get("id")
    name = request.form.get("name")
    price = float(request.form.get("price").replace(",", ""))
    image = request.form.get("image")

    # check if product already in cart
    for item in session["cart"]:
        if item["id"] == product_id:
            item["quantity"] += 1
            break
    else:
        session["cart"].append({
            "id": product_id,
            "name": name,
            "price": price,
            "image": image,
            "quantity": 1
        })

    # update totals
    session["total_items"] = sum(i["quantity"] for i in session["cart"])
    session["total_price"] = sum(i["price"] * i["quantity"] for i in session["cart"])

    session.modified = True
    flash("Item added to cart")
    return redirect(request.referrer)


@app.route("/remove-item", methods=["POST"])
def remove_item():
    product_id = request.form.get("product_id")
    session["cart"] = [item for item in session["cart"] if item["id"] != product_id]

    session["total_items"] = sum(i["quantity"] for i in session["cart"])
    session["total_price"] = sum(i["price"] * i["quantity"] for i in session["cart"])
    session.modified = True

    return redirect(url_for("cart_page"))

@app.route("/update-quantity", methods=["POST"])
def update_quantity():
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity"))

    for item in session["cart"]:
        if item["id"] == product_id:
            item["quantity"] = quantity
            break

    session["total_items"] = sum(i["quantity"] for i in session["cart"])
    session["total_price"] = sum(i["price"] * i["quantity"] for i in session["cart"])
    session.modified = True

    return redirect(url_for("cart_page"))

@app.route('/buy-now', methods=["POST"])
def buy_now():
    # use id to get laptop details
    return render_template("checkout.html", product_id=id)

# ------------------------
# ⭐ Submit Rating
# ------------------------
@app.route("/rate/<id>", methods=["POST"])
def rate_laptop(id):
    rating = int(request.form["rating"])
    id = str(id)

    if id not in ratings:
        ratings[id] = []

    ratings[id].append(rating)
    return redirect(request.referrer)


# ------------------------
# 🤖 AI Recommendation Engine
# ------------------------
def recommend_laptops(selected_ids):
    if not selected_ids:
        return random.sample(laptops, 3)

    selected = [l for l in laptops if str(l["id"]) in selected_ids]

    # Take the first selected laptop for reference
    base = selected[0]

    # Similar laptops by processor, RAM, and price range
    recs = [
        l for l in laptops
        if l["Processor"] == base["Processor"]
        or l["RAM"] == base["RAM"]
        or abs(int(l["Price (INR)"]) - int(base["Price (INR)"])) <= 20000
    ]

    # remove duplicates and selected laptops
    recs = [r for r in recs if str(r["id"]) not in selected_ids]

    # return 3 random recommendations
    return random.sample(recs, min(len(recs), 3))

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_msg = request.json.get("message", "").lower()

    responses = {
    "hi": "Hello! 👋 How can I assist you today?",
    "hello": "Hello! 😊 What laptop details would you like to know?",
    
    "dell": "💼 Dell laptops are highly reliable for office and business use. • Inspiron – budget and everyday tasks • XPS – premium performance and build quality.",
    "hp": "💛 HP laptops offer solid reliability and good customer support. • Pavilion – budget & students • Omen – gaming and high performance.",
    "lenovo": "🟥 Lenovo provides the best value-for-money laptops. • IdeaPad – students & daily use • Legion – high-end gaming and performance.",
    "asus": "🟦 Asus is excellent for performance and gaming. • VivoBook – everyday & office • TUF/ROG – gaming with strong thermals.",
    "acer": "🟨 Acer offers powerful performance at affordable pricing. • Aspire – budget segment • Predator – gaming laptops.",
    
    "gaming laptop": "🎮 For gaming, consider: Ryzen 7 / Core i7 | 16GB RAM | RTX 3050 / 3060 GPU | 144Hz display. These specs provide smooth performance in modern games.",
    "student laptop": "🎓 For students: Ryzen 5 / Core i5 | 8GB RAM | 512GB SSD | good battery backup. Lightweight models are recommended for portability.",
    
    "under 30000": "💰 Top laptops under ₹30,000 — Lenovo V14 | HP 15s | Acer Aspire 3. Ideal for basic office and student needs.",
    "under 40000": "💰 Best laptops under ₹40,000 — Lenovo IdeaPad Slim 3 | HP 15s | Acer Aspire 5. Good for students & office users.",
    "under 50000": "💰 Recommended under ₹50,000 — Dell Inspiron 15 3000 | Lenovo IdeaPad 3 | Acer Aspire 5. Balanced performance and value.",
    "under 60000": "💰 Best picks under ₹60,000 — Asus VivoBook Pro | HP Victus | Lenovo IdeaPad Gaming. Suitable for entry-level gaming and editing.",
    "under 70000": "💰 Best under ₹70,000 — Lenovo Legion 5 | Asus TUF F15 | HP Victus 16. Great for gaming and heavy work.",
    "under 80000": "💰 Top laptops under ₹80,000 — Dell G15 | Asus ROG Strix | Lenovo Legion 5. Powerful gaming and graphics performance.",
    "under 100000": "💰 Best under ₹1,00,000 — MacBook Air M1 | Dell XPS 13 | Asus ROG Zephyrus. Premium build and high performance.",
    
    "battery": "🔋 For long battery life, choose Intel U-series / Ryzen U-series processors and 50–70Wh battery capacity.",
    "heating": "🔥 Laptop heating can be reduced by ensuring proper ventilation, using it on hard surfaces and cleaning air vents regularly.",
    "slow": "⚡ To speed up a slow laptop: upgrade to SSD, add more RAM, remove startup apps, and perform regular updates.",
    "warranty": "🛡 Warranty can be checked using the laptop's serial number on the brand's official support website.",
    "clean": "🧼 Clean your laptop screen with a microfiber cloth and use compressed air to remove dust from the keyboard and vents.",
    
    "bye": "Thank you for chatting with us! 👋 Have a great day ahead!",
    "thank you": "You're welcome! 😊 Happy to assist you anytime."
}


    for key in responses:
        if key in user_msg:
            return jsonify({"reply": responses[key]})

    return jsonify({"reply": "I'm here to help 😊 Ask about brands, gaming laptops, student laptops, budget laptops, battery, or warranty."})

@app.route("/checkout/<int:id>", methods=["POST"])
def checkout(id):
    antivirus = next((a for a in antivirus_list if a["id"] == id), None)

    customer_name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]
    payment_method = request.form["payment"]

    session["order"] = {
        "name": customer_name,
        "email": email,
        "phone": phone,
        "payment_method": payment_method
    }

    upi_id = "9980307550-2@axl"  # change to your UPI
    return render_template("checkout.html", antivirus=antivirus, upi_id=upi_id)



@app.route("/order_success/<int:id>", methods=["POST"])
def order_success(id):
    antivirus = next((a for a in antivirus_list if a["id"] == id), None)

    # Here you can also store order in database if needed
    return render_template("order_success.html", antivirus=antivirus)


if __name__ == '__main__':
    app.run(debug=True)