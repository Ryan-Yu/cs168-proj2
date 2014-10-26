from BasicTest import *

class DropStartAckTest(BasicTest):
    def handle_packet(self):
        for p in self.forwarder.in_queue:
            if not (p.msg_type == "ack" and p.seqno == 1):
                self.forwarder.out_queue.append(p)
        self.forwarder.in_queue=[]