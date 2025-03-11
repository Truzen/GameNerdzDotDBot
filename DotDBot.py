import discord
import requests
from bs4 import BeautifulSoup
import asyncio
import datetime
import pytz
import schedule
import time

# Discord Bot Token
TOKEN = 'YOUR_DISCORD_BOT_TOKEN'

# Website URL
WEBSITE_URL = 'YOUR_WEBSITE_URL'

# CSS selectors
PRODUCT_NAME_SELECTOR = '.store-pass-product-name'
PRODUCT_PRICE_SELECTOR = '.store-pass-product-price'
PRODUCT_MSRP_SELECTOR = '.store-pass-product-msrp'
CART_TOTAL_SELECTOR = '.cart-total-grandTotal'
ADD_TO_CART_URL = "YOUR_ADD_TO_CART_URL" #This URL is specific to the product.

# Channel ID to send the announcement
CHANNEL_ID = YOUR_DISCORD_CHANNEL_ID

# Previous product name to compare against
previous_product_name = None

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def get_product_price(session):
    try:
        cart_response = session.get("https://www.gamenerdz.com/cart.php")
        cart_response.raise_for_status()
        cart_soup = BeautifulSoup(cart_response.content, 'html.parser')
        cart_total_element = cart_soup.select_one(CART_TOTAL_SELECTOR)
        if cart_total_element:
            return cart_total_element.text.strip()
        else:
            return "Price not found in cart."
    except Exception as e:
        print(f"Error getting cart price: {e}")
        return "Error getting price."

async def check_for_new_product():
    global previous_product_name

    try:
        response = requests.get(WEBSITE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        product_name_element = soup.select_one(PRODUCT_NAME_SELECTOR)
        price_element = soup.select_one(PRODUCT_PRICE_SELECTOR)
        msrp_element = soup.select_one(PRODUCT_MSRP_SELECTOR)

        if product_name_element and price_element and msrp_element:
            current_product_name = product_name_element.text.strip()
            current_price = price_element.text.strip()
            current_msrp = msrp_element.text.strip()

            if previous_product_name is None:
                previous_product_name = current_product_name
                print(f"Initial product set: {previous_product_name}")
                return current_product_name, current_price

            if current_product_name != previous_product_name:
                previous_product_name = current_product_name
                print(f"New product found: {current_product_name}")
                if current_price == current_msrp:
                    with requests.Session() as session:
                        session.get(ADD_TO_CART_URL) #Add to cart
                        cart_price = await get_product_price(session)
                        return current_product_name, cart_price
                else:
                    return current_product_name, current_price
            else:
                print("No new product found.")
                return None, None
        else:
            print("Product details not found.")
            return None, None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching website: {e}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None

async def daily_deal_check():
    global client
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Channel with ID {CHANNEL_ID} not found.")
        return

    print("Starting daily deal check.")
    product_name, product_price = await check_for_new_product()

    if product_name:
        await channel.send(f"@channel 🎉 Deal of the Day! 🎉\n[{product_name}]({WEBSITE_URL}) - {product_price}")
        now_utc = datetime.datetime.now(pytz.utc)
        now_eastern = now_utc.astimezone(pytz.timezone('US/Eastern'))
        end_time = now_eastern.replace(hour=14, minute=0, second=0, microsecond=0)

        while now_eastern < end_time:
            await asyncio.sleep(120)
            now_utc = datetime.datetime.now(pytz.utc)
            now_eastern = now_utc.astimezone(pytz.timezone('US/Eastern'))
            new_product_name, new_product_price = await check_for_new_product()

            if new_product_name and new_product_name != product_name:
                await channel.send(f"@channel 🎉 New Deal of the Day! 🎉\n[{new_product_name}]({WEBSITE_URL}) - {new_product_price}")
                break

    else:
        await channel.send("@channel Bot didn't find a new deal today.")
    print("Finished daily deal check.")

def run_daily_check():
    asyncio.run_coroutine_threadsafe(daily_deal_check(), client.loop)

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')
    schedule.every().day.at("13:00").do(run_daily_check)

    async def scheduler():
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)

    client.loop.create_task(scheduler())

client.run(TOKEN)
