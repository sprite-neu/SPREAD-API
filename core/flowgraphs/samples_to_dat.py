#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Samples To Dat
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


class samples_to_dat(gr.top_block):

    def __init__(self, fft_size=512, filename="", noise_pwr_db=-50, output="testing"):
        gr.top_block.__init__(self, "Samples To Dat")

        ##################################################
        # Parameters
        ##################################################
        self.fft_size = fft_size
        self.filename = filename
        self.noise_pwr_db = noise_pwr_db
        self.output = output

        ##################################################
        # Blocks
        ##################################################
        self.fft_vxx_0 = fft.fft_vcc(fft_size, True, (window.blackmanharris(fft_size)), True, 1)
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_gr_complex*1, fft_size)
        self.blocks_nlog10_ff_0 = blocks.nlog10_ff(10, fft_size, -noise_pwr_db)
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_gr_complex*1, filename, False)
        try:
            self.blocks_file_source_0.set_begin_tag(pmt.PMT_NIL)
        except AttributeError:
            # This is a new feature in 3.7.12 that's not backward compatible to 3.7.10.2.
            pass
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_float*fft_size, output+".dat", False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.blocks_complex_to_mag_squared_0 = blocks.complex_to_mag_squared(fft_size)



        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_nlog10_ff_0, 0))
        self.connect((self.blocks_file_source_0, 0), (self.blocks_stream_to_vector_0, 0))
        self.connect((self.blocks_nlog10_ff_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.blocks_stream_to_vector_0, 0), (self.fft_vxx_0, 0))
        self.connect((self.fft_vxx_0, 0), (self.blocks_complex_to_mag_squared_0, 0))

    def get_fft_size(self):
        return self.fft_size

    def set_fft_size(self, fft_size):
        self.fft_size = fft_size

    def get_filename(self):
        return self.filename

    def set_filename(self, filename):
        self.filename = filename
        self.blocks_file_source_0.open(self.filename, False)

    def get_noise_pwr_db(self):
        return self.noise_pwr_db

    def set_noise_pwr_db(self, noise_pwr_db):
        self.noise_pwr_db = noise_pwr_db

    def get_output(self):
        return self.output

    def set_output(self, output):
        self.output = output
        self.blocks_file_sink_0.open(self.output+".dat")


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "", "--fft-size", dest="fft_size", type="intx", default=512,
        help="Set fft-size [default=%default]")
    parser.add_option(
        "-f", "--filename", dest="filename", type="string", default="",
        help="Set file [default=%default]")
    parser.add_option(
        "-n", "--noise-pwr-db", dest="noise_pwr_db", type="intx", default=-50,
        help="Set noise_pwr_db [default=%default]")
    parser.add_option(
        "-o", "--output", dest="output", type="string", default="testing",
        help="Set outfile [default=%default]")
    return parser


def main(top_block_cls=samples_to_dat, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()

    tb = top_block_cls(fft_size=options.fft_size, filename=options.filename, noise_pwr_db=options.noise_pwr_db, output=options.output)
    tb.start()
    tb.wait()


if __name__ == '__main__':
    main()
