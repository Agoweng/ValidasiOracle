import cv2
import numpy as np
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st

st.set_page_config(
    page_title="Oracle Form Validator", page_icon="🐔", layout="wide"
)

st.title("Validator Daily Transaction - Oracle Forms")
st.write(
    "TRIAL V.1"
    
)

# Sidebar untuk Upload Master Excel Acuan
st.sidebar.header("📁 1. Upload Master Acuan")
uploaded_excel = st.sidebar.file_uploader(
    "Pilih file Excel acuan (.xlsx)", type=["xlsx"]
)

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
    # 1. Konversi PIL Image ke OpenCV format
    img_cv = np.array(image)

    # Konversi RGB ke BGR agar sesuai format OpenCV
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    h, w, _ = img_cv.shape

    # --- TEKNIK CROP AREA SPESIFIK ---
    # Memotong bagian header (Tanggal & House) dan bagian tabel penting
    # Format: img_cv[y_mulai:y_selesai, x_mulai:x_selesai]
    crop_header = img_cv[
        int(h * 0.05) : int(h * 0.28), int(w * 0.05) : int(w * 0.50)
    ]
    crop_table = img_cv[
        int(h * 0.45) : int(h * 0.95), int(w * 0.03) : int(w * 0.95)
    ]

    # Gabungkan kembali hasil crop secara vertikal agar terbaca sebagai satu blok terfokus
    combined_crop = np.vstack([crop_header, crop_table])

    # 2. Ubah ke Grayscale
    gray = cv2.cvtColor(combined_crop, cv2.COLOR_BGR2GRAY)

    # 3. Perbesar ukuran gambar (Resizing/Upscaling) agar angka kecil tajam
    resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # 4. Thresholding (Pembersihan latar belakang)
    _, thresh = cv2.threshold(resized, 180, 255, cv2.THRESH_BINARY)

    # Jalankan OCR pada area yang sudah difokuskan dan dipotong
    custom_config = r"--oem 3 --psm 6"
    extracted_text = pytesseract.image_to_string(thresh, config=custom_config)

    st.text_area(
        "Teks yang terbaca oleh sistem (Cleaned & Focused OCR):",
        extracted_text,
        height=250,
    )

    # Validasi Dasar
    if "DAILY TRANSACTION" in extracted_text.upper() or "15-07" in extracted_text or "21-07" in extracted_text:
      st.success("✅ Area Form Utama Berhasil Dibaca Secara Spesifik!")
    else:
      st.warning(
          "⚠️ Format teks kurang jelas terbaca pada area crop."
      )

  except Exception as e:
    st.error(f"Terjadi kesalahan saat memproses OCR: {e}")

else:
  st.info(
      "👈 Silakan *upload* file Excel acuan melalui sidebar di sebelah kiri"
      " terlebih dahulu."
  )
