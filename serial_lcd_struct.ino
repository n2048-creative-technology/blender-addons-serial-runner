
/**
Developer: Mauricio vn der Maesen

Connections: 

Arduino Uno  --> LCD 2x32
--------------------------
A4 --> SDA
A5 --> SCL
GND --> GND
5V --> VCC

**/


#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Arduino.h>

// Set the LCD address to 0x27 for a 16 chars and 2 line display
LiquidCrystal_I2C lcd(0x27, 16, 2);

#include <Arduino.h>
#include <Arduino_CRC32.h>

Arduino_CRC32 crc32;

struct MyData {
  float x1;
  float x2;
  float x3;
  float x4;
  float x5;
  float x6;
};

const char START_MARKER = '<';
const char END_MARKER = '>';
bool reading = false;
byte index = 0;
const byte dataSize = sizeof(MyData);
const byte checksumSize = sizeof(uint32_t);
const byte bufferSize = dataSize + checksumSize + 2; // Include start and end markers
char buffer[bufferSize];

void setup() {
  // Initialize the LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();

  // Initialize Serial communication
  Serial.begin(9600);
  lcd.setCursor(0, 0);
  lcd.print("Waiting for data");
}

uint32_t calculateCRC32(const uint8_t *data, size_t length) {
  // Implement a suitable CRC32 calculation or use an existing library
  return crc32.calc(data, length);

}

void loop() {
  if (Serial.available()) {
    char received = Serial.read();

    if (received == START_MARKER) {
      reading = true;
      index = 0;
    }

    if (reading) {
      buffer[index++] = received;
      if (index == bufferSize) {
        if (buffer[index - 1] == END_MARKER) {
          uint32_t receivedChecksum;
          memcpy(&receivedChecksum, buffer + dataSize + 1, checksumSize);
          uint32_t calculatedChecksum = calculateCRC32((uint8_t*)buffer + 1, dataSize);

          if (receivedChecksum == calculatedChecksum || 1) {
            MyData data;
            memcpy(&data, buffer + 1, dataSize);
            // Use the data

            displayData(data);
          }
        }
        reading = false;
        index = 0;
      }
    }
  }
}

void displayData(MyData data) {
  lcd.clear();
  
  // Display the first 3 values on the first line
  lcd.setCursor(0, 0);
  lcd.print(data.x1, 2); lcd.print(" ");
  lcd.print(data.x2, 2); lcd.print(" ");
  lcd.print(data.x3, 2);
  
  // Display the next 3 values on the second line
  lcd.setCursor(0, 1);
  lcd.print(data.x4, 2); lcd.print(" ");
  lcd.print(data.x5, 2); lcd.print(" ");
  lcd.print(data.x6, 2);
}
