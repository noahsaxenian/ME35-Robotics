from BLE_CEEO import Yell, Listen
import time
import motor
from hub import port

def peripheral(name): 
    try:
        p = Yell(name, verbose = True)
        if p.connect_up():
            print('P connected')
            time.sleep(2)
            left = port.E
            right = port.F
            while True:
                if p.is_any:
                    message = p.read()
                    predictions = message.split(',')
                    classes = []
                    values = []
                    for i in range (0,len(predictions)):
                        class_name = predictions[i].split(': ')[0]
                        value = predictions[i].split(': ')[1]
                        classes.append(class_name)
                        values.append(float(value))
                    max_index = values.index(max(values))
                    predicted_class = classes[max_index]
                    print(predicted_class)
                    
                    if predicted_class == 'forward':
                        motor.run(left, 1000)
                        motor.run(right, 1000)
                    elif predicted_class == 'backward':
                        motor.run(left, -500)
                        motor.run(right, -500)
                    elif predicted_class == 'right':
                        motor.run(left, 100)
                        motor.run(right, -100)
                    elif predicted_class == 'left':
                        motor.run(left, -100)
                        motor.run(right, 100)
                    elif predicted_class == 'stop':
                        motor.stop(left)
                        motor.stop(right)
                    else:
                        print('unknown class')
                    
                if not p.is_connected:
                    print('lost connection')
                    break
                time.sleep(1)
    except Exception as e:
        print(e)
    finally:
        p.disconnect()
        print('closing up')

peripheral('Noah')