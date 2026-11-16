

import os
import re
import streamlit as st
from PIL import Image
from google import genai

# -----------------------------------
# AYARLAR
# -----------------------------------

MODEL = "gemini-3.1-flash-lite"

st.set_page_config(
    page_title="Akıllı Gıda Analizi",
    page_icon="🥗",
    layout="wide"
)

st.title("🥗 Akıllı Gıda Analizi")
st.write(
    "Ürün etiketlerini yapay zekâ ile analiz et, "
    "besin değerlerini incele ve ürünleri karşılaştır."
)

# -----------------------------------
# GÖRSEL HAZIRLAMA
# -----------------------------------

def prepare_image(uploaded_file):
    image = Image.open(uploaded_file)
    image = image.convert("RGB")
    image.thumbnail((1200, 1200))
    return image


# -----------------------------------
# YAPAY ZEKÂ ANALİZİ
# -----------------------------------

def analyze_with_ai(prompt, images):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "API anahtarı bulunamadı. GEMINI_API_KEY ayarını kontrol et."
        )

    client = genai.Client(api_key=api_key)

    contents = [prompt] + images

    response = client.models.generate_content(
        model=MODEL,
        contents=contents
    )

    return response.text


# -----------------------------------
# SKORU METİNDEN ÇIKARMA
# -----------------------------------

def extract_score(text, pattern):

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        score = int(match.group(1))
        return max(0, min(100, score))

    return None


# -----------------------------------
# SKOR GÖSTERME
# -----------------------------------

