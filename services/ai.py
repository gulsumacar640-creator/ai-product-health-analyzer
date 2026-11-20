import json
import os
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
MODEL_NAME = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite')

def _client():
    key = os.getenv('GEMINI_API_KEY')
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get('GEMINI_API_KEY')
        except Exception:
            pass
    if not key:
        raise RuntimeError('GEMINI_API_KEY bulunamadı. .env dosyasını kontrol edin.')
    return genai.Client(api_key=key)

def _image(data):
    im = Image.open(BytesIO(data)).convert('RGB')
    im.thumbnail((1200, 1200))
    out = BytesIO()
    im.save(out, format='JPEG', quality=88)
    return types.Part.from_bytes(data=out.getvalue(), mime_type='image/jpeg')

def _ask(prompt, images):
    client = _client()
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt] + [_image(x) for x in images],
            config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0.1),
        )
        return json.loads(response.text)
    finally:
        client.close()

SCHEMA = '''Yalnızca geçerli JSON döndür. Şema:
{"product_name":"", "product_type":"", "summary":"3-4 cümle", "ingredients":["etikette görülen içerik ve anlamı"], "pros":["2-4 açıklayıcı madde"], "cons":["2-4 açıklayıcı madde"], "usage_advice":"2-3 cümle, kişisel sağlık tavsiyesi değil", "details":[{"label":"", "value":""}], "limitations":"", "nutrition_per_100g":{"energy_kj":null,"sugars_g":null,"saturated_fat_g":null,"salt_g":null,"fiber_g":null,"protein_g":null,"fruit_veg_nuts_percent":null}, "fabric_materials":[], "care_advice":"", "estimated_score":null}.
Besin değerlerini SADECE açıkça 100 g için yazıyorsa sayısal aktar; birimleri dönüştürme veya tahmin etme. Görünmeyen değerler null. Kısa fakat yüzeysel olmayan Türkçe açıklamalar yaz. Fotoğraftan kimyasal güvenlik veya kumaş bileşimi uydurma. Yalnızca bilinen alerjenleri belirt. Besin tablosu eksikse ürünün görünen içeriğine dayalı ihtiyatlı bir 0-100 tahmini skor ver; güvenilirliği düşük olacaktır. Ürün hakkında hiçbir somut bilgi yoksa estimated_score null yap. Skor bilimsel veya klinik ölçüm değildir. Giysilerde tahmini skor yalnızca kullanım uygunluğu içindir.'''

def analyze_product(image_bytes, category, extra_info=''):
    prompt = f'''Kategori: {category}. Kullanıcı ek bilgisi: {extra_info or 'Yok'}.
Ürünün ne olduğunu açıkla, görülen içerikleri değerlendir, olumlu ve olumsuz yanları açıkla.
Gıdada şeker, doymuş yağ, tuz, lif ve protein değerlerini yalnızca etiket varsa bildir; eksik veri olduğunu açıkça belirt.
Giyside kumaş etiketine dayalı konfor, bakım ve kullanım tavsiyesi ver.
{SCHEMA}'''
    return _ask(prompt, [image_bytes])

