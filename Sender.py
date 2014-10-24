import sys
import getopt
import os

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''

class Window(object):

    def __init__(self, window_size):
        self.seqno_to_packet_map = {}
        self.seqno_to_ack_map = {}
        self.window_size = window_size

    # Adds a <sequence number -> packet> pair into map
    def add_packet_to_map(self, seqno, packet):
        self.seqno_to_packet_map[seqno] = packet

    # Removes a <sequence number -> packet> pair from map
    def remove_seqno_from_packet_map(self, seqno):
        del self.seqno_to_packet_map[seqno]

    # Adds a <sequence number -> ack> pair into map
    def add_ack_to_map(self, seqno, ack):
        self.seqno_to_ack_map[seqno] = ack

    # Removes a <sequence number -> ack> pair from map
    def remove_seqno_from_ack_map(self, seqno):
        del self.seqno_to_ack_map[seqno]

    # Gets a packet associated with a particular sequence number
    def get_packet_via_seqno(self, seqno):
        return self.seqno_to_packet_map[seqno]

    # Gets the ack associated with a particular sequence number
    def get_ack_number_via_seqno(self, seqno):
        return self.seqno_to_ack_map[seqno]

    # Returns true or false based on whether more packets can be fit into the window
    def window_is_full(self):
        return len(self.seqno_to_packet_map) >= self.window_size

    # Returns true or false based on whether a particular packet is contained in our window
    def is_seqno_contained_in_packet_map(self, seqno):
        return seqno in self.seqno_to_packet_map





class Sender(BasicSender.BasicSender):

    PACKET_SIZE = 1472
    # Entire packet contains message type, sequence number, data, and checksum
    # Message type can be either 'start', 'end', 'ack', or 'data', for a maximum of 5 bytes
    # Sequence number can be up to 32 bits = 8 bytes
    # Checksum can be up to 10 bytes
    # We also have 3 separators, '|', for a total of 3 bytes
    CHUNK_SIZE = PACKET_SIZE - 5 - 8 - 10 - 3

    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.window = Window(5)
        if sackMode:
            raise NotImplementedError #remove this line when you implement SACK

    # Main sending loop.
    def start(self):
        # NOTE: Packet payload size should be larger than 1000 bytes (unless it is the last packet in the stream)
        # but less than 1472 bytes.

        seqno = 0
        msg_type = None

        while not msg_type == 'end':
            # First, check whether the number of bytes in the infile is > 1472
            file_chunk = self.chunkFile(self.infile)

            # Set msg_type appropriately, based on what type the chunk is
            msg_type = 'data'
            if seqno == 0:
                msg_type = 'start'
            elif not file_chunk:
                msg_type = 'end'

            packet_to_send = self.make_packet(msg_type, seqno, file_chunk)
            self.send(packet_to_send)
            print("Just sent packet: " + packet_to_send)

            packet_response = self.receive(0.5)

            self.handle_response(packet_response)
            seqno = seqno + 1



    def handle_timeout(self):
        pass

    def handle_new_ack(self, ack):
        pass

    def handle_dup_ack(self, ack):
        pass

    def log(self, msg):
        if self.debug:
            print msg

    # Chunks a file into size 1472 bytes, if it is able to be chunked
    def chunkFile(self, file):
        chunk = file.read(self.CHUNK_SIZE)
        # If no chunk, will return empty string; else, returns String representation of chunk
        return chunk

    # Handles a response from the receiver.
    # This has been taken from StanfurdSender.py
    def handle_response(self,response_packet):
        if Checksum.validate_checksum(response_packet):
            print "recv: %s" % response_packet
        else:
            print "recv: %s <--- CHECKSUM FAILED" % response_packet





'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"
        print "-k | --sack Enable selective acknowledgement mode"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest, port, filename, debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