def show_score(score):

    if score is None:
        st.warning("Sağlık skoru metinden alınamadı.")
        return

    if score < 40:
        color = "#e74c3c"
    elif score < 60:
        color = "#f39c12"
    elif score < 75:
        color = "#f1c40f"
    else:
        color = "#2ecc71"

    st.markdown(
        f"""
        <div style="
            display:flex;
            justify-content:center;
            margin:20px 0;
        ">
            <div style="
                width:150px;
                height:150px;
                border-radius:50%;
                background:conic-gradient(
                    {color} {score * 3.6}deg,
                    #e5e7eb {score * 3.6}deg
                );
                display:flex;
                align-items:center;
                justify-content:center;
            ">
                <div style="
                    width:125px;
                    height:125px;
                    border-radius:50%;
                    background:white;
                    display:flex;
                    flex-direction:column;
                    align-items:center;
                    justify-content:center;
                ">
                    <span style="
                        font-size:36px;
                        font-weight:bold;
                        color:{color};
                    ">{score}</span>
                    <span style="font-size:14px;color:#555;">
                        / 100
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# -----------------------------------
# ANALİZ PROMPTU
# -----------------------------------

def create_prompt():

    return """
Sen bir gıda etiketi analiz asistanısın.

Gönderilen ürün görselini dikkatlice incele.

Aşağıdaki başlıklara göre Türkçe analiz yap:

1. Ürünün adı ve ürün türü
2. İçindekiler listesi
3. Şeker miktarı
4. Tuz miktarı
5. Doymuş yağ miktarı
6. Protein miktarı
7. Lif miktarı
8. Katkı maddeleri
9. İçerik kalitesi
10. Ürünün olumlu ve olumsuz yönleri

Ardından ürünün genel beslenme profilini değerlendirerek
0 ile 100 arasında bir sağlık skoru ver.

Skor verirken:
- Şeker miktarını dikkate al.
- Tuz miktarını dikkate al.
- Doymuş yağ miktarını dikkate al.
- Protein ve lif miktarını dikkate al.
- İçindekiler listesini değerlendir.
- Katkı maddelerini değerlendir.
- Ürünün türünü dikkate al. İçecekleri ve katı gıdaları
  aynı ölçütlerle değerlendirme.

Etikette okunamayan veya bulunmayan bilgileri uydurma.
Eksik bilgileri açıkça belirt ve skorun güvenilirliğinin
sınırlı olabileceğini söyle.

Cevabının en başında şu formatı kullan:

SAĞLIK SKORU: 75/100

Sonrasında ürünün detaylı analizini yaz.
Skoru 0-100 arasında tam sayı olarak ver.
"""


# -----------------------------------
# TEK ÜRÜN ANALİZİ
# -----------------------------------

def analyze_single_product(uploaded_file):

    if uploaded_file is None:
        st.info("Lütfen bir ürün etiketi görseli yükle.")
        return

    image = prepare_image(uploaded_file)

    st.image(
        image,
        caption="Yüklenen ürün etiketi",
        width=350
    )

    prompt = create_prompt()

    try:
        with st.spinner(
            "Yapay zekâ ürün etiketini inceliyor..."
        ):
            result = analyze_with_ai(prompt, [image])

        score = extract_score(
            result,
            r"SAĞLIK SKORU\s*:\s*(\d{1,3})"
        )

        st.subheader("Ürünün Sağlık Skoru")
        show_score(score)

        st.subheader("Ürün Analizi")
        st.markdown(result)

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")


# -----------------------------------
# İKİ ÜRÜN KARŞILAŞTIRMA
# -----------------------------------

def compare_products(file1, file2):

    if file1 is None or file2 is None:
        st.info("Karşılaştırmak için iki ürünün de görselini yükle.")
        return

    image1 = prepare_image(file1)
    image2 = prepare_image(file2)

    col1, col2 = st.columns(2)

    with col1:
        st.image(image1, caption="1. Ürün", width=250)

    with col2:
        st.image(image2, caption="2. Ürün", width=250)

    prompt = create_prompt()

    try:
        with st.spinner("İki ürün de analiz ediliyor..."):

            result1 = analyze_with_ai(prompt, [image1])
            result2 = analyze_with_ai(prompt, [image2])

        score1 = extract_score(
            result1,
            r"SAĞLIK SKORU\s*:\s*(\d{1,3})"
        )

        score2 = extract_score(
            result2,
            r"SAĞLIK SKORU\s*:\s*(\d{1,3})"
        )

        st.subheader("Karşılaştırma Sonuçları")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 1. Ürün")
            show_score(score1)

        with col2:
            st.markdown("### 2. Ürün")
            show_score(score2)

        st.divider()

        st.subheader("Detaylı Analizler")

        with st.expander("1. Ürün Analizi", expanded=True):
            st.markdown(result1)

        with st.expander("2. Ürün Analizi", expanded=True):
            st.markdown(result2)

        st.subheader("Karşılaştırma Yorumu")

        if score1 is not None and score2 is not None:

            if score1 > score2:
                st.success(
                    "1. ürünün sağlık skoru daha yüksek."
                )

            elif score2 > score1:
                st.success(
                    "2. ürünün sağlık skoru daha yüksek."
                )

            else:
                st.info(
                    "İki ürünün sağlık skoru eşit."
                )

        else:
            st.warning(
                "Skorlardan biri hesaplanamadığı için "
                "karşılaştırma yapılamadı."
            )

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")


# -----------------------------------
# UYGULAMA MENÜSÜ
# -----------------------------------

st.sidebar.title("Menü")

choice = st.sidebar.radio(
    "İşlem seç:",
    [
        "Tek Ürün Analizi",
        "İki Ürün Karşılaştır"
    ]
)

if choice == "Tek Ürün Analizi":

    st.header("Tek Ürün Analizi")

    uploaded_file = st.file_uploader(
        "Ürün etiketini yükle",
        type=["jpg", "jpeg", "png"]
    )

    if st.button("Ürünü Analiz Et"):
        analyze_single_product(uploaded_file)


elif choice == "İki Ürün Karşılaştır":

    st.header("İki Ürünü Karşılaştır")

    col1, col2 = st.columns(2)

    with col1:
        file1 = st.file_uploader(
            "Birinci ürünün etiketini yükle",
            type=["jpg", "jpeg", "png"],
            key="product1"
        )

    with col2:
        file2 = st.file_uploader(
            "İkinci ürünün etiketini yükle",
            type=["jpg", "jpeg", "png"],
            key="product2"
        )

    if st.button("Ürünleri Karşılaştır"):
        compare_products(file1, file2)

