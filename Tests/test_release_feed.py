"""Guard against publishing a stale or edited feed for a verified DMG."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from release import validate_feed


class ReleaseFeedTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name)
        source = ROOT / 'Tests/fixtures/release-feed'
        self.manifest = json.loads((source / 'release.json').read_text())
        self.feed = ET.parse(source / 'appcast.xml')

    def validate(self):
        self.feed.write(self.output / 'appcast.xml')
        validate_feed(self.output, self.manifest)

    def test_real_prepared_feed(self):
        self.validate()

    def test_download_redirect_rejected(self):
        self.feed.find('./channel/item/enclosure').set('url', 'https://example.com/other.dmg')
        with self.assertRaises(RuntimeError): self.validate()

    def test_stale_build_rejected(self):
        self.feed.find('.//{http://www.andymatuschak.org/xml-namespaces/sparkle}version').text = '6'
        with self.assertRaises(RuntimeError): self.validate()

    def test_changed_signature_rejected(self):
        self.feed.find('./channel/item/enclosure').set(
            '{http://www.andymatuschak.org/xml-namespaces/sparkle}edSignature', 'invalid')
        with self.assertRaises(RuntimeError): self.validate()

    def test_extra_item_rejected(self):
        self.feed.find('./channel').append(copy.deepcopy(self.feed.find('./channel/item')))
        with self.assertRaises(RuntimeError): self.validate()


if __name__ == '__main__':
    unittest.main()
