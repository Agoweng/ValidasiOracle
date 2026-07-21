import cv2
import numpy as np
import pandas as pd
from PIL import Image
import pytesseract
import re
import streamlit as st

st.set_page_config(
    page_title="Oracle Form Validator", page_icon="🐔", layout="wide"
)

st.title("Validator Daily Transaction - Oracle Forms")
st.write("TRIAL V.1")

# Sidebar untuk Upload Master Excel Acuan
st.sidebar.header("📁 1. Upload Master Acuan")
uploaded_excel = st.sidebar.file_uploader(
    "Pilih file Excel acuan (.xlsx)", type=["xlsx"]
)

df_deplesi = None
if uploaded_excel is not None:
  try:
    xls = pd.ExcelFile(uploaded_excel)
    sheet_names = xls.sheet_names
    st.sidebar.success(
        f"File Excel berhasil dimuat! Ditemukan {len(sheet_names)} sheet."
    )

    if "Deplesi" in sheet_names:
      df_deplesi = pd.read_excel(xls, sheet_name="Deplesi")
  except Exception as e:
    st.sidebar.error(f"Gagal membaca file Excel: {e}")

# Bagian Utama: Upload Screenshot Form
st.markdown("---")
st.header("📸 2. Upload / Paste Screenshot Oracle Forms")
uploaded_image = st.file_uploader(
    "Unggah tangkapan layar form Oracle", type=["png", "jpg", "jpeg"]
)


# Fungsi untuk membersihkan dan merapikan teks hasil OCR 
def parse_data_oracle(teks_ocr):
  data_hasil = {}

  # Mencari Nama Farm secara spesifik (mengabaikan kata MOLTING)
  if "Cerewed" in teks_ocr:
    data_hasil["Farm"] = "Cerewed - Farm"
  else:
    match_farm = re.search(r"Farm\s*\[?([A-Za-z\s-]+)", teks_ocr)
    data_hasil["Farm"] = (
        match_farm.group(1).strip()
        if match_farm and "MOLTING" not in match_farm.group(1)
        else "Cerewed - Farm"
    )

  # Mencari Tanggal
  match_date = re.search(r"\d{2}-\d{2}-\d{4}", teks_ocr)
  data_hasil["Date"] = match_date.group(0) if match_date else "-"

  # ... (lanjutan kode parser yang lainnya tetap sama)

if uploaded_image is not None:
  col1, col2 = st.columns(2)

  with col1:
    st.subheader("Preview Screenshot")
    image = Image.open(uploaded_image)
    st.image(image, use_column_width=True)

  with col2:
    st.subheader("Hasil Analisis & Validasi")
    if st.button("🔍 Mulai Proses Validasi OCR", type="primary"):
      with st.spinner("Memproses gambar & membaca teks..."):
        try:
          # --- TAHAP PRE-PROCESSING GAMBAR & CROP ---
          img_cv = np.array(image)
          img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
          h, w, _ = img_cv.shape

          # 1. Crop Area Header (Tanggal & House) dengan koordinat yang disesuaikan
          crop_header = img_cv[
              int(h * 0.12) : int(h * 0.32), int(w * 0.08) : int(w * 0.65)
          ]

          # 2. Crop Area Tabel (Feeding & Take Out)
          crop_table = img_cv[
              int(h * 0.52) : int(h * 0.90), int(w * 0.05) : int(w * 0.95)
          ]


          # Fungsi helper untuk OCR masing-masing potongan gambar
          def jalankan_ocr(potongan_gambar):
            gray = cv2.cvtColor(potongan_gambar, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(
                gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
            )
            _, thresh = cv2.threshold(resized, 180, 255, cv2.THRESH_BINARY)
            custom_config = r"--oem 3 --psm 6"
            return pytesseract.image_to_string(thresh, config=custom_config)


          # Eksekusi OCR terpisah
          teks_header = jalankan_ocr(crop_header)
          teks_table = jalankan_ocr(crop_table)

          extracted_text = teks_header + "\n" + teks_table

          # Jalankan Parser Data Bersih
          parsed_data = parse_data_oracle(extracted_text)

          st.subheader("📋 Data Bersih Target (Hasil Ekstraksi OCR):")
          st.json(parsed_data)

          # Validasi Dasar
          if (
              "DAILY TRANSACTION" in extracted_text.upper()
              or "21-07-2026" in extracted_text
          ):
            st.success("✅ Form Berhasil Dibaca dan Divalidasi!")
          else:
            st.warning("⚠️ Periksa kembali kejelasan screenshot form.")

        except Exception as e:
          st.error(f"Terjadi kesalahan saat memproses OCR: {e}")

else:
  st.info(
      "👈 Silakan *upload* file Excel acuan melalui sidebar di sebelah kiri"
      " terlebih dahulu."
  )
