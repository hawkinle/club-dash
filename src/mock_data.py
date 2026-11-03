import os
import random
from datetime import datetime, timedelta
import pandas as pd

def generate_mock_club_data():
    """
    Generates realistic seed data tailored for the Upper Horton Sports Club
    covering current trading (last 60 days) and comparative prior year trading (same month last year).
    Ensures today has live completed orders up to the current hour and includes the configured Square location.
    """
    random.seed(42)

    sandbox_loc = os.getenv("SQUARE_LOCATION_ID", "").strip()
    primary_loc = sandbox_loc if sandbox_loc else "LOC_UHSC_MAIN"
    primary_name = "Default Test Account (Sandbox)" if sandbox_loc else "Upper Horton Sports Club - Main Clubhouse"

    locations_data = [
        {
            "location_id": primary_loc,
            "name": primary_name,
            "status": "ACTIVE",
            "currency": "AUD",
            "address": "22 Cobbadah St, Upper Horton NSW 2347"
        },
        {
            "location_id": "LOC_UHSC_MAIN",
            "name": "Upper Horton Sports Club - Main Clubhouse",
            "status": "ACTIVE",
            "currency": "AUD",
            "address": "22 Cobbadah St, Upper Horton NSW 2347"
        },
        {
            "location_id": "LOC_UHSC_GROUNDS",
            "name": "Upper Horton Sports Club - Grounds & Canteen",
            "status": "ACTIVE",
            "currency": "AUD",
            "address": "22 Cobbadah St, Upper Horton NSW 2347"
        }
    ]
    # Remove duplicate location IDs if any
    seen_locs = set()
    unique_locs = []
    for l in locations_data:
        if l["location_id"] not in seen_locs:
            seen_locs.add(l["location_id"])
            unique_locs.append(l)
    df_locations = pd.DataFrame(unique_locs)

    categories_data = [
        {"category_id": "CAT_BEER", "name": "Bar - Beer & Cider"},
        {"category_id": "CAT_SPIRITS", "name": "Bar - Spirits & Wine"},
        {"category_id": "CAT_NONALC", "name": "Bar - Non-Alcoholic"},
        {"category_id": "CAT_CANTEEN", "name": "Canteen & Bistro"},
        {"category_id": "CAT_EVENTS", "name": "Events & Gate"},
        {"category_id": "CAT_MERCH", "name": "Club Merchandise"},
    ]
    df_categories = pd.DataFrame(categories_data)

    menu_items = [
        # Beer (Tap / Draught)
        {"item_id": "ITEM_GN_SCHOONER", "category_id": "CAT_BEER", "category_name": "Bar - Beer & Cider", "name": "Great Northern Super Crisp (Schooner)", "price": 7.50},
        {"item_id": "ITEM_CD_SCHOONER", "category_id": "CAT_BEER", "category_name": "Bar - Beer & Cider", "name": "Carlton Dry (Schooner)", "price": 8.00},
        {"item_id": "ITEM_RESCHS_SCHOONER", "category_id": "CAT_BEER", "category_name": "Bar - Beer & Cider", "name": "Reschs Draught (Schooner)", "price": 8.00},
        
        # Beer (Packaged - Stubbies & Cans)
        {"item_id": "ITEM_VB_STUBBY", "category_id": "CAT_BEER", "category_name": "Bar - Beer & Cider", "name": "Victoria Bitter (Stubby)", "price": 7.00},
        {"item_id": "ITEM_CORONA", "category_id": "CAT_BEER", "category_name": "Bar - Beer & Cider", "name": "Corona Extra (Bottle)", "price": 8.50},
        {"item_id": "ITEM_CIDER", "category_id": "CAT_BEER", "category_name": "Bar - Beer & Cider", "name": "Somersby Apple Cider (Can)", "price": 8.50},
        {"item_id": "ITEM_MID_STRENGTH", "category_id": "CAT_BEER", "category_name": "Bar - Beer & Cider", "name": "XXXX Gold (Stubby)", "price": 6.50},
        {"item_id": "ITEM_SLOW_CIDER", "category_id": "CAT_BEER", "category_name": "Bar - Beer & Cider", "name": "Artisan Pear Perry Cider", "price": 9.50},  # Low mover
        
        # Spirits & Wine
        {"item_id": "ITEM_BUNDY_CAN", "category_id": "CAT_SPIRITS", "category_name": "Bar - Spirits & Wine", "name": "Bundaberg Rum & Cola Can", "price": 10.50},
        {"item_id": "ITEM_JD_CAN", "category_id": "CAT_SPIRITS", "category_name": "Bar - Spirits & Wine", "name": "Jack Daniels & Cola Can", "price": 11.00},
        {"item_id": "ITEM_GIN_TONIC", "category_id": "CAT_SPIRITS", "category_name": "Bar - Spirits & Wine", "name": "House Gin & Tonic", "price": 9.50},
        {"item_id": "ITEM_SHIRAZ_GLASS", "category_id": "CAT_SPIRITS", "category_name": "Bar - Spirits & Wine", "name": "Pepperjack Shiraz (Glass)", "price": 9.00},
        {"item_id": "ITEM_SAUV_GLASS", "category_id": "CAT_SPIRITS", "category_name": "Bar - Spirits & Wine", "name": "Sauvignon Blanc (Glass)", "price": 8.50},
        {"item_id": "ITEM_SLOW_LIQUEUR", "category_id": "CAT_SPIRITS", "category_name": "Bar - Spirits & Wine", "name": "Grand Marnier (Nip)", "price": 12.00}, # Dead stock
        
        # Soft Drinks
        {"item_id": "ITEM_COKE_CAN", "category_id": "CAT_NONALC", "category_name": "Bar - Non-Alcoholic", "name": "Coca-Cola 375ml", "price": 3.50},
        {"item_id": "ITEM_SOLO_CAN", "category_id": "CAT_NONALC", "category_name": "Bar - Non-Alcoholic", "name": "Solo Lemon 375ml", "price": 3.50},
        {"item_id": "ITEM_GINGER_BEER", "category_id": "CAT_NONALC", "category_name": "Bar - Non-Alcoholic", "name": "Bundaberg Ginger Beer", "price": 4.50},
        {"item_id": "ITEM_WATER", "category_id": "CAT_NONALC", "category_name": "Bar - Non-Alcoholic", "name": "Mount Franklin Spring Water", "price": 3.00},
        
        # Canteen
        {"item_id": "ITEM_WORKS_BURGER", "category_id": "CAT_CANTEEN", "category_name": "Canteen & Bistro", "name": "Upper Horton Works Burger", "price": 14.00},
        {"item_id": "ITEM_STEAK_SANDWICH", "category_id": "CAT_CANTEEN", "category_name": "Canteen & Bistro", "name": "Rib Fillet Steak Sandwich", "price": 15.00},
        {"item_id": "ITEM_CHIPS_LG", "category_id": "CAT_CANTEEN", "category_name": "Canteen & Bistro", "name": "Hot Chips (Large Basket)", "price": 7.50},
        {"item_id": "ITEM_CHIPS_SM", "category_id": "CAT_CANTEEN", "category_name": "Canteen & Bistro", "name": "Hot Chips (Cup)", "price": 4.50},
        {"item_id": "ITEM_MEAT_PIE", "category_id": "CAT_CANTEEN", "category_name": "Canteen & Bistro", "name": "Plain Beef Gourmet Pie", "price": 6.50},
        {"item_id": "ITEM_SAUSAGE_ROLL", "category_id": "CAT_CANTEEN", "category_name": "Canteen & Bistro", "name": "Jumbo Sausage Roll", "price": 5.00},

        # Events & Merchandise
        {"item_id": "ITEM_GATE_ADULT", "category_id": "CAT_EVENTS", "category_name": "Events & Gate", "name": "Weekend Event Gate Pass - Adult", "price": 20.00},
        {"item_id": "ITEM_RAFFLE_BOOK", "category_id": "CAT_EVENTS", "category_name": "Events & Gate", "name": "Meat Tray Raffle Ticket Book", "price": 10.00},
        {"item_id": "ITEM_CLUB_CAP", "category_id": "CAT_MERCH", "category_name": "Club Merchandise", "name": "Upper Horton Club Cap", "price": 25.00},
        {"item_id": "ITEM_STUBBY_HOLDER", "category_id": "CAT_MERCH", "category_name": "Club Merchandise", "name": "Club Stubby Cooler", "price": 8.00},
    ]
    df_items = pd.DataFrame(menu_items)

    orders_list = []
    line_items_list = []
    payments_list = []
    refunds_list = []

    now = datetime.now()
    
    windows = [
        (now - timedelta(days=60), now, 1.0),
        (now - timedelta(days=365 + 45), now - timedelta(days=365 - 15), 0.92)
    ]

    card_brands = ["VISA", "MASTERCARD", "EFTPOS"]
    order_seq = 1000

    for win_start, win_end, volume_scale in windows:
        curr_date = win_start
        while curr_date <= win_end:
            day_of_week = curr_date.weekday()
            is_today = (curr_date.date() == now.date())

            if is_today:
                # For today, generate orders up to current hour so Today filter is never empty
                curr_hour = max(now.hour, 1)
                num_orders = random.randint(12, 28)
                hours_pool = list(range(max(6, curr_hour - 5), curr_hour + 1))
                if not hours_pool:
                    hours_pool = [curr_hour]
            elif day_of_week == 4: # Friday
                num_orders = int(random.randint(40, 75) * volume_scale)
                hours_pool = [16, 17, 18, 19, 20, 21, 22]
            elif day_of_week == 5: # Saturday
                num_orders = int(random.randint(70, 130) * volume_scale)
                hours_pool = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
            elif day_of_week == 6: # Sunday
                num_orders = int(random.randint(25, 50) * volume_scale)
                hours_pool = [12, 13, 14, 15, 16, 17, 18]
            elif day_of_week in [1, 3]: # Tue/Thu
                num_orders = int(random.randint(10, 25) * volume_scale)
                hours_pool = [17, 18, 19, 20]
            else:
                num_orders = int(random.randint(5, 12) * volume_scale)
                hours_pool = [17, 18, 19]

            for _ in range(num_orders):
                order_seq += 1
                order_id = f"ORD_{order_seq}"
                hour = random.choice(hours_pool)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                order_time = curr_date.replace(hour=hour, minute=minute, second=second)

                # Ensure order_time is strictly in the past
                if order_time > now:
                    order_time = now - timedelta(minutes=random.randint(1, 180))

                # Distribute between primary location (or sandbox) and grounds
                loc_id = primary_loc
                if random.random() < 0.25:
                    loc_id = "LOC_UHSC_GROUNDS"

                # Weighted item selection: slow items rarely picked
                num_items = random.choices([1, 2, 3, 4, 5], weights=[0.4, 0.3, 0.15, 0.1, 0.05])[0]
                
                # Filter out slow items 95% of the time so they act as realistic dead stock
                pool = [item for item in menu_items if "SLOW" not in item["item_id"] or random.random() < 0.05]
                chosen_items = random.sample(pool, k=min(num_items, len(pool)))

                order_gross = 0.0
                order_disc = 0.0
                is_member_disc = random.random() < 0.10

                for idx, item in enumerate(chosen_items):
                    qty = random.choices([1, 2, 3, 4], weights=[0.65, 0.2, 0.1, 0.05])[0]
                    line_gross = round(item["price"] * qty, 2)
                    line_disc = round(line_gross * 0.10, 2) if is_member_disc else 0.0
                    line_net = round(line_gross - line_disc, 2)

                    order_gross += line_gross
                    order_disc += line_disc

                    line_items_list.append({
                        "line_item_id": f"LI_{order_seq}_{idx}",
                        "order_id": order_id,
                        "name": item["name"],
                        "catalog_object_id": item["item_id"],
                        "category_name": item["category_name"],
                        "quantity": float(qty),
                        "gross_sales_money": line_gross,
                        "total_discount_money": line_disc,
                        "net_sales_money": line_net,
                        "created_at": order_time
                    })

                order_gross = round(order_gross, 2)
                order_disc = round(order_disc, 2)
                order_net = round(order_gross - order_disc, 2)
                order_tax = round(order_net / 11.0, 2)

                orders_list.append({
                    "order_id": order_id,
                    "location_id": loc_id,
                    "created_at": order_time,
                    "closed_at": order_time + timedelta(minutes=random.randint(1, 5)),
                    "state": "COMPLETED",
                    "total_money": order_gross,
                    "tax_money": order_tax,
                    "discount_money": order_disc,
                    "tip_money": 0.0,
                    "net_money": order_net
                })

                # Payment
                payment_id = f"PAY_{order_seq}"
                is_cash = random.random() < 0.22
                pay_method = "CASH" if is_cash else "CARD"
                card_brand = "CASH" if is_cash else random.choice(card_brands)
                fees = 0.0 if is_cash else round(order_net * 0.016, 2)

                payments_list.append({
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "location_id": loc_id,
                    "created_at": order_time,
                    "status": "COMPLETED",
                    "amount_money": order_net,
                    "tip_money": 0.0,
                    "processing_fee_money": fees,
                    "payment_method": pay_method,
                    "card_brand": card_brand,
                    "entry_mode": "CASH" if is_cash else "CONTACTLESS"
                })

                if random.random() < 0.007:
                    refund_id = f"REF_{order_seq}"
                    refunds_list.append({
                        "refund_id": refund_id,
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "location_id": loc_id,
                        "created_at": order_time + timedelta(minutes=15),
                        "amount_money": order_net,
                        "status": "COMPLETED",
                        "reason": "Customer changed mind / return"
                    })

            curr_date += timedelta(days=1)

    return (
        df_locations,
        df_categories,
        df_items[["item_id", "category_id", "category_name", "name"]],
        pd.DataFrame(orders_list),
        pd.DataFrame(line_items_list),
        pd.DataFrame(payments_list),
        pd.DataFrame(refunds_list)
    )
