# virtual_instruments.py
import random

class AH2500:
    def __init__(self, name, address):
        pass
    
    def C(self):
        return random.uniform(0.000001, 0.0001)
    
    def L(self):
        return random.uniform(0.001, 0.1)
    
    def close(self):
        pass

class MLP:
    def __init__(self, name, address):
        pass
    def close(self):
        pass

class MercuryIPS:
    def __init__(self, name, address):
        pass
    def close(self):
        pass

class UDP:
    def __init__(self, name, address):
        pass
    def close(self):
        pass