#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Merge2Recordings
# GNU Radio version: 3.7.13.5
##################################################

from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import pmt


class merge2recordings(gr.top_block):

    def __init__(self, file1='', file2='', outfile=''):
        gr.top_block.__init__(self, "Merge2Recordings")

        ##################################################
        # Parameters
        ##################################################
        self.file1 = file1
        self.file2 = file2
        self.outfile = outfile

        ##################################################
        # Blocks
        ##################################################
        self.blocks_file_source_0_0 = blocks.file_source(gr.sizeof_gr_complex*1, file2, False)
        try:
            self.blocks_file_source_0_0.set_begin_tag(pmt.PMT_NIL)
        except AttributeError:
            # This is a new feature in 3.7.12 that's not backward compatible to 3.7.10.2.
            pass
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_gr_complex*1, file1, False)
        try:
            self.blocks_file_source_0.set_begin_tag(pmt.PMT_NIL)
        except AttributeError:
            # This is a new feature in 3.7.12 that's not backward compatible to 3.7.10.2.
            pass
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_gr_complex*1, outfile, False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.blocks_add_xx_0 = blocks.add_vcc(1)



        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.blocks_file_source_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.blocks_file_source_0_0, 0), (self.blocks_add_xx_0, 1))

    def get_file1(self):
        return self.file1

    def set_file1(self, file1):
        self.file1 = file1
        self.blocks_file_source_0.open(self.file1, False)

    def get_file2(self):
        return self.file2

    def set_file2(self, file2):
        self.file2 = file2
        self.blocks_file_source_0_0.open(self.file2, False)

    def get_outfile(self):
        return self.outfile

    def set_outfile(self, outfile):
        self.outfile = outfile
        self.blocks_file_sink_0.open(self.outfile)


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "", "--file1", dest="file1", type="string", default='',
        help="Set file1 [default=%default]")
    parser.add_option(
        "", "--file2", dest="file2", type="string", default='',
        help="Set file2 [default=%default]")
    parser.add_option(
        "", "--outfile", dest="outfile", type="string", default='',
        help="Set outfile [default=%default]")
    return parser


def main(top_block_cls=merge2recordings, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()

    tb = top_block_cls(file1=options.file1, file2=options.file2, outfile=options.outfile)
    tb.start()
    tb.wait()


if __name__ == '__main__':
    main()
