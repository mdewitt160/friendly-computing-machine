from abc import ABCMeta, abstractmethod

class ScopeSession(metaclass=ABCMeta):

    @abstractmethod
    def Connect(self):
        pass

    @abstractmethod
    def Disconnect(self):
        pass
    
    @abstractmethod
    def Write(self, command):
        pass

    @abstractmethod
    def Read(self):
        pass

    @abstractmethod
    def ReadRaw(self, samples):
        pass