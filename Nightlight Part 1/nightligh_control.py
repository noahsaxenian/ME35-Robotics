import paho.mqtt.publish as publish

broker_address='broker.hivemq.com'
topic = "nightlight/switch"
message = 'toggle'

def toggle():
    publish.single(topic, message, hostname=broker_address)