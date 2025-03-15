#include "ECE140_WIFI.h"
#include "ECE140_MQTT.h"
#include <Adafruit_BMP085.h>  // Include the BMP085 library
#include <Wifi.h>

// Define client ID and topic prefix
#define CLIENT_ID "esp32-sensors"
#define TOPIC_PREFIX "apple/ece140/sensors"

// Initialize MQTT and WiFi objects
ECE140_MQTT mqtt(CLIENT_ID, TOPIC_PREFIX);
ECE140_WIFI wifi;

// WiFi credentials (loaded from .env file)
const char* ucsdUsername = UCSD_USERNAME;
const char* ucsdPassword = UCSD_PASSWORD;
const char* wifiSsid = WIFI_SSID;
const char* nonEnterpriseWifiPassword = NON_ENTERPRISE_WIFI_PASSWORD;

// Initialize BMP sensor
Adafruit_BMP085 bmp;

void setup() {
    Serial.begin(115200);

    // Initialize BMP sensor
    if (!bmp.begin()) {
        Serial.println("Could not find a valid BMP085 sensor, check wiring!");
        while (1) {}  // Halt if sensor is not found
    }

    // Connect to WiFi
    Serial.println("[Main] Connecting to WiFi...");
    wifi.connectToWPAEnterprise(wifiSsid, ucsdUsername, ucsdPassword);

    // Connect to MQTT Broker
    Serial.println("[Main] Connecting to MQTT...");
    if (!mqtt.connectToBroker(1883)) {
        Serial.println("[Main] Failed to connect to MQTT broker");
    }
}

void loop() {
    // Read temperature and pressure from BMP sensor
    float temperature = bmp.readTemperature();
    float pressure = bmp.readPressure() / 100.0F;  // Convert pressure to hPa
    String mac = WiFi.macAddress();


    // Create JSON payload
    String payload = "{\"temperature\": " + String(temperature) + ", \"pressure\": " + String(pressure) + ", \"mac_address\": \"" + String(mac) +"\"}";
    // Publish sensor data
    Serial.println("[Main] Publishing sensor data...");
    Serial.println(payload);
    mqtt.publishMessage("readings", payload);

    // MQTT loop and delay
    mqtt.loop();
    delay(5000);  // Send data every 5 seconds
}