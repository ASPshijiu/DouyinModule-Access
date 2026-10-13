import unittest
import publisher as p

K='sha256:'+'a'*64
J='sha256:'+'b'*64
class PublisherTest(unittest.TestCase):
    def policy(self):
        return dict(schema=1,revision=12,blacklist=[],whitelist=[K],administrators=[K])
    def test_validation(self):
        p.validate(self.policy())
        for changes in [dict(revision=True),dict(blacklist=[K]),dict(whitelist=['123']),dict(administrators=[]),dict(revision=2**63)]:
            with self.assertRaises(ValueError):p.validate(self.policy()|changes)
    def test_versions(self):
        a=self.policy();p.check_next(a,a)
        for b in [a|dict(revision=11),a|dict(whitelist=[J])]:
            with self.assertRaises(ValueError):p.check_next(b,a)
        p.check_next(a|dict(revision=13,whitelist=[J]),a)
    def test_canonical_order(self):
        a=self.policy()|dict(whitelist=[J,K]);b=a|dict(whitelist=[K,J])
        self.assertEqual(p.canonical(a),p.canonical(b))
        self.assertNotEqual(p.canonical(a),p.canonical(a|dict(administrators=[J])))
if __name__=='__main__':unittest.main()
