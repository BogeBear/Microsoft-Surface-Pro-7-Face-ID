# SPDX-License-Identifier: GPL-3.0-only
import unittest
from reprobe_graph import verify
A='HEADER\n- entity 1: sensor (1 pad, 1 link)\n device node name /dev/v4l-subdev15\n pad0: fmt:Y10/640x480\n -> "bridge":0 []\n\n'
B='- entity 2: bridge (1 pad, 1 link)\n device node name /dev/v4l-subdev1\n pad0: fmt:Y10/640x480\n <- "sensor":0 []\n\n'
class Tests(unittest.TestCase):
    def test_only_ids_and_entity_order_may_change(self):
        self.assertTrue(verify(A+B,'HEADER\n'+B.replace('entity 2','entity 700')+A.replace('HEADER\n','').replace('entity 1','entity 900'))['logical_graph_verified'])
    def test_entity_id_width_description_padding_only(self):
        self.assertTrue(verify(A+B,(A+B).replace('entity 1:', 'entity 10001:').replace(' device node name', '     device node name'))['logical_graph_verified'])
    def test_values_links_flags_nodes_or_headers_cannot_change(self):
        for old,new in [('640x480','320x240'),(' []',' [ENABLED]'),('bridge','other'),('subdev15','subdev16'),('HEADER','OTHER')]:
            with self.subTest(field=old):
                with self.assertRaises(ValueError):verify(A+B,(A+B).replace(old,new))
    def test_duplicates_and_missing_entity_fail(self):
        for value in [A+B+B,A+B.replace('entity 2','entity 1'),A,'HEADER']:
            with self.assertRaises(ValueError):verify(A+B,value)
if __name__=='__main__':unittest.main()
