#!/usr/bin/env python

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation

ax = plt.axes(xlim=(0, 10), ylim=(0, 10), aspect='equal')
circle = plt.Circle((5, 5), 0.75)
ax.add_patch(circle)

def init():
    return circle,

def update(i):
    x = 5 + 3*np.sin(np.radians(i))
    y = 5 + 3*np.cos(np.radians(i))
    circle.center = (x, y)
    return circle,

anim = animation.FuncAnimation(plt.gcf(), update,
                               init_func=init,
                               interval = 20,
                               blit=True)
plt.show()