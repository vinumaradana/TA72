import paho.mqtt.client as mqtt
import json
from datetime import datetime
import requests
import time
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# MQTT Broker settings
BROKER = "broker.hivemq.com"
PORT = 1883
BASE_TOPIC = "apple/ece140/sensors"  # Load BASE_TOPIC from .env file
TOPIC = BASE_TOPIC + "/#"
print("Base topic: ", BASE_TOPIC)

# Web server settings
WEB_SERVER_URL = "http://localhost:6543/add_temp"  # Replace with your server's URL

def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker."""
    if rc == 0:
        print("Successfully connected to MQTT broker")
        client.subscribe(TOPIC)
        print(f"Subscribed to {TOPIC}")
    else:
        print(f"Failed to connect with result code {rc}")

def on_message(client, userdata, msg):
    """Callback for when a message is received."""
    try:
        payload = json.loads(msg.payload.decode())


        if msg.topic == BASE_TOPIC + '/readings':
            print(f"Payload received: {payload}")

            # Extract temperature data
            temperature = payload["temperature"]
            mac_address = payload["mac_address"]
            url = f"http://0.0.0.0:6543/add_temp"
            data = {"value": temperature, "unit": "celsius", "mac_address": mac_address}
            print(data)
            # Send POST request to your web server
            try:
                response = requests.post(
                    WEB_SERVER_URL,
                    json=data,
                    timeout=5
                )
                if response.status_code == 200:
                    print("Temperature data sent successfully!")
                else:
                    print(f"Failed to send data: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Error sending POST request: {e}")

            # Wait for 5 seconds before sending the next request
            time.sleep(5)

    except json.JSONDecodeError:
        print(f"\nReceived non-JSON message on {msg.topic}:")
        print(f"Payload: {msg.payload.decode()}")

def main():
    # Create MQTT client
    client = mqtt.Client()
    print("Creating MQTT client...")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        # Connect to MQTT broker
        client.connect(BROKER, PORT, keepalive=60)
        print("Connecting to broker...")
        client.loop_forever()  # Start the MQTT loop
        print("Started MQTT loop...")

    except KeyboardInterrupt:
        print("\nDisconnecting from broker...")
        client.loop_stop()
        client.disconnect()
        print("Exited successfully!!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()