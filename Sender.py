import sys
import getopt

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

    def get_number_of_packets_in_window(self):
        return len(self.seqno_to_packet_map)



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
        self.window = Window(500)
        self.current_sequence_number = 0
        self.done_sending = False

        if sackMode:
            raise NotImplementedError #remove this line when you implement SACK

    # Main sending loop.
    def start(self):
        # NOTE: Packet payload size should be larger than 1000 bytes (unless it is the last packet in the stream)
        # but less than 1472 bytes.

        msg_type = None
        is_chunking_done = False

        while not self.done_sending:
            # Repeatedly send packets until our window is full or until our chunking is complete (i.e. msg_type == false)
            while not self.window.window_is_full() and is_chunking_done is False:
                # Send the next packet chunk and return a boolean that represents whether we are done chunking
                is_chunking_done = self.send_next_packet_chunk()
                if is_chunking_done:
                    msg_type = 'end'
            packet_response = self.receive(0.5)

            # If we haven't received a response in 500ms, then handle timeout
            if (packet_response == None):
                self.handle_timeout()
            else:
                # TODO: Our ACK was successfully received -- what do we do in this case?
                # TODO: Probably need to update <sequence number -> ACK> map?
                # (Need to validate checksum before we do anything, in this block)
                self.handle_response(packet_response)

            # Go-Back-N Behavior:
            # If window size is 3, then:
            # Send packets 1, 2, 3 successfully
            # Packet 4 dropped, packets 5, 6 sent successfully
            # Window {4, 5, 6} times out, GBN resends 4, 5, 6
            # ACKs: 2, 3, 4, 4, 4, 7



            # Declare that we are done sending if our window is empty
            # TODO: Is there another condition where we set self.done_sending equal to False?
            if (self.window.get_number_of_packets_in_window == 0):
                self.done_sending = True
            

    '''
    Helper method that does the following things:

    1. Grabs the next file chunk from the infile
    2. Sets the msg_type appropriately, and generates a packet with the chunk
    3. Adds the packet to our window data structure
    4. Sends the packet to the receiver
    5. Increments the current sequence number by 1
    6. Returns True if the packet is completely finished being chunked, and False otherwise
    '''
    def send_next_packet_chunk(self):
        # Create next file chunk
        file_chunk = self.chunkFile(self.infile)

        # Set msg_type appropriately, based on what type the chunk is
        msg_type = 'data'
        if self.current_sequence_number == 0:
            msg_type = 'start'
        elif not file_chunk:
            msg_type = 'end'

        # Generate a packet with the current file chunk
        packet_to_send = self.make_packet(msg_type, self.current_sequence_number, file_chunk)

        # Add packet to our <sequence number -> packet> map
        self.window.add_packet_to_map(self.current_sequence_number, packet_to_send)

        # Send newly generated packet and increment the sequence number by 1
        self.send(packet_to_send)
        print("Just sent packet: " + packet_to_send)
        self.current_sequence_number += 1

        packet_finished_chunking = (msg_type == 'end')
        # Return true if we are completely done chunking (i.e. if msg_type == 'end')
        return packet_finished_chunking



    def handle_timeout(self):
        # If a timeout occurs, then GBN specifies that we resend everything in our window
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
