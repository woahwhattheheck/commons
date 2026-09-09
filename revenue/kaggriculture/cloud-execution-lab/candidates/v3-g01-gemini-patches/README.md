# G01 Gemini patches

Apply diffs onto unpacked titan-current.tar.gz @ ba1efc8732073d7ad566ea5090fb9aa3e8b2bc33 (SHA256 3b4b083ec2647bb0e715978c2565e916da0ee94c08b234902e3a7e4d3418c320).
Copy rival_model.py e11_rival_sell.py e20_hire_shop.py next to main.py.
Flags default off: TITAN_E11_RIVAL_SELL TITAN_RIVAL_MODEL TITAN_E20_HIRE_GUARD TITAN_SHOP_ARB.
pytest test_g01_flags_off.py
Archive promotion stays with Bryce.
