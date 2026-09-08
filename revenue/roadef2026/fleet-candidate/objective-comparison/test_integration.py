# SPDX-License-Identifier: MIT
"""Portable shape/manifest tests for the same source-composition utility."""
import hashlib
import unittest
import integrate_compare as patch

class IntegrationTests(unittest.TestCase):
    def source(self):
        return 'independent prefix\n' + patch.ANCHOR + '\nunchanged quantization\n' + patch.OLD + '\nindependent suffix\n'

    def test_exact_delta_only(self):
        source=self.source(); changed=patch.apply(source)
        self.assertEqual(changed.replace(patch.function_body(), '',1).replace(patch.NEW,patch.OLD,1),source)

    def test_idempotent(self):
        changed=patch.apply(self.source());self.assertEqual(patch.apply(changed),changed)

    def test_independent_edits_survive(self):
        source=self.source().replace('independent prefix','distance and topology changes').replace('independent suffix','different neighborhood')
        changed=patch.apply(source)
        self.assertTrue(changed.startswith('distance and topology changes'))
        self.assertTrue(changed.endswith('different neighborhood\n'))

    def test_unknown_or_ambiguous_shape_rejected(self):
        for source in [self.source().replace('std::sort(before','different(before'),self.source()+patch.OLD,self.source()+patch.ANCHOR]:
            with self.subTest(source=source),self.assertRaises(ValueError):patch.apply(source)

    def test_incomplete_prior_patch_rejected(self):
        with self.assertRaises(ValueError):patch.apply(self.source().replace(patch.OLD,patch.NEW))

    def manifest(self):
        original=self.source().encode()
        return {'owner':'retained','files':[{'path':'other.py','sha256':'keep','bytes':99},{'path':'main.cpp','sha256':hashlib.sha256(original).hexdigest(),'bytes':len(original)}]},original

    def test_manifest_preserves_other_records(self):
        m,original=self.manifest();changed=patch.apply(original.decode()).encode()
        r=patch.update_manifest(m,original,changed)
        self.assertEqual(r['files'][0],m['files'][0]);self.assertEqual(r['owner'],'retained')
        self.assertEqual(r['files'][1]['sha256'],hashlib.sha256(changed).hexdigest())
        self.assertEqual(m['files'][1]['bytes'],len(original))

    def test_mismatched_manifest_rejected(self):
        m,original=self.manifest();m['files'][1]['bytes']+=1
        with self.assertRaises(ValueError):patch.update_manifest(m,original,original)

    def test_duplicate_manifest_rejected(self):
        m,original=self.manifest();m['files'].append(dict(m['files'][1]))
        with self.assertRaises(ValueError):patch.update_manifest(m,original,original)

if __name__=='__main__':unittest.main()
