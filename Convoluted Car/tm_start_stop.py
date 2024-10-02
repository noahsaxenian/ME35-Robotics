from pyscript.js_modules import teach, pose, mqtt_library
import time

topic = "ME35-24/carstartstop"

# initialize MQTT client
client = mqtt_library.myClient
client.init()

def run():
    # function to send run command
    message = 'run'
    client.publish(topic, message)

def stop():
    # function to send stop command
    message = 'stop'
    client.publish(topic, message)


def run_model(URL2):
    s = pose.s
    s.URL2 = URL2
    s.init()

def get_predictions():
    # find the predictions by ElementID and parse
    predictions = []
    container = document.getElementById('label-container')
    if container:
        divs = container.getElementsByTagName('div')
        for i in range (0,divs.length):
            divElement = divs[i].textContent
            predictions.append(divElement)
    return predictions


run_model("https://teachablemachine.withgoogle.com/models/wovVCX6Nw/")

while True:
    predictions = get_predictions()
    
    # parse the predictions array to find the class with max value
    classes = []
    values = []
    if predictions: 
        for i in range(0, len(predictions)):
            class_name = predictions[i].split(': ')[0]
            value = predictions[i].split(': ')[1]
            classes.append(class_name)
            values.append(float(value))
        max_index = values.index(max(values))
        predicted_class = classes[max_index]
        
        # act according to predicted class
        if predicted_class == "start":
            run()
        elif predicted_class == "stop":
            stop()
        else:
            print(predicted_class)
    time.sleep(1)