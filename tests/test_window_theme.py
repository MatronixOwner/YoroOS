"""Structural guarantees for the Yoro Arc Aurorae controls."""
import unittest
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from yoroapps import style

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

    def test_glass_titlebars_and_blur_mask(self):
        root = ET.parse(THEME / 'decoration.svg').getroot()
        nodes = {node.get('id'): node for node in root.iter() if node.get('id')}
        for element, gradient in (('path74', 'active'), ('path138', 'active'),
                                  ('path98', 'inactive'), ('path44', 'inactive')):
            self.assertEqual(nodes[element].get('fill'), f'url(#yoro-glass-{gradient})')
        for gradient in ('yoro-glass-active', 'yoro-glass-inactive'):
            stops = list(nodes[gradient])
            self.assertGreaterEqual(len(stops), 2)
            for stop in stops:
                self.assertGreater(float(stop.get('stop-opacity')), 0.5)
                self.assertLess(float(stop.get('stop-opacity')), 1.0)
        for piece in ('center', 'top', 'topleft', 'topright', 'left', 'right',
                      'bottom', 'bottomleft', 'bottomright'):
            self.assertIn('mask-' + piece, nodes)

    def test_application_glass_does_not_fade_text(self):
        for mode in ('light', 'dark'):
            sheet = style.get_stylesheet(mode=mode, glass=True)
            self.assertIn('QWidget#glassWindow', sheet)
            self.assertIn('rgba(', sheet)
            self.assertNotIn('windowOpacity', sheet)
        self.assertNotIn('QWidget#glassWindow', style.get_stylesheet(mode='light'))

    def test_metadata_and_frame_exist(self):
        self.assertTrue((THEME / 'decoration.svg').is_file())
        self.assertIn('YoroArc', (THEME / 'metadata.json').read_text())
        self.assertIn('RightButtons=IAX', (THEME / 'YoroArcrc').read_text())
