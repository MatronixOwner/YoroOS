"""Structural guarantees for the Yoro Arc Aurorae controls."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

THEME = Path(__file__).resolve().parents[1] / 'desktop/themes/YoroArc'

class WindowThemeTest(unittest.TestCase):
    def test_distinct_complete_button_states(self):
        artwork = []
        for name in ('close', 'minimize', 'maximize', 'restore'):
            content = (THEME / (name + '.svg')).read_text()
            root = ET.fromstring(content)
            ids = {node.get('id') for node in root.iter()}
            self.assertTrue({'active-center', 'inactive-center', 'hover-center',
                             'pressed-center', 'deactivated-center'} <= ids)
            self.assertIn('rect', content)
            self.assertNotIn('<circle', content)
            artwork.append(content)
        self.assertEqual(len(set(artwork)), 4)
        self.assertIn('#f9d8dc', artwork[0])  # distinctive close hover

    def test_metadata_and_frame_exist(self):
        self.assertTrue((THEME / 'decoration.svg').is_file())
        self.assertIn('YoroArc', (THEME / 'metadata.json').read_text())
        self.assertIn('RightButtons=IAX', (THEME / 'YoroArcrc').read_text())
