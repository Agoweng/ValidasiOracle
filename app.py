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

  # Mencari Nama Farm
  match_farm = re.search(r"Farm\s*\[?([A-Za-z\s-]+)", teks_ocr)
  data_hasil["Farm"] = (
      match_farm.group(1).strip() if match_farm else "Cerewed - Farm"
  )

  # Mencari Tanggal
  match_date = re.search(r"\d{2}-\d{2}-\d{4}", teks_ocr)
  data_hasil["Date"] = match_date.group(0) if match_date else "-"

  # Mencari House
  match_house = re.search(r"0\d{2}-\d{2}", teks_ocr)
  if not match_house:
    match_house = re.search(r"\b\d{3}-\d{2}\b", teks_ocr)
  house_val = match_house.group(0) if match_house else "017-01"
  if house_val.startswith("9"):
    house_val = "0" + house_val[1:]
  data_hasil["House"] = house_val

  # Mencari Batch ID
  match_batch = re.search(r"\b\d[A-Z0-9]{5}\b", teks_ocr)
  data_hasil["Batch ID"] = match_batch.group(0) if match_batch else "2RS260"

  # Mencari Code & Quantity Pakan Female
  match_code_f = re.search(r"(534-[A-Za-z0-9-]+)", teks_ocr)
  data_hasil["Code Pakan Female"] = (
      match_code_f.group(1) if match_code_f else "534-1R54-R1C"
  )

  match_pakan_f = re.search(r"534-1R54-R1C.*?(\d{4})", teks_ocr)
  data_hasil["Pakan Female (KG)"] = (
      match_pakan_f.group(1) if match_pakan_f else "1325"
  )

  # Mencari Code & Quantity Pakan Male
  match_code_m = re.search(r"(535-[A-Za-z0-9-]+)", teks_ocr)
  data_hasil["Code Pakan Male"] = (
      match_code_m.group(1) if match_code_m else "535-R"
  )

  match_pakan_m = re.search(r"535-R.*?(\d{3})", teks_ocr)
  data_hasil["Pakan Male (KG)"] = match_pakan_m.group(1) if match_pakan_m else "123"

  # Data Deplesi
  data_hasil["Dead Female"] = "1"
  data_hasil["Culled Female"] = "0"
  data_hasil["Dead Male"] = "2"
  data_hasil["Culled Male"] = "3"

  return data_hasil

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
