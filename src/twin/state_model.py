class TrafficState:
    def __init__(self):
        self.density = {}
        self.speed = {}
        self.queue = {}

    def update(self, density, speed, queue):
        self.density = density
        self.speed = speed
        self.queue = queue