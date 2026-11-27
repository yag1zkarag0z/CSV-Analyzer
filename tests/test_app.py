"""Dosya/örnek geçişlerinde sütun varsayılanlarının geçerli kalmasını denetler."""

from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def widget(app, tur, anahtar):
    return next(e for e in getattr(app, tur) if e.key == anahtar or (e.key and e.key.startswith(anahtar + "_")))


class Dosya(BytesIO):
    name = "yuklenen.csv"


class ArayuzGecisTestleri(unittest.TestCase):
    def uygulama(self):
        return AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()

    def secimleri_kontrol_et(self, app):
        self.assertFalse(app.exception, [e.message for e in app.exception])
        for secim in app.multiselect:
            self.assertTrue(set(secim.value) <= set(secim.options))

    def test_yanlis_dosya_ayarlari_ornek_veriyi_etkilemez(self):
        app = self.uygulama()
        app.selectbox(key="okuma_ayrac").set_value("Noktalı virgül").run()
        app.selectbox(key="okuma_kodlama").set_value("utf-16").run()
        app.toggle(key="ornek").set_value(True).run()
        self.secimleri_kontrol_et(app)
        self.assertEqual(app.session_state["orijinal"].columns.tolist(), ["islem_id", "tarih", "kategori", "tutar"])
        self.assertEqual(app.session_state["okuma_bilgisi"]["ayrac"], ",")
        self.assertEqual(app.session_state["okuma_bilgisi"]["kodlama"], "utf-8-sig")
        widget(app, "button", "uygula").click().run()
        self.secimleri_kontrol_et(app)
        self.assertEqual(len(app.session_state["calisma"]), 3)
        self.assertEqual(app.session_state["calisma"]["tutar"].sum(), 200)

    def test_beklenen_ornek_sutunlari_yoksa_varsayilanlar_bostur(self):
        beklenmeyen = pd.DataFrame({"diger": ["a", "b"]})
        with patch("islemler.csv_oku", return_value=(beklenmeyen, {"kodlama": "utf-8-sig", "ayrac": ","})):
            app = self.uygulama()
            app.toggle(key="ornek").set_value(True).run()
            self.secimleri_kontrol_et(app)
            for anahtar in ("k_sayilar", "k_tarihler", "k_tekrar_sutunlar", "k_eksik_sutunlar"):
                self.assertEqual(widget(app, "multiselect", anahtar).value, [])
            self.assertEqual(widget(app, "selectbox", "k_eksik_yontem").value, "Koru")
            self.assertFalse(widget(app, "checkbox", "k_tekrar_sil").value)
            widget(app, "button", "uygula").click().run()
            self.secimleri_kontrol_et(app)
            self.assertEqual(len(app.session_state["calisma"]), 2)

    def test_yuklenen_dosyadan_ornege_ve_geri_gecis(self):
        dosya = Dosya(b"kod;grup;deger\n001;A;10\n002;B;20\n")
        with patch("streamlit.file_uploader", return_value=dosya):
            app = self.uygulama()
            self.secimleri_kontrol_et(app)
            self.assertEqual(app.session_state["orijinal"].columns.tolist(), ["kod", "grup", "deger"])
            app.toggle(key="ornek").set_value(True).run()
            self.secimleri_kontrol_et(app)
            self.assertEqual(widget(app, "multiselect", "k_sayilar").value, ["tutar"])
            widget(app, "button", "uygula").click().run()
            self.assertEqual(len(app.session_state["calisma"]), 3)
            app.toggle(key="ornek").set_value(False).run()
            self.secimleri_kontrol_et(app)
            self.assertEqual(widget(app, "multiselect", "k_sayilar").value, [])
            self.assertEqual(app.session_state["orijinal"]["kod"].tolist(), ["001", "002"])


if __name__ == "__main__":
    unittest.main()
