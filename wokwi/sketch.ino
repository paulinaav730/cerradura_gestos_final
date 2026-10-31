// Copia este código en tu proyecto de Wokwi (sketch.ino)
#include <ArduinoJson.h>    // Biblioteca para el formato JSON
#include <WiFi.h>           // Biblioteca para el manejo de WIFI
#include <PubSubClient.h>   // Biblioteca para el manejo del protocolo MQTT
#include <ESP32Servo.h>

const char* ssid = "Wokwi-GUEST";            // Red WiFi del simulador
const char* password = "";
const char* mqtt_server = "broker.hivemq.com";
const char* topic = "cerradura_tm_7c3f";     // Debe coincidir con TOPIC en app.py

WiFiClient espClient;
PubSubClient client(espClient);
Servo myservo;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectada");
  Serial.print("Dirección IP: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    Serial.print(F("deserializeJson() falló: "));
    Serial.println(error.f_str());
    return;
  }

  String gesto = doc["gesto"];
  Serial.print("Gesto recibido: ");
  Serial.println(gesto);

  if (gesto.equals("Abre")) {
    digitalWrite(18, HIGH);   // LED de abierto
    digitalWrite(5, LOW);
    myservo.write(180);
  }
  if (gesto.equals("Cierra")) {
    digitalWrite(5, HIGH);    // LED de cerrado
    digitalWrite(18, LOW);
    myservo.write(0);
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Esperando conexión MQTT...");
    // ID aleatorio para no chocar con otros clientes en el broker público
    String clientId = "CerraduraIA-" + String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("conectada");
      client.subscribe(topic);
    } else {
      Serial.print("falla, rc=");
      Serial.print(client.state());
      Serial.println(" Intento de nuevo en 5 segundos");
      delay(5000);
    }
  }
}

void setup() {
  pinMode(18, OUTPUT);
  pinMode(5, OUTPUT);
  myservo.setPeriodHertz(50);       // Servo estándar de 50 Hz
  myservo.attach(13, 500, 2400);
  Serial.begin(115200);
  randomSeed(micros());
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}
