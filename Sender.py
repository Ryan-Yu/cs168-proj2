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

        # Map of <sequence number -> number of ACKs that have been received with this sequence number>
        # We use this map to determine how to handle duplicate ACKs
        self.seqno_to_ack_map = {}
        self.window_size = window_size

    # Adds a <sequence number -> packet> pair into map
    def add_packet_to_map(self, seqno, packet):
        self.seqno_to_packet_map[seqno] = (packet, False)

    # Removes a <sequence number -> packet> pair from map
    def remove_seqno_from_packet_map(self, seqno):
        del self.seqno_to_packet_map[seqno]

    # Adds a <sequence number -> number of ACKs> pair into map
    def add_acks_count_to_map(self, seqno, ack):
        self.seqno_to_ack_map[seqno] = ack

    # Removes a <sequence number -> number of ACKs> pair from map
    def remove_seqno_from_ack_map(self, seqno):
        del self.seqno_to_ack_map[seqno]

    # Gets a packet pair associated with a particular sequence number
    def get_packet_via_seqno(self, seqno):
        return self.seqno_to_packet_map[seqno][0]

    def get_packet_pair_via_seqno(self, seqno):
        return self.seqno_to_packet_map[seqno]

    # Gets the number of ACKs with a particular sequence number
    def get_ack_number_via_seqno(self, seqno):
        return self.seqno_to_ack_map[seqno]

    # Returns true or false based on whether more packets can be fit into the window
    def window_is_full(self):
        return len(self.seqno_to_packet_map) >= self.window_size

    # Returns true or false based on whether a particular sequence number is contained in our window
    def is_seqno_contained_in_packet_map(self, seqno):
        return seqno in self.seqno_to_packet_map

    # Returns true or false based on whether a particular seqno is contained in our ACK map
    def is_seqno_contained_in_ack_map(self, seqno):
        return seqno in self.seqno_to_ack_map

    def get_number_of_packets_in_window(self):
        return len(self.seqno_to_packet_map)



