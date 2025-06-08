# preload_inventory.py

from app import get_db

inventory_items = [
    {"type": "Propulsion System",  "name": "Motor CW X6 Plus",          "quantity": 10, "price": 1500.0},
    {"type": "Propulsion System",  "name": "Motor CCW X6 Plus",         "quantity":  8, "price": 1500.0},
    {"type": "Propulsion System",  "name": "Propeller CW 2388",         "quantity": 12, "price":  200.0},
    {"type": "Propulsion System",  "name": "Propeller CCW 2388",        "quantity": 12, "price":  200.0},
    {"type": "Propulsion System",  "name": "Propeller CW 2480",         "quantity":  7, "price":  250.0},
    {"type": "Propulsion System",  "name": "Propeller CCW 2480",        "quantity":  7, "price":  250.0},
    {"type": "Airframe",           "name": "Airframe - Center Hub",      "quantity": 15, "price": 1200.0},
    {"type": "Airframe",           "name": "L Gear - Vertical (Pieces)", "quantity":  6, "price":  300.0},
    {"type": "Airframe",           "name": "L Gear - Horizontal Set",    "quantity":  4, "price":  350.0},
    {"type": "Airframe",           "name": "Inner Arm",                  "quantity":  3, "price":  800.0},
    {"type": "Airframe",           "name": "Outer Arm",                  "quantity":  5, "price":  900.0},
    {"type": "Airframe",           "name": "Arm Foldable Part",          "quantity":  8, "price":  400.0},
    {"type": "Airframe",           "name": "Canopy",                     "quantity": 10, "price":  700.0},
    {"type": "Airframe",           "name": "L.G. Holder",                "quantity": 10, "price":  250.0},
    {"type": "Airframe",           "name": "Tank Holder",                "quantity": 16, "price":  500.0},
    {"type": "Airframe",           "name": "Tripod Mount",               "quantity":  7, "price":  600.0},
    {"type": "Airframe Accessories","name":"SS 3*10mm Attachement",       "quantity": 92, "price":   50.0},
    {"type": "Airframe Accessories","name":"SS 3*12mm Attachement",       "quantity": 80, "price":   60.0},
    {"type": "Avionics Systems",   "name": "PMU",                        "quantity":  2, "price": 2000.0},
    {"type": "Avionics Systems",   "name": "GPS",                        "quantity":  2, "price": 1800.0},
    {"type": "Avionics Systems",   "name": "Autopilot",                  "quantity":  1, "price": 3500.0},
    {"type": "Avionics Systems",   "name": "LED",                        "quantity":  4, "price":   50.0},
    {"type": "Spraying System",    "name": "Pesticide Tank",             "quantity":  3, "price": 1200.0},
    {"type": "Spraying System",    "name": "Tank Bottom Cap",            "quantity":  3, "price":  150.0},
    {"type": "Spraying System",    "name": "Tank Top Cap",               "quantity":  2, "price":  150.0},
    {"type": "Spraying System",    "name": "Pump",                       "quantity":  1, "price":  900.0},
    {"type": "Spraying System",    "name": "Nozzles",                    "quantity": 20, "price":   80.0},
    {"type": "Spraying System",    "name": "Festo Connectors 6-8-6",    "quantity":  2, "price":  100.0},
    {"type": "Spraying System",    "name": "Festo Connectors 8-12-8",   "quantity":  1, "price":  100.0},
    {"type": "Spraying System",    "name": "Festo Connectors 8-8-8",    "quantity":  3, "price":  100.0},
    {"type": "Spraying System",    "name": "Festo Connectors 8-6",      "quantity":  5, "price":  100.0},
    {"type": "Spraying System",    "name": "PU Tube 6",                 "quantity": 10, "price":   50.0},
    {"type": "Spraying System",    "name": "PU Tube 8",                 "quantity": 15, "price":   50.0},
    {"type": "Spraying System",    "name": "PU Tube 12",                "quantity":  2, "price":   50.0},
    {"type": "Spraying System",    "name": "L-Festo",                   "quantity":  1, "price":   70.0},
    {"type": "Spraying System",    "name": "Flat Nozzles with Stem",     "quantity": 12, "price":   90.0},
    {"type": "Spraying System",    "name": "Flowsensor",                 "quantity":  1, "price":  300.0},
    {"type": "Electronics Acc",    "name": "XT60 M",                    "quantity":  5, "price":  150.0},
    {"type": "Electronics Acc",    "name": "XT90 M",                    "quantity":  2, "price":  180.0},
    {"type": "Electronics Acc",    "name": "XT60 F",                    "quantity":  8, "price":  150.0},
    {"type": "Electronics Acc",    "name": "XT90 F",                    "quantity":  1, "price":  180.0},
    {"type": "Electronics Acc",    "name": "PDB",                       "quantity":  3, "price":  400.0},
    {"type": "Electronics Acc",    "name": "Power Terminal 150A Harness","quantity":  2, "price":  250.0},
    {"type": "Electronics Acc",    "name": "Extension Cable-150amps",   "quantity":  4, "price":  200.0},
    {"type": "Electronics Acc",    "name": "Power Terminal XT-90 Harness","quantity":  1, "price":  250.0},
    {"type": "Electronics Acc",    "name": "GPS Mount",                 "quantity":  3, "price":  300.0},
    {"type": "Mechanical Acc",     "name": "Paddles (23 Propeller Mount)","quantity":  0, "price":   50.0},
    {"type": "Mechanical Acc",     "name": "Paddles (24 Propeller Mount)","quantity":  4, "price":   50.0},
    {"type": "Mechanical Acc",     "name": "Wire mesh",                 "quantity":  0, "price":  100.0},
    {"type": "Mechanical Acc",     "name": "Battery Plate",             "quantity":  2, "price":  200.0},
    {"type": "Mechanical Acc",     "name": "Battery Mount Accessories", "quantity":  1, "price":  150.0},
    {"type": "Mechanical Acc",     "name": "Battery Strap",             "quantity": 21, "price":  100.0},
    {"type": "Communication System","name":"Receiver",                  "quantity":  5, "price":  500.0},
    {"type": "Communication System","name":"Antenna",                  "quantity":  8, "price":  200.0},
    {"type": "Communication System","name":"T12 Rocker",               "quantity":  4, "price":  300.0},
    {"type": "Communication System","name":"Antenna Cable",            "quantity":  6, "price":  100.0},
    {"type": "Communication System","name":"T12 radio Controller",     "quantity":  2, "price": 1000.0},
    {"type": "Communication System","name":"Dot Device",               "quantity":  1, "price":  700.0},
    {"type": "Ground Equipment",   "name":"Charger",                  "quantity":  3, "price":  800.0},
    {"type": "Ground Equipment",   "name":"Genset",                   "quantity":  2, "price": 1500.0},
    {"type": "Tools",              "name":"Allen Key-2.5",           "quantity": 17, "price":   50.0},
    {"type": "Tools",              "name":"Allen Key-3",             "quantity": 20, "price":   60.0},
    {"type": "Tools",              "name":"Spirit Level",            "quantity":  0, "price":  100.0},
    {"type": "Tools",              "name":"Lipo Checker",            "quantity":  4, "price":  120.0},
]

def preload_inventory():
    conn = get_db()
    c = conn.cursor()

    # 1) Delete all products (no TRUNCATE, so we don't need sequence‐ownership)
    c.execute("DELETE FROM products;")

    # 2) Re‐insert every item; new IDs will just keep incrementing in sequence
    for item in inventory_items:
        c.execute(
            "INSERT INTO products (name, type, quantity, price) VALUES (%s, %s, %s, %s)",
            (item["name"], item["type"], item["quantity"], item["price"])
        )

    conn.commit()
    conn.close()
    print("Inventory cleared and reloaded (IDs will continue incrementing).")

if __name__ == '__main__':
    preload_inventory()
