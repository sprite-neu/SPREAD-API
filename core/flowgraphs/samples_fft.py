#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Samples Fft
# GNU Radio version: 3.7.13.5
##################################################

from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import fft
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.fft import window
from gnuradio.filter import firdes
from optparse import OptionParser
import pmt


class samples_fft(gr.top_block):

    def __init__(self, fft_size=512, filename="", output="testing_fft"):
        gr.top_block.__init__(self, "Samples Fft")

        ##################################################
        # Parameters
        ##################################################
        self.fft_size = fft_size
        self.filename = filename
        self.output = output

        ##################################################
        # Blocks
        ##################################################
        self.fft_vxx_0 = fft.fft_vcc(fft_size, True, (window.blackmanharris(fft_size)), True, 1)
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_gr_complex*1, fft_size)
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_gr_complex*1, filename, False)
        try:
            self.blocks_file_source_0.set_begin_tag(pmt.PMT_NIL)
        except AttributeError:
            # This is a new feature in 3.7.12 that's not backward compatible to 3.7.10.2.
            pass
        self.blocks_file_sink_2 = blocks.file_sink(gr.sizeof_gr_complex*fft_size, output+".32fc", False)
        self.blocks_file_sink_2.set_unbuffered(False)



        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source_0, 0), (self.blocks_stream_to_vector_0, 0))
        self.connect((self.blocks_stream_to_vector_0, 0), (self.fft_vxx_0, 0))
        self.connect((self.fft_vxx_0, 0), (self.blocks_file_sink_2, 0))

    def get_fft_size(self):
        return self.fft_size

    def set_fft_size(self, fft_size):
        self.fft_size = fft_size

    def get_filename(self):
        return self.filename

    def set_filename(self, filename):
        self.filename = filename
        self.blocks_file_source_0.open(self.filename, False)

    def get_output(self):
        return self.output

    def set_output(self, output):
        self.output = output
        self.blocks_file_sink_2.open(self.output+".32fc")


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "", "--fft-size", dest="fft_size", type="intx", default=512,
        help="Set fft-size [default=%default]")
    parser.add_option(
        "-f", "--filename", dest="filename", type="string", default="",
        help="Set file [default=%default]")
    parser.add_option(
        "-o", "--output", dest="output", type="string", default="testing_fft",
        help="Set outfile [default=%default]")
    return parser


def main(top_block_cls=samples_fft, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()

    tb = top_block_cls(fft_size=options.fft_size, filename=options.filename, output=options.output)
    tb.start()
    tb.wait()


if __name__ == '__main__':
    main()