class Sender(BasicSender.BasicSender):

    PACKET_SIZE = 1472
    # Entire packet contains message type, sequence number, data, and checksum
    # Message type can be either 'start', 'end', 'ack', or 'data', for a maximum of 5 bytes
    # Sequence number can be up to 32 bits = 8 bytes
    # Checksum can be up to 10 bytes
    # We also have 3 separators, '|', for a total of 3 bytes

    # Piazza says that the CHUNK_SIZE can also just be set to 1400 bytes
    CHUNK_SIZE = PACKET_SIZE - 5 - 8 - 10 - 3
    # CHUNK_SIZE = 1000

    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.window = Window(5)
        self.current_sequence_number = 0
        self.done_sending = False
        self.is_chunking_done = False
        self.sackMode = sackMode

        # if sackMode:
        #     raise NotImplementedError #remove this line when you implement SACK

    # Main sending loop.
    def start(self):
        # NOTE: Packet payload size should be larger than 1000 bytes (unless it is the last packet in the stream)
        # but less than 1472 bytes.

        msg_type = None

        while not self.done_sending:
            # Repeatedly send packets until our window is full or until our chunking is complete (i.e. msg_type == false)
            while not self.window.window_is_full() and self.is_chunking_done is False:
                # Send the next packet chunk and return a boolean that represents whether we are done chunking
                self.is_chunking_done = self.send_next_packet_chunk()
                if self.is_chunking_done:
                    msg_type = 'end'

            # Receive an ACK from the Receiver
            packet_response = self.receive(0.5)

            # If we haven't received a response in 500ms, then handle timeout
            if (packet_response == None):
                self.handle_timeout()
            else:

                # Via the spec, we ignore all ACK packets with an invalid checksum
                if Checksum.validate_checksum(packet_response):
                    msg_type, seqno, data, checksum = self.split_packet(packet_response)

                    if self.sackMode:
                        seqno = int(seqno.split(";")[0])
                    # For some reason, 'seqno' is returned as a string... so we parse it into an integer
                    else:
                        seqno = int(seqno)

                    # Do ACKs have data? Probably not?
                    if (self.debug):
                        print("Received packet: %s | %d | %s | %s" % (msg_type, seqno, data, checksum))

                    # Put the current sequence number in our <sequence number -> ACKs> map, given some conditions

                    # If we haven't seen the current ACK before
                    if not self.window.is_seqno_contained_in_ack_map(seqno):
                        self.handle_new_ack(seqno)

                    # Current sequence number is NOT already contained within our map...
                    else:
                        # Increment the number of ACKs (for seqno) by 1
                        self.window.add_acks_count_to_map(seqno, self.window.get_ack_number_via_seqno(seqno) + 1)

                        # Algorithm: If ACK count is 3, then we use fast retransmit and resend the seqno with count == 3
                        if (self.window.get_ack_number_via_seqno(seqno) == 3):
                            self.handle_dup_ack(seqno)

                else:
                    # Ignore ACKs with invalid checksum
                    # Do we need to handle_timeout() if we receive an ACK with an invalid checksum?
                    self.handle_timeout()
                    pass

            # Declare that we are done sending if our window is empty AND we are done chunking
            if (self.window.get_number_of_packets_in_window() == 0 and self.is_chunking_done is True):
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

        # Update packet map
        self.window.add_packet_to_map(self.current_sequence_number, packet_to_send)

        if (self.debug):
            print("Just sent packet with sequence number %s" % self.current_sequence_number)
        self.current_sequence_number += 1

        packet_finished_chunking = (msg_type == 'end')
        # Return true if we are completely done chunking (i.e. if msg_type == 'end')
        return packet_finished_chunking



    def handle_timeout(self):
        # If a timeout occurs, then GBN specifies that we resend everything in our window
        # *This handles PACKET LOSS OF ARBITRARY SIZE* 
        # This is because we will only attempt to send n packets, where n is the size of our window
        # If we don't receive an ACK for any one packet, then it will time out, and this method will
        # resend EVERYTHING in the current window

        # i.e. in the below example, this method will send the last five packets (3, 4, 5, 6, 7), resulting
        # in ACKs of (8, 8, 8, 8, 8)

        # Assuming NO FAST RETRANSMIT
        # https://piazza.com/class/hz9lw7aquvu2r9?cid=637
        # (is this correct?)
        #       1 2 3 (dropped) 4 5 6 7 3 4 5 6 7
        # ACKS: 2 3 3           3 3 3 3 8 8 8 8 8

        if self.sackMode:
            for seqno in self.window.seqno_to_packet_map:
                current_packet_pair = self.window.get_packet_pair_via_seqno(seqno)

                # If we're in SACK mode, then resend all packets in our window that have not been received successfully
                if (current_packet_pair[1] == False):
                    self.send(current_packet_pair[0])
                    if self.debug:
                        print("We are able to resend packet %s" % seqno)
        else:
            for seqno in self.window.seqno_to_packet_map:
                current_packet = self.window.get_packet_via_seqno(seqno)

                if self.debug:
                    print("We are able to resend packet %s" % seqno)

                self.send(current_packet)

    # Called when we encounter an ACK with a sequence number that we have never seen before
    def handle_new_ack(self, ack):

        # Slide the window if it is full
        if self.window.window_is_full() or self.is_chunking_done:

            # Find all entries in map that have sequence number less than 'ack', and remove them from the map
            list_of_sequences_numbers_to_remove = []
            for seqno in self.window.seqno_to_packet_map:
                if seqno < ack:
                    list_of_sequences_numbers_to_remove.append(seqno)
            for seqno_to_remove in list_of_sequences_numbers_to_remove:
                self.window.remove_seqno_from_packet_map(seqno_to_remove)

                if self.debug:
                    print("We are shifting our window right now and removing sequence number %s from it" % seqno_to_remove)       

        # Because we haven't seen the current ACK before, put it in our ACK map
        self.window.add_acks_count_to_map(ack, 0)

        # Iterate through our packet map, and for every packet with a lower sequence number than this received ACK,
        # Update the packet pair's "received" boolean to True
        for seqno in self.window.seqno_to_packet_map:
            if seqno < ack:
                current_packet_pair = self.window.get_packet_pair_via_seqno(seqno)
                current_packet_pair[1] = True

    def handle_dup_ack(self, ack):
        if (self.debug):
            print("We are now handling the duplicate ACK %s!!!!!!!!!!!!!!!!!" % ack)

        # Grab packet that has the sequence number of 'ack', and resend it
        if (self.window.is_seqno_contained_in_packet_map(ack)):
            packet_to_resend = self.window.get_packet_via_seqno(ack)
            self.send(packet_to_resend)
            if (self.debug):
                print("We just resent ACK %s due to fast retransmit!!!!!" % ack)

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
            # print "Checksum is valid: %s" % response_packet
            print "Checksum is valid!"
        else:
            # Checksum for response packet is not valid
            # Naively, we simply just resend the packet
            self.send(self.packet_to_send)





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
