from BasicTest import *

DROP_NO = 200
#drops the first several hundred packets, but low enough number that it shouldn't timeout given good network conditions


class DropFirstPacketsTest(BasicTest):
    
    def handle_packet(self):
        countdown = DROP_NO
        for p in self.forwarder.in_queue:
            if countdown < 0:
                countdown -= 1;
            else:
                self.forwarder.out_queue.append(p)
        
        self.forwarder.in_queue = []