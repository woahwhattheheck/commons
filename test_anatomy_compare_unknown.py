from __future__ import annotations

import unittest

from host import anatomy


def model(
    name: str,
    *,
    arch: object = "llama",
    hidden: object = 4096,
    tokenizer: object = "llama",
    vocab: object = 32000,
    roles: dict | None = None,
) -> dict:
    return {
        "file": name,
        "arch": arch,
        "hidden": hidden,
        "tokenizer": tokenizer,
        "vocab": vocab,
        "roles": roles or {},
    }


class AnatomyUnknownEvidenceTests(unittest.TestCase):
    def test_missing_tokenizer_and_vocab_are_not_same_token_space(self) -> None:
        result = anatomy.compare(
            model("a.gguf", tokenizer=None, vocab=None),
            model("b.gguf", tokenizer=None, vocab=None),
        )
        self.assertFalse(result["same_tokenizer"])
        self.assertEqual(result["verdict"], "TOKEN SPACE UNKNOWN — inspect tokenizer metadata before grafting")

    def test_same_tokenizer_name_without_vocab_is_still_unknown(self) -> None:
        result = anatomy.compare(
            model("a.gguf", tokenizer="llama", vocab=None),
            model("b.gguf", tokenizer="llama", vocab=None),
        )
        self.assertFalse(result["same_tokenizer"])
        self.assertTrue(result["verdict"].startswith("TOKEN SPACE UNKNOWN"))

    def test_one_missing_tokenizer_component_is_unknown(self) -> None:
        cases = (
            (None, 32000, "llama", 32000),
            ("llama", None, "llama", 32000),
            ("llama", 32000, None, 32000),
            ("llama", 32000, "llama", None),
            ("", 32000, "llama", 32000),
        )
        for a_tok, a_vocab, b_tok, b_vocab in cases:
            with self.subTest(case=(a_tok, a_vocab, b_tok, b_vocab)):
                result = anatomy.compare(
                    model("a.gguf", tokenizer=a_tok, vocab=a_vocab),
                    model("b.gguf", tokenizer=b_tok, vocab=b_vocab),
                )
                self.assertFalse(result["same_tokenizer"])
                self.assertTrue(result["verdict"].startswith("TOKEN SPACE UNKNOWN"))

    def test_unknown_architecture_is_not_same_architecture(self) -> None:
        for marker in (None, "", "?"):
            with self.subTest(marker=marker):
                result = anatomy.compare(
                    model("a.gguf", arch=marker),
                    model("b.gguf", arch=marker),
                )
                self.assertFalse(result["same_arch"])
                self.assertEqual(
                    result["verdict"],
                    "ARCHITECTURE UNKNOWN — inspect architecture metadata before grafting",
                )

    def test_known_same_family_result_is_unchanged(self) -> None:
        result = anatomy.compare(model("a.gguf"), model("b.gguf"))
        self.assertTrue(result["same_arch"])
        self.assertTrue(result["same_hidden"])
        self.assertTrue(result["same_tokenizer"])
        self.assertTrue(result["verdict"].startswith("SAME FAMILY"))

    def test_known_different_token_space_result_is_unchanged(self) -> None:
        result = anatomy.compare(
            model("a.gguf", tokenizer="llama", vocab=32000),
            model("b.gguf", tokenizer="gpt2", vocab=50257),
        )
        self.assertFalse(result["same_tokenizer"])
        self.assertTrue(result["verdict"].startswith("DIFFERENT TOKEN SPACE"))

    def test_known_same_hidden_different_arch_result_is_unchanged(self) -> None:
        result = anatomy.compare(
            model("a.gguf", arch="llama"),
            model("b.gguf", arch="mistral"),
        )
        self.assertFalse(result["same_arch"])
        self.assertTrue(result["same_hidden"])
        self.assertTrue(result["same_tokenizer"])
        self.assertTrue(result["verdict"].startswith("same hidden, different arch"))

    def test_known_cross_family_result_is_unchanged(self) -> None:
        result = anatomy.compare(
            model("a.gguf", arch="llama", hidden=4096),
            model("b.gguf", arch="mistral", hidden=8192),
        )
        self.assertFalse(result["same_arch"])
        self.assertFalse(result["same_hidden"])
        self.assertTrue(result["same_tokenizer"])
        self.assertTrue(result["verdict"].startswith("CROSS-FAMILY"))

    def test_role_matching_is_independent_of_unknown_metadata(self) -> None:
        roles_a = {
            "blk.*.attn_q.weight": {"dims": [4096, 4096]},
            "blk.*.ffn_up.weight": {"dims": [11008, 4096]},
        }
        roles_b = {
            "blk.*.attn_q.weight": {"dims": [4096, 4096]},
            "blk.*.ffn_up.weight": {"dims": [14336, 4096]},
        }
        result = anatomy.compare(
            model("a.gguf", arch="?", tokenizer=None, vocab=None, roles=roles_a),
            model("b.gguf", arch="?", tokenizer=None, vocab=None, roles=roles_b),
        )
        self.assertEqual(result["shared_roles"], 2)
        self.assertEqual(result["dim_matching_roles"], ["blk.*.attn_q.weight"])
        self.assertTrue(result["verdict"].startswith("TOKEN SPACE UNKNOWN"))

    def test_compare_output_shape_is_unchanged(self) -> None:
        result = anatomy.compare(model("a.gguf"), model("b.gguf"))
        self.assertEqual(
            set(result),
            {
                "a", "b", "same_arch", "same_hidden", "same_tokenizer",
                "verdict", "shared_roles", "dim_matching_roles",
            },
        )


if __name__ == "__main__":
    unittest.main()