def compare_products(image_a, info_a, image_b, info_b, category, barcode_a=None, barcode_b=None):
    def barcode_context(product):
        if not product:
            return 'Barkod verisi yok; yalnızca görseli incele.'
        n = product.get('nutriments') or {}
        allowed = ('energy-kj_100g','sugars_100g','saturated-fat_100g','salt_100g','proteins_100g','fiber_100g')
        facts = {k: product.get(k) for k in ('product_name','brands','ingredients_text_tr','ingredients_text','allergens','nutriscore_grade','quantity')}
        facts['nutriments'] = {k: n[k] for k in allowed if k in n}
        return json.dumps(facts, ensure_ascii=False)
    prompt = f'''Kategori: {category}. Birinci görsel Ürün A, ikinci görsel Ürün B.
Barkod verisi A: {barcode_context(barcode_a)}
Barkod verisi B: {barcode_context(barcode_b)}
Fotoğrafta barkod varsa ve veri tabanında bulunmuşsa bu bilgileri kullan; fotoğraftaki etiketle çelişki varsa açıkça belirt.
Barkod verisi bulunamaması analiz için engel değildir. Barkoddan ürün kimliği bulunmuşsa görselin yalnızca barkod göstermesi durumunda bile veri tabanındaki içerik ve besin bilgilerini değerlendir.
Besin değerlerini sadece fotoğraf veya barkod verisi destekliyorsa aktar; ürünün olmayan özelliklerini uydurma.
A ek bilgi: {info_a or 'Yok'}; B ek bilgi: {info_b or 'Yok'}.
İki ürünü ayrı ayrı analiz et; her biri için içerik, 2-4 avantaj, 2-4 dezavantaj ve kısa kullanım/tüketim önerisi ver.
Yalnızca şu JSON yapısını döndür: {{"product_a": {{}}, "product_b": {{}}, "criteria":[{{"criterion":"", "product_a":"", "product_b":""}}], "recommendation":"3-4 cümle dengeli karşılaştırma"}}.
product_a ve product_b nesnelerini şu şemaya göre doldur: {SCHEMA}'''
    return _ask(prompt, [image_a, image_b])


def analyze_barcode_product(product: dict):
    """Analyze database facts, not a photograph or an invented nutrient profile."""
    facts = {
        'product_name': product.get('product_name'),
        'brands': product.get('brands'),
        'ingredients_text': product.get('ingredients_text_tr') or product.get('ingredients_text') or product.get('ingredients_text_en'),
        'allergens': product.get('allergens'),
        'quantity': product.get('quantity'),
        'nutriscore_grade': product.get('nutriscore_grade'),
        'nutriments': {k: v for k, v in (product.get('nutriments') or {}).items()
                       if k in ('energy-kj_100g','sugars_100g','saturated-fat_100g',
                                'salt_100g','proteins_100g','fiber_100g')},
    }
    prompt = (
        'Aşağıdaki Open Food Facts ürün verilerini Türkçe ve anlaşılır biçimde analiz et. '
        'Yalnızca bu JSON verilerini kullan. Veri olmayan değerleri uydurma. '
        'İçindekiler listesini Türkçeye çevir, önemli bileşenlerin rolünü açıkla. '
        'Avantajlar ve dezavantajlar için 2-4 açıklayıcı madde ver, kanıt yoksa bunu belirt. '
        '2-3 cümlelik ölçülü tüketim tavsiyesi yaz. '
        'Nutri-Score varsa A-E harf derecesidir; bunu 0-100 puana çevirme. Besin değerleri eksikse yalnızca mevcut içeriklere dayanarak ihtiyatlı 0-100 tahmini skor ver; yetersiz kanıtta null ver. '
        'Alerjenleri yalnızca veride geçtiği biçimde bildir. '
        'Hastalık veya kişiye özel beslenme teşhisi koyma. '
        'Sadece şu alanları içeren geçerli JSON döndür: '
        '{"product_name":"","product_type":"","summary":"",'
        '"ingredients":[],"pros":[],"cons":[],"usage_advice":"",'
        '"details":[{"label":"","value":""}],"limitations":"","estimated_score":null,"nutrition_per_100g":{"energy_kj":null,"sugars_g":null,"saturated_fat_g":null,"salt_g":null,"fiber_g":null,"protein_g":null}}. '
        'Ürün verisi: ' + json.dumps(facts, ensure_ascii=False)
    )
    result = _ask(prompt, [])
    n = facts['nutriments']
    result['nutrition_per_100g'] = {
        'energy_kj': n.get('energy-kj_100g'),
        'sugars_g': n.get('sugars_100g'),
        'saturated_fat_g': n.get('saturated-fat_100g'),
        'salt_g': n.get('salt_100g'),
        'fiber_g': n.get('fiber_100g'),
        'protein_g': n.get('proteins_100g'),
    }
    return result
