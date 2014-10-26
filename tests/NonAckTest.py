import random
import BasicSender
from BasicSender import *
from BasicTest import *

#Hits the sender with packs that aren't acks... spooky

class NonAckTest(BasicTest):
    def handle_packet(self):
        for p in self.forwarder.in_queue:
            if p.msg_type=="ack":
                if random.choice([True,False]):
                    p.update_packet(msg_type='data', seqno=p.seqno, 
                                    data='I am a data packet', full_packet=None) 
                self.forwarder.out_queue.append(p)
            else:
                self.forwarder.out_queue.append(p)

        self.forwarder.in_queue=[]