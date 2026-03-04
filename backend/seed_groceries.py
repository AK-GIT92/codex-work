import asyncio
import random
import csv
from faker import Faker
import asyncpg

fake = Faker()
TOTAL_RECORDS = 5000
CSV_FILE = "grocery_seed.csv"

# -----------------------------
# US + Canada Grocery Items
# -----------------------------

grocery_items = [

# Dairy
"Whole Milk", "2% Milk", "Skim Milk", "Heavy Cream", "Half and Half",
"Cheddar Cheese", "Mozzarella Cheese", "Parmesan Cheese", "Swiss Cheese",
"Cream Cheese", "Greek Yogurt", "Vanilla Yogurt", "Salted Butter",
"Unsalted Butter", "Sour Cream", "Cottage Cheese",

# Bakery
"White Bread", "Whole Wheat Bread", "Sourdough Bread", "Bagels",
"English Muffins", "Croissants", "Hamburger Buns", "Hot Dog Buns",
"Tortillas", "Pancake Mix", "Waffle Mix",

# Meat & Seafood
"Ground Beef", "Ribeye Steak", "Sirloin Steak", "Chicken Breast",
"Chicken Thighs", "Chicken Wings", "Pork Chops", "Bacon",
"Breakfast Sausage", "Turkey Breast", "Ham Slices",
"Salmon Fillet", "Tilapia Fillet", "Shrimp", "Frozen Fish Sticks",

# Pantry
"White Rice", "Brown Rice", "Jasmine Rice", "Spaghetti",
"Macaroni", "Fettuccine", "Penne Pasta", "Tomato Sauce",
"Alfredo Sauce", "Marinara Sauce", "Peanut Butter",
"Almond Butter", "Strawberry Jam", "Grape Jelly",
"Maple Syrup", "Honey", "Granola", "Cornflakes",
"Oatmeal", "Flour", "Baking Soda", "Baking Powder",
"Brown Sugar", "White Sugar", "Sea Salt", "Black Pepper",
"Olive Oil", "Vegetable Oil", "Canola Oil",

# Drinks
"Orange Juice", "Apple Juice", "Cranberry Juice",
"Cola Soda", "Diet Cola", "Root Beer", "Ginger Ale",
"Sparkling Water", "Bottled Water",
"Ground Coffee", "Coffee Beans", "Green Tea",
"Black Tea", "Iced Tea", "Hot Chocolate Mix",

# Frozen
"Frozen Pizza", "Frozen Fries", "Frozen Vegetables",
"Frozen Blueberries", "Vanilla Ice Cream",
"Chocolate Ice Cream", "Ice Cream Sandwiches",

# Produce
"Bananas", "Apples", "Oranges", "Blueberries",
"Strawberries", "Avocados", "Tomatoes",
"Lettuce", "Spinach", "Broccoli", "Carrots",
"Onions", "Garlic", "Bell Peppers",
"Potatoes", "Sweet Potatoes", "Cucumbers",

# Canned
"Canned Corn", "Canned Beans", "Black Beans",
"Kidney Beans", "Chickpeas", "Canned Tuna",
"Chicken Noodle Soup", "Tomato Soup", "Beef Stew",

# Canadian Favorites
"Pure Maple Syrup", "Poutine Gravy Mix",
"Montreal Steak Spice", "All Dressed Chips",
"Ketchup Chips", "Butter Tarts",
"Tourtiere Pie", "Caesar Cocktail Mix"
]

# -----------------------------
# Helper Functions
# -----------------------------

def generate_description(max_words=50):
    paragraph = fake.paragraph(nb_sentences=6)
    words = paragraph.split()
    return " ".join(words[:max_words])

def generate_price():
    # Realistic grocery pricing
    return round(random.uniform(1.50, 45.00), 2)

def generate_csv():
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        for _ in range(TOTAL_RECORDS):
            name = random.choice(grocery_items)
            description = generate_description()
            price = generate_price()

            writer.writerow([name, description, price])

# -----------------------------
# COPY into PostgreSQL
# -----------------------------


async def copy_to_db():
    conn = await asyncpg.connect(
        user="neondb_owner",
        password="npg_iGagM1V3fBSP",
        database="kyle",
        host="ep-tiny-haze-a7rs6bkb-pooler.ap-southeast-2.aws.neon.tech",
        port=5432
    )

    with open(CSV_FILE, "rb") as f:
        await conn.copy_to_table(
            table_name="grocery_list",
            schema_name="next_js_db",
            source=f,
            columns=["grocery_name", "grocery_description", "grocery_price"],
            format="csv"
        )

    await conn.close()


# -----------------------------
# Main
# -----------------------------

async def main():
    print("Generating CSV...")
    generate_csv()

    print("Inserting into database using COPY...")
    await copy_to_db()

    print("🔥 5000 grocery items inserted successfully.")

if __name__ == "__main__":
    asyncio.run(main())

