"""
File    : Motor_control.py
Author  : Sooyeon Kim, Serin Cha, Yoonsue Choi
Date    : January 04, 2024
Update  : January 19, 2024
Description : 1. Positioning motors to initial point at low speed
            :    Initial position - 150deg for each
            : 2. Motor control
            :    2-1. you can control the motor values using arrow keys or number keys
                      (1) Keyboard (Arrow key) input:
            :            Steering motion: 'up(cw)'    'down(ccw)'
            :            Yawing motion  : 'right(ccw)' 'left(cw)'

                      (2) Keyboard (Number key) input:
                         you can insert the particular motor value as a number
                         Press 's' key then you can enter the steering motor input as a number
                         Press 'y' key then you can enter the yawing motor input as a number
                         
                         --------DYNAMIXEL AX-12 information------ 
                         motor value range = 0 ~ 1023
                         motor degree range = 0 ~ 300 deg
                         initial motor value & degree = 512 & 150 deg (to control both +,- direction) 
                          --> we set this condition to 0, so you can use +,- values.
                              if you enter -100 for the motor value, the actual value goes to 412(=512 - 100) automatically
                         input motor value '1' means '0.29 degree' rotation of the motor (300deg/1023 =0.29325513)

            :    2-2. You can modify "scale_factor" variables to limit the motion
            : 3. Saving data in 10Hz
"""
import os
import sys
import time
import keyboard
import threading
import csv
import tkinter

from datetime import datetime

# 1. Data saving path + file name.csv
csv_file_path = "D:\Leeds\MotorData.csv"  

if os.name == 'nt':
    import msvcrt
    def getch():
        return msvcrt.getch().decode()
else:
    import sys, tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    def getch():
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

from dynamixel_sdk import *

######################################################
##################### VARIABLES ######################
######################################################

# 2. DEVICENAME : Check the port num from the PC Device Manager!!

# Motor setting
DXL1_ID                    = 6   # Steering(Flexion) 6
DXL2_ID                    = 1   # Yawing 1
DEVICENAME                 = 'COM11' # ex) Windows: "COM1", Linux: "/dev/ttyUSB0", Mac: "/dev/tty.usbserial-*"
BAUDRATE                   = 1000000

MOVING_SPEED               = 31  # 0~1023 x 0.111 rpm (ex-1023:114 rpm)  ************************************************원래 1023이었음, 천천히 움직이게 하기 위해서 수정함.
                                   # AX-12 : No Load Speed	59 [rev/min] (at 12V)
MOVING_SPEED_SLOW          = 50
DXL_MOVING_STATUS_THRESHOLD = 5

# Control table address
ADDR_MX_TORQUE_ENABLE      = 24
ADDR_MX_GOAL_POSITION      = 30
ADDR_MX_PRESENT_POSITION   = 36
ADDR_MX_MOVING_SPEED       = 32
ADDR_MX_PRESENT_SPEED      = 38

TORQUE_ENABLE              = 1
TORQUE_DISABLE             = 0

PROTOCOL_VERSION           = 1.0

# Data Byte Length
LEN_MX_GOAL_POSITION       = 4
LEN_MX_PRESENT_POSITION    = 4
LEN_MX_MOVING              = 1

# 3. Input value limit.
# Motor input limit (It can be editable)
steering_angle_limit_min = -305 # about -90 deg rotation of the disk
steering_angle_limit_max = 305 # about +90 deg rotation of the disk
yawing_angle_limit = 100 # about +-30 deg rotation of the disk

# Motor initial position (150 deg for each motor)
dxl1_init = 512
dxl2_init = 512

######################################################
################ FUNCTION AND THREAD #################
######################################################
exit_flag = False

# Initialize global variables
dxl1_goal_position, dxl2_goal_position = 0, 0
dxl1_goal_angle,    dxl2_goal_angle    = 0, 0
dxl1_present_position, dxl2_present_position = 0, 0

### Motor control input function

### at present, keyboard input
# 4. Scaling factor between motor value - tip angle (needle의 angle 대비 control input 값의 비율)
#    control_input = scale_factor * steering angle
#Scaling factor to limit the range of motion (steering and yawing)

scale_factor_steering = 1
scale_factor_yawing   = 1

try:
    # Python 2
    input_func = raw_input
except NameError:
    # Python 3
    input_func = input


def get_Steering_motor_input():
    while not exit_flag:
        try:
            # Accept numeric motor input (숫자 입력을 받음)
            user_input = input_func("Steering motor input: ")

            #  Check whether the entered value is convertable to a number (입력된 값이 숫자로 변환 가능한지 확인)
            number = int(user_input)

            # Returns if it can be converted to a numner (숫자로 변환이 가능하면 반환)
            return number
        except ValueError:
            # Exception handling when conversion fails (변환 실패 시 예외 처리)
            print("Please enter a valid number.")
            
            
def get_Yawing_motor_input():
    while not exit_flag:
        try:
            # Accept numeric motor input (숫자 입력을 받음)
            user_input = input_func("Yawing motor input: ")

            #  Check whether the entered value is convertable to a number (입력된 값이 숫자로 변환 가능한지 확인)
            number = int(user_input)

            # Returns if it can be converted to a numner (숫자로 변환이 가능하면 반환)
            return number
        except ValueError:
            # Exception handling when conversion fails (변환 실패 시 예외 처리)
            print("Please enter a valid number.")
            

# Motor status display

window=tkinter.Tk()

window.title("Motor Status Display")
window.geometry("300x150+100+100")
window.resizable(False, False)

label1 = tkinter.Label(window,text='Steering motor : ')

x_pos = 20
y_pos = 30
label1.place(x=x_pos,y=y_pos)

label2 = tkinter.Label(window,text='Yawing motor  : ')
label2.place(x=x_pos,y=y_pos+40)

entry1 = tkinter.Entry(window)
entry2 = tkinter.Entry(window)

entry1.place(x=x_pos+100,y=y_pos)
entry2.place(x=x_pos+100,y=y_pos+40)



  
        

            

def input_data():
    global dxl1_goal_angle, dxl2_goal_angle
    while not exit_flag:
        time.sleep(0.02) # unit : sec (20ms)
                         # 0.001부터 가능하나, 사람이 1ms으로 제어할 수 있을 정도로 예민하지 않음을 고려할 것
                         # 보통 사람의 반응시간은 200~250 ms
                         
        if keyboard.is_pressed('s'):
            # By pressing the 'x' key on your keyboard, you can enter steering motor input as a number.
            dxl1_goal_angle = get_Steering_motor_input()
        if keyboard.is_pressed('y'):
            # By pressing the 'y' key on your keyboard, you can enter yawing motor input as a number.
            dxl2_goal_angle = get_Yawing_motor_input()
        
        
        if keyboard.is_pressed('up'):
            dxl1_goal_angle += 1
        if keyboard.is_pressed('down'):
            dxl1_goal_angle -= 1
        if keyboard.is_pressed('right'):
            dxl2_goal_angle += 1
        if keyboard.is_pressed('left'):
            dxl2_goal_angle -= 1
        
    
        # Ensure dxl_goal_angle stays within limits (unit: control input)
        dxl1_goal_angle = max(min(dxl1_goal_angle, scale_factor_steering * steering_angle_limit_max),
                            scale_factor_steering * steering_angle_limit_min)
        dxl2_goal_angle = max(min(dxl2_goal_angle, scale_factor_yawing * yawing_angle_limit),
                            -scale_factor_yawing * yawing_angle_limit)


### Thread for data logging
        
def log_data():
    global dxl1_goal_position, dxl2_goal_position
    global dxl1_present_position, dxl2_present_position
    with open(csv_file_path, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Time', 'Steering[deg]', 'Yawing[deg]', 
                             'Servo1(in)', 'Servo2(in)', 'Servo1(out)', 'Servo2(out)'])

        while not exit_flag:
            csv_writer.writerow([datetime.now(), dxl1_goal_angle, dxl2_goal_angle, 
                                 dxl1_goal_position, dxl2_goal_position,
                                 dxl1_present_position, dxl2_present_position])
            time.sleep(0.1) # 10Hz data logging
        else:
            csv_file.close()

## Mapping function
def mapping(value, in_min, in_max, out_min, out_max):
    normalized_value = (value - in_min) / (in_max - in_min)
    mapped_value = normalized_value * (out_max - out_min) + out_min
    return mapped_value


######################################################
################# MOTER CONNECTION ###################
######################################################
        
# Dynamixel setting
portHandler = PortHandler(DEVICENAME)
packetHandler = PacketHandler(PROTOCOL_VERSION)

# Open port
if portHandler.openPort():
    print("Succeeded to open the port")
else:
    print("Failed to open the port")
    print("Press any key to terminate...")
    getch()
    quit()

# Set port baudrate
if portHandler.setBaudRate(BAUDRATE):
    print("Succeeded to change the baudrate")
else:
    print("Failed to change the baudrate")
    print("Press any key to terminate...")
    getch()
    quit()

# Enable Dynamixel Torque
dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL1_ID, ADDR_MX_TORQUE_ENABLE, TORQUE_ENABLE)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
else:
    print("Dynamixel#%d has been successfully connected" % DXL1_ID)

dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL2_ID, ADDR_MX_TORQUE_ENABLE, TORQUE_ENABLE)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
else:
    print("Dynamixel#%d has been successfully connected" % DXL2_ID)


######################################################
##################### EXECUTION ######################
######################################################
## 1. Motor Positioning
print("====================STEP 1=====================")
print("====Positioning Motors to Initial Position=====")

# Write moving speed : to move slowly...
dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, DXL1_ID, ADDR_MX_MOVING_SPEED, MOVING_SPEED_SLOW)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, DXL2_ID, ADDR_MX_MOVING_SPEED, MOVING_SPEED_SLOW)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

# Write goal position : initial position = 512 control input
dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, DXL1_ID, ADDR_MX_GOAL_POSITION, dxl1_init)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, DXL2_ID, ADDR_MX_GOAL_POSITION, dxl2_init)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

while True:
    # Read present position
    dxl1_present_position, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, DXL1_ID, ADDR_MX_PRESENT_POSITION)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))
    dxl2_present_position, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, DXL2_ID, ADDR_MX_PRESENT_POSITION)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))        

    if not ((abs(dxl1_init - dxl1_present_position) > DXL_MOVING_STATUS_THRESHOLD) and (abs(dxl1_init - dxl2_present_position) > DXL_MOVING_STATUS_THRESHOLD)):
            break

######################################################
time.sleep(0.2)
print("")
user_input = input(">> Enter to confirm")
print("")


## 2. Motor Control
print("====================STEP 2=====================")
print("==============Press 'esc' to quit==============")
print(" ")
print("==============(1) Arrow key control============")
print("====Steering motion: 'up(cw)''down(ccw)'=======")
print("====Yawing motion  : 'right(ccw)''left(cw)'====")
print(" ")
print("==============(2) Num key control==============")
print("====Steering motion:  Press 's' key & ")
print("                      Enter the motor value====")
print("====Yawing motion:  Press 'y' key & ")
print("                    Enter the motor value======")
print(" ")


# Thread for data logging
log_thread = threading.Thread(target=log_data)
log_thread.start()

# Thread for control input
input_thread = threading.Thread(target=input_data)
input_thread.start()

# Write moving speed to maximize the response
dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, DXL1_ID, ADDR_MX_MOVING_SPEED, MOVING_SPEED)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, DXL2_ID, ADDR_MX_MOVING_SPEED, MOVING_SPEED)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))


running = True

while running:
    
    # Offest correction
    dxl1_goal_position = dxl1_init - int(dxl1_goal_angle) # + is cw
    dxl2_goal_position = dxl2_init - int(dxl2_goal_angle) # + is ccw
    # dxl1_STEPSIZE = int(dxl1_goal_angle)
    
    # for i in range(1,dxl1_STEPSIZE):
    #     time.sleep(0.05)
    #     dxl1_goal_position = dxl1_init - int(i) # + is cw
    # window.update_idletasks()
    # window.update()    
    
    # Write goal position
    dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, DXL1_ID, ADDR_MX_GOAL_POSITION, dxl1_goal_position)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))
    dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, DXL2_ID, ADDR_MX_GOAL_POSITION, dxl2_goal_position)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))
        
    # Read Dynamixel present position
    dxl1_present_position, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, DXL1_ID, ADDR_MX_PRESENT_POSITION)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))

    dxl2_present_position, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, DXL2_ID, ADDR_MX_PRESENT_POSITION)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))
        
    # Update the motor value display ()
    
    entry1.delete(0,"end")
    entry1.insert(0,dxl1_init - dxl1_present_position)
    entry2.delete(0,"end")
    entry2.insert(0,dxl2_init - dxl2_present_position)
    
    window.update_idletasks()
    window.update()  
    

    
    # Print
    # print("[User] Steering: %d, Yawing: %d || [Motor] Steering: %d, Yawing: %d" % (dxl1_goal_angle ,dxl2_goal_angle, dxl1_present_position, dxl2_present_position))
      ##print("Steering: %d, Yawing: %d" %(dxl1_goal_angle, dxl2_goal_angle))################

    ## Program 강제 종료
    if keyboard.is_pressed('esc'):
        print("Quit the program")
        exit_flag = True
        running   = False
        break

    
## Quit the Program
# Disable Dynamixel Torque
dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL1_ID, ADDR_MX_TORQUE_ENABLE, TORQUE_DISABLE)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL2_ID, ADDR_MX_TORQUE_ENABLE, TORQUE_DISABLE)
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))

# Close port
portHandler.closePort()

sys.exit(0)