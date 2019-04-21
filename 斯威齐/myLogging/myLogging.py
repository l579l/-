import logging
class myLogging:
    def __init__(self,level=logging.DEBUG,name=__name__,file=False,):
        self.logger=logging.getLogger(name)
        self.logger.setLevel(level=level)
        formatter=logging.Formatter('%(asctime)s-%(filename)s-%(levelname)s---%(message)s')
        handler=logging.FileHandler('log.txt')
        handler.setFormatter(formatter)
        handler.setLevel(level)
        consoler=logging.StreamHandler()
        consoler.setLevel(level)
        consoler.setFormatter(formatter)
        if file:
            self.logger.addHandler(handler)
        self.logger.addHandler(consoler)
    def info(self,mess):
        self.logger.info(mess)
    def debug(self,mess):
        self.logger.DEBUG(mess)

