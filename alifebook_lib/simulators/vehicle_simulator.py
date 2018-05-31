import numpy as np
import pyglet
import pymunk
import pymunk.pyglet_util
from pymunk.vec2d import Vec2d
from enum import IntEnum


class VehicleSimulator(object):
    COLLISION_TYPE = IntEnum("COLLISION_TYPE", "OBJECT VEHICLE LEFT_SENSOR RIGHT_SENSOR FEED")
    DISPLAY_MARGIN = 10
    ARENA_SIZE = 600

    # simulation setting parameters
    VEHICLE_RADIUS = 20
    SENSOR_ANGLE = np.pi * 45 / 180
    SENSOR_RANGE = 80
    SENSOR_NOISE = 0
    MOTOR_NOISE = 1.0
    FEED_COLOR = (0, 0, 0)
    FEED_ACTIVE_COLOR = (255, 0, 0)
    FEED_EATING_TIME = 100

    #def __init__(self, controll_func, obstacle_num=5, obstacle_radius=30, feed_num=0, feed_radius=5):
    def __init__(self, obstacle_num=5, obstacle_radius=30, feed_num=0, feed_radius=5):
        super(VehicleSimulator, self).__init__()
        #self.__controll_func = controll_func
        self.__left_sensor_val = 0
        self.__right_sensor_val = 0
        self.__feed_sensor_val = False
        self.__feed_touch_counter = {}

        self.__window = pyglet.window.Window(self.ARENA_SIZE+self.DISPLAY_MARGIN*2, self.ARENA_SIZE+self.DISPLAY_MARGIN*2, vsync=False)
        self.__draw_options = pymunk.pyglet_util.DrawOptions()
        self.__closed = False
        @self.__window.event
        def on_draw():
            pyglet.gl.glClearColor(255,255,255,255)
            self.__window.clear()
            self.__simulation_space.debug_draw(self.__draw_options)

        # @self.__window.event
        # def on_key_press(symbol, modifiers):
        #     if symbol == pyglet.window.key.SPACE:
        #         global running
        #         running = not running

        @self.__window.event
        def on_close():
            pyglet.app.EventLoop().exit()
            self.__closed = True

        self.__simulation_space = pymunk.Space()
        self.__simulation_space.gravity = 0, 0

        # arena
        walls = [pymunk.Segment(self.__simulation_space.static_body, (self.DISPLAY_MARGIN, self.DISPLAY_MARGIN), (self.ARENA_SIZE+self.DISPLAY_MARGIN, self.DISPLAY_MARGIN), 0),
                 pymunk.Segment(self.__simulation_space.static_body, (self.ARENA_SIZE+self.DISPLAY_MARGIN, self.DISPLAY_MARGIN), (self.ARENA_SIZE+self.DISPLAY_MARGIN, self.ARENA_SIZE+self.DISPLAY_MARGIN), 0),
                 pymunk.Segment(self.__simulation_space.static_body, (self.ARENA_SIZE+self.DISPLAY_MARGIN, self.ARENA_SIZE+self.DISPLAY_MARGIN), (self.DISPLAY_MARGIN, self.ARENA_SIZE+self.DISPLAY_MARGIN), 0),
                 pymunk.Segment(self.__simulation_space.static_body, (self.DISPLAY_MARGIN, self.ARENA_SIZE+self.DISPLAY_MARGIN), (self.DISPLAY_MARGIN, self.DISPLAY_MARGIN), 0)]
        for w in walls:
            w.collision_type = self.COLLISION_TYPE.OBJECT
            w.friction = 0.2
        self.__simulation_space.add(walls)

        # vehicle
        mass = 1
        self.vehicle_body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, self.VEHICLE_RADIUS))
        self.vehicle_body.position = self.ARENA_SIZE/2+self.DISPLAY_MARGIN, self.ARENA_SIZE/2+self.DISPLAY_MARGIN
        self.vehicle_shape = pymunk.Circle(self.vehicle_body, self.VEHICLE_RADIUS)
        self.vehicle_shape.friction = 0.2
        self.vehicle_shape.collision_type = self.COLLISION_TYPE.VEHICLE
        self.__simulation_space.add(self.vehicle_body, self.vehicle_shape)

        # left sensor
        sensor_l_s = pymunk.Segment(self.vehicle_body, (0, 0), (self.SENSOR_RANGE * np.cos(self.SENSOR_ANGLE), self.SENSOR_RANGE * np.sin(self.SENSOR_ANGLE)), 0)
        sensor_l_s.sensor = True
        sensor_l_s.collision_type = self.COLLISION_TYPE.LEFT_SENSOR
        handler_l = self.__simulation_space.add_collision_handler(self.COLLISION_TYPE.LEFT_SENSOR, self.COLLISION_TYPE.OBJECT)
        handler_l.pre_solve = self.__left_sensr_handler
        handler_l.separate = self.__left_sensr_separate_handler
        self.__simulation_space.add(sensor_l_s)

        # right sensor
        sensor_r_s = pymunk.Segment(self.vehicle_body, (0, 0), (self.SENSOR_RANGE * np.cos(-self.SENSOR_ANGLE), self.SENSOR_RANGE * np.sin(-self.SENSOR_ANGLE)), 0)
        sensor_r_s.sensor = True
        sensor_r_s.collision_type = self.COLLISION_TYPE.RIGHT_SENSOR
        handler_r = self.__simulation_space.add_collision_handler(self.COLLISION_TYPE.RIGHT_SENSOR, self.COLLISION_TYPE.OBJECT)
        handler_r.pre_solve = self.__right_sensr_handler
        handler_r.separate = self.__right_sensr_separate_handler
        self.__simulation_space.add(sensor_r_s)

        # obstacles
        OBSTACLE_RADIUS = 30
        for a in (np.linspace(0, np.pi*2, obstacle_num, endpoint=False) + np.pi/2):
            body = pymunk.Body(body_type=pymunk.Body.STATIC)
            body.position = (self.DISPLAY_MARGIN+self.ARENA_SIZE/2+self.ARENA_SIZE*0.3*np.cos(a), self.DISPLAY_MARGIN+self.ARENA_SIZE/2+self.ARENA_SIZE*0.3*np.sin(a))
            shape = pymunk.Circle(body, obstacle_radius)
            shape.friction = 0.2
            shape.collision_type = self.COLLISION_TYPE.OBJECT
            self.__simulation_space.add(shape)

        for i in range(feed_num):
            body = pymunk.Body(1, 1)
            body.position = self.DISPLAY_MARGIN + feed_radius + np.random.rand(2) * (self.ARENA_SIZE - feed_radius*2)
            shape = pymunk.Circle(body, feed_radius)
            shape.sensor = True
            shape.color = self.FEED_COLOR
            shape.collision_type = self.COLLISION_TYPE.FEED
            handler = self.__simulation_space.add_collision_handler(self.COLLISION_TYPE.VEHICLE, self.COLLISION_TYPE.FEED)
            handler.pre_solve = self.__feed_touch_handler
            handler.separate = self.__feed_separate_handler
            self.__simulation_space.add(body, shape)
            self.__feed_touch_counter[shape] = 0

    def reset(self):
        # TODO: implement reset action
        pass

    def update(self, action, body_color=None):
        if body_color is not None:
            assert len(body_color) == 3
            self.vehicle_shape.color = body_color

        self.vehicle_body.velocity = (0, 0)
        self.vehicle_body.angular_velocity = 0
        #self.vehicle_body.force = (10,10)
        #self.vehicle_body.force = (5000,5000)
        #v = self.vehicle_body.velocity
        #print(self.vehicle_body.velocity_at_world_point((0, self.VEHICLE_RADIUS)))
        #self.vehicle_body.force = 100*(50-v[0]) , 100*(50-v[1])
        #print(v)
        #self.vehicle_body.torque = 10000
        #self.flag = False
        #self.vehicle_body.force = (500000,500000)

        #target_velocity_l, target_velocity_r = 10, 0

        #current_velocity_l = self.vehicle_body.velocity_at_local_point((0, self.VEHICLE_RADIUS)).get_length()
        #current_velocity_r = self.vehicle_body.velocity_at_local_point((0, -self.VEHICLE_RADIUS)).get_length()

        #force_l = 1*(target_velocity_l - current_velocity_l)
        #force_r = 1*(target_velocity_r - current_velocity_r)
        #self.vehicle_body.apply_force_at_local_point((force_l, 0), (0, self.VEHICLE_RADIUS))
        #if force_l > 0:
            #self.vehicle_body.apply_force_at_local_point((force_l, 0), (0, self.VEHICLE_RADIUS))
        #else:
            #self.vehicle_body.apply_force_at_local_point((-force_l, 0), (0, self.VEHICLE_RADIUS))
        #self.vehicle_body.apply_force_at_local_point((force_l, 0), (0, self.VEHICLE_RADIUS))
        #self.vehicle_body.apply_force_at_local_point((force_r, 0), (0, -self.VEHICLE_RADIUS))
        #self.vehicle_body.apply_force_at_local_point((force_l, 0), (0, self.VEHICLE_RADIUS))
        #self.vehicle_body.apply_force_at_local_point((10, 0), (0, self.VEHICLE_RADIUS))
        #self.vehicle_body.apply_force_at_local_point((force_r, 0), (0, -self.VEHICLE_RADIUS))
        velocity_l, velocity_r = action[0], action[1]
        velocity_l += self.MOTOR_NOISE * np.random.randn()
        velocity_r += self.MOTOR_NOISE * np.random.randn()
        self.vehicle_body.apply_impulse_at_local_point((velocity_l*self.vehicle_body.mass, 0), (0, self.VEHICLE_RADIUS))
        self.vehicle_body.apply_impulse_at_local_point((velocity_r*self.vehicle_body.mass, 0), (0, -self.VEHICLE_RADIUS))
        lf = self.__get_lateral_velocity() * self.vehicle_body.mass
        self.vehicle_body.apply_impulse_at_local_point(-lf, (0,0))
        self.__simulation_space.step(1/100)

        pyglet.clock.tick()
        for window in pyglet.app.windows:
            self.__window.switch_to()
            self.__window.dispatch_events()
            self.__window.dispatch_event('on_draw')
            self.__window.flip()

    def get_sensor_data(self):
        sensor_data = {
            "left_distance": self.__left_sensor_val,
            "right_distance": self.__right_sensor_val,
            "feed_touching": self.__feed_sensor_val
        }
        return sensor_data

    def __feed_touch_handler(self, arbiter, space, data):
        feed = arbiter.shapes[1]
        feed.color = self.FEED_ACTIVE_COLOR
        self.__feed_touch_counter[feed] += 1
        self.__feed_sensor_val = True
        if (self.__feed_touch_counter[feed] > self.FEED_EATING_TIME):
            feed.body.position = self.DISPLAY_MARGIN + feed.radius/2 + np.random.rand(2) * (self.ARENA_SIZE - feed.radius)
        return True

    def __feed_separate_handler(self, arbiter, space, data):
        feed = arbiter.shapes[1]
        feed.color = self.FEED_COLOR
        self.__feed_touch_counter[feed] = 0
        self.__feed_sensor_val = False
        return True

    def __left_sensr_handler(self, arbiter, space, data):
        p = arbiter.contact_point_set.points[0]
        distance = self.vehicle_body.world_to_local(p.point_b).get_length()
        self.__left_sensor_val = 1 - distance / self.SENSOR_RANGE
        self.__left_sensor_val += self.SENSOR_NOISE * np.random.randn()
        return True

    def __left_sensr_separate_handler(self, arbiter, space, data):
        self.__left_sensor_val = 0
        return True

    def __right_sensr_handler(self, arbiter, space, data):
        p = arbiter.contact_point_set.points[0]
        distance = self.vehicle_body.world_to_local(p.point_b).get_length()
        self.__right_sensor_val = 1 - distance / self.SENSOR_RANGE
        self.__right_sensor_val += self.SENSOR_NOISE * np.random.randn()
        return True

    def __right_sensr_separate_handler(self, arbiter, space, data):
        self.__right_sensor_val = 0
        return True

    def __get_lateral_velocity(self):
        v = self.vehicle_body.world_to_local(self.vehicle_body.velocity + self.vehicle_body.position)
        rn = Vec2d(0, -1)
        return v.dot(rn) * rn

    def __bool__(self):
        return not self.__closed


if __name__ == '__main__':
    simulator = VehicleSimulator(obstacle_num=5)
    while simulator:
        sensor_data = simulator.get_sensor_data()
        left_wheel_speed  = 20 + 20 * sensor_data["left_distance"]
        right_wheel_speed = 20 + 20 * sensor_data["right_distance"]
        action = [left_wheel_speed, right_wheel_speed]
        simulator.update(action, body_color=(0, 0, 255))