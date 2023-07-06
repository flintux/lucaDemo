#%% Snippet for left PC (Ctrl + Enter to run cell)
import os
import time


# %% Packages needed 
import demoInit as tp

# %% Initialize communication (run cell once is enough)
pos = tp.demo_init()


pos.set_speed(1000, 3000)


#%% Move around positioner

def moveAlpha(angle):
    pos.set_position(0, 0)
    pos.set_current(30, 0)
    wait, _ = pos.goto_relative(angle, 0)
    time.sleep(wait + 0.1)
    pos.set_current(0, 0)

def moveBeta(angle):
    pos.set_position(0, 0)
    pos.set_current(0, 50)
    _, wait = pos.goto_relative(0, angle)
    time.sleep(wait + 0.1)
    pos.set_current(0, 0)

# %%