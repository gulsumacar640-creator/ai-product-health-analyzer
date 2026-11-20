import streamlit as st
from services.ai import analyze_product, compare_products, analyze_barcode_product
from services.barcode import lookup_barcode, decode_barcode
from services.scoring import score_product

st.set_page_config(page_title='Akıllı Ürün Analiz Platformu', page_icon='🔎', layout='wide')
st.markdown('''<style>
.block-container {max-width:1050px; padding-top:1.4rem;}
.hero {background:linear-gradient(120deg,#17304b,#315c70);padding:24px;border-radius:16px;color:white;margin-bottom:18px;}
.hero h1{color:white;font-size:clamp(1.4rem,4vw,2.3rem);}
@media(max-width:640px){.block-container{padding-left:.8rem;padding-right:.8rem;}}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🔎 Akıllı Ürün Analiz Platformu</h1><p>Yiyecek ve giysileri bilinçli değerlendirin.</p></div>', unsafe_allow_html=True)

def get_image(label, key):
    source = st.radio(f'{label} kaynağı', ['Galeriden yükle', 'Kamerayla çek'], horizontal=True, key=key+'_source')
    if source == 'Kamerayla çek':
        return st.camera_input(label, key=key+'_camera')
    return st.file_uploader(label, type=['jpg','jpeg','png','webp'], key=key+'_upload')

def score_ring(score):
    if score is None:
        st.info('📊 Sayısal skor hesaplanamadı — eksik veya doğrulanmamış veri.')
        return
    score = max(0,min(100,int(score)))
    color = '#e74c3c' if score < 40 else '#f39c12' if score < 60 else '#eab308' if score < 75 else '#2ecc71'
    st.markdown(f'''<div style="width:150px;height:150px;border-radius:50%;background:conic-gradient({color} {score*3.6}deg,#e5e7eb 0);display:grid;place-items:center;margin:12px auto"><div style="width:125px;height:125px;border-radius:50%;background:#fff;color:{color};display:grid;place-items:center;font-weight:bold;font-size:30px">{score}<span style="font-size:12px;margin-top:-36px">/100</span></div></div>''', unsafe_allow_html=True)

def show_result(result, category):
    st.subheader(result.get('product_name') or 'Ürün')
    st.caption(result.get('product_type') or category)
    st.markdown('#### 🔎 Ürün hakkında')
    st.write(result.get('summary') or 'Ürün tanımı bulunamadı.')
    st.markdown('#### 📊 Genel değerlendirme')
    score, reason = score_product(result, category)
    score_ring(score)
    st.caption('Skor güvenilirliği: ' + reason)
    st.markdown('#### 🧾 İçerik analizi')
    ingredients = result.get('ingredients') or []
    if ingredients:
        for item in ingredients:
            st.write('• '+str(item))
    else:
        st.info('İçerik bilgisi okunamadı. Etiketin daha net fotoğrafını ekleyin.')
    left, right = st.columns(2)
    with left:
        st.markdown('#### ✅ Avantajları')
        for item in result.get('pros') or ['Yeterli veri yok']:
            st.write('• '+str(item))
    with right:
        st.markdown('#### ⚠️ Dezavantajları')
        for item in result.get('cons') or ['Yeterli veri yok']:
            st.write('• '+str(item))
    st.markdown('#### 💡 Tüketim / kullanım tavsiyesi')
    st.info(result.get('usage_advice') or result.get('care_advice') or 'Yeterli veri yok.')
    with st.expander('📋 Detaylı inceleme'):
        for item in result.get('details') or []:
            if isinstance(item,dict):
                st.write(f"**{item.get('label','Bilgi')}:** {item.get('value','')}")
        if category == 'Yiyecek':
            n = result.get('nutrition_per_100g') or {}
            labels = {'energy_kj':'Enerji (kJ)','sugars_g':'Şeker (g)','saturated_fat_g':'Doymuş yağ (g)','salt_g':'Tuz (g)','fiber_g':'Lif (g)','protein_g':'Protein (g)'}
            for key,label in labels.items():
                st.write(f'**{label}:** {n.get(key) if n.get(key) is not None else "Etikette okunamadı"}')
    if result.get('limitations'):
        st.caption('⚠️ '+str(result['limitations']))

category = st.radio('Ürün kategorisi', ['Yiyecek','Giysi'], horizontal=True, key='global_category')
st.caption('Yiyecek ve giysi için ayrı inceleme, barkod ve karşılaştırma alanları.')
if st.session_state.get('_last_category') != category:
    st.session_state.pop('barcode_result', None)
    st.session_state.pop('clothing_barcode_analysis', None)
    st.session_state['_last_category'] = category
page = st.radio('Bölüm', [f'{category} İnceleme', f'{category} Karşılaştırma', f'{category} Barkod', 'Analiz Geçmişi'], horizontal=True, label_visibility='collapsed', key='section_'+category)
if page == f'{category} İnceleme':
    uploaded = get_image('Ürün görseli', 'single')
    extra = st.text_area('Etiket veya ürün hakkında ek bilgi (isteğe bağlı)', height=75)
    if uploaded:
        st.image(uploaded, caption='Analiz edilecek görsel', width=330)
    if st.button('Yapay zekâ ile analiz et', type='primary', disabled=uploaded is None, use_container_width=True):
        with st.spinner('Ürün inceleniyor...'):
            try:
                result = analyze_product(uploaded.getvalue(), category, extra)
                st.session_state.setdefault('history', []).append((category,result))
                show_result(result,category)
            except Exception as e:
                st.error(f'Analiz sırasında hata oluştu: {e}')
elif page == f'{category} Karşılaştırma':
    a,b = st.columns(2)
    with a:
        st.markdown('### Ürün A')
        fa = get_image('Ürün A görseli','a')
        ia = st.text_input('Ürün A ek bilgisi')
        if fa: st.image(fa,width=280)
    with b:
        st.markdown('### Ürün B')
        fb = get_image('Ürün B görseli','b')
        ib = st.text_input('Ürün B ek bilgisi')
        if fb: st.image(fb,width=280)
    if st.button('Ürünleri karşılaştır', type='primary', disabled=not(fa and fb), use_container_width=True):
        with st.spinner('Karşılaştırılıyor...'):
            try:
                # Yiyecek fotoğraflarında önce barkod dene; yoksa normal etiket analizi yap.
                # Görseller her durumda Gemini'ye gönderilir; barkod verisi ek bağlamdır.
                facts_a, facts_b = None, None
                if category == 'Yiyecek':
                    for side, uploaded in [('A', fa), ('B', fb)]:
                        try:
                            code = decode_barcode(uploaded.getvalue())
                            if code:
                                product = lookup_barcode(code)
                                if product:
                                    if side == 'A': facts_a = product
                                    else: facts_b = product
                                    st.success(f'Ürün {side}: {code} barkodu okundu — {product.get("product_name") or "Ürün bulundu"}')
                                else:
                                    st.info(f'Ürün {side}: Barkod okundu fakat veri tabanında bulunamadı; fotoğraf analiz edilecek.')
                        except Exception as barcode_error:
                            st.caption(f'Ürün {side}: Barkod sorgusu yapılamadı ({barcode_error}); fotoğraf analizi devam ediyor.')
                result = compare_products(fa.getvalue(),ia,fb.getvalue(),ib,category,
                                          barcode_a=facts_a, barcode_b=facts_b)
                a,b = st.columns(2)
                with a:
                    st.markdown('### Ürün A')
                    show_result(result.get('product_a') or {},category)
                with b:
                    st.markdown('### Ürün B')
                    show_result(result.get('product_b') or {},category)
                st.markdown('### Genel karşılaştırma')
                for row in result.get('criteria') or []:
                    st.write(f"**{row.get('criterion','Kriter')}** — A: {row.get('product_a','?')} | B: {row.get('product_b','?')}")
                st.info(result.get('recommendation') or 'Karşılaştırma önerisi yok.')
            except Exception as e:
                st.error(f'Karşılaştırma sırasında hata oluştu: {e}')
elif page == f'{category} Barkod':
    st.subheader('📷 '+category+' barkod sorgulama')
    if category == 'Giysi':
        st.caption('Giysi barkodunu fotoğraflayın veya numarasını girin. Barkod numarası tek başına kumaş bilgisini göstermez; giysi etiketi fotoğrafını da ekleyebilirsiniz.')
        mode = st.radio('Barkod giriş yöntemi', ['Fotoğraf yükle','Kamerayla çek','Numarayı yaz'], horizontal=True, key='clothing_barcode_mode')
        photo = None
        if mode == 'Fotoğraf yükle':
            photo = st.file_uploader('Giysi barkod veya etiket fotoğrafı', type=['jpg','jpeg','png','webp'], key='clothing_barcode_upload')
        elif mode == 'Kamerayla çek':
            photo = st.camera_input('Giysi barkod veya etiket fotoğrafı', key='clothing_barcode_camera')
        code = None
        if photo:
            st.image(photo, width=320)
            try:
                code = decode_barcode(photo.getvalue())
                if code: st.success('Okunan barkod: '+code)
                else: st.info('Barkod okunamadı. Etiket fotoğrafıyla analiz yapabilir veya numarayı yazabilirsiniz.')
            except Exception as exc:
                st.warning('Barkod çözümleme başarısız: '+str(exc))
        manual = st.text_input('Barkod numarası (varsa)', value=code or '', key='clothing_code_'+str(code or ''))
        st.caption('Giysi ürün veri tabanı bağlı değil. Barkod numarasından marka, model veya kumaş içeriği uydurulmaz.')
        if st.button('Giysi etiketini analiz et', type='primary', disabled=photo is None, key='clothing_analyze_barcode'):
            try:
                with st.spinner('Giysi etiketi inceleniyor...'):
                    result = analyze_product(photo.getvalue(), 'Giysi', 'Barkod numarası (ürün kimliği doğrulanmamış): '+manual+'. Yalnızca görselde okunabilen malzeme, bakım ve marka bilgilerini kullan. Barkoddan ürün özellikleri uydurma.')
                st.session_state['clothing_barcode_analysis'] = result
            except Exception as exc:
                st.error('Giysi analizi başarısız: '+str(exc))
        if st.session_state.get('clothing_barcode_analysis'):
            show_result(st.session_state['clothing_barcode_analysis'], 'Giysi')
    else:
        st.caption('Gıda ürününün barkod fotoğrafını yükleyin, kamerayla çekin veya numarasını yazın.')
        method = st.radio(
            'Barkod giriş yöntemi',
            ['Fotoğraf yükle', 'Kamerayla çek', 'Numarayı yaz'],
            horizontal=True,
        )
        detected = None
        if method == 'Numarayı yaz':
            barcode = st.text_input('Barkod numarası (8–14 rakam)', key='manual_barcode')
        else:
            if method == 'Fotoğraf yükle':
                uploaded_barcode = st.file_uploader(
                    'Barkod fotoğrafını yükle',
                    type=['png', 'jpg', 'jpeg', 'webp'],
                    key='barcode_photo',
                )
            else:
                uploaded_barcode = st.camera_input(
                    'Barkodu net ve yakın çekin',
                    key='barcode_camera',
                )
            barcode = ''
            if uploaded_barcode is not None:
                st.image(uploaded_barcode, caption='Barkod görseli', width=320)
                try:
                    detected = decode_barcode(uploaded_barcode.getvalue())
                    if detected:
                        st.success(f'Okunan barkod: {detected}')
                    else:
                        st.warning('Barkod okunamadı. Daha net fotoğraf deneyin veya numarayı yazın.')
                except Exception as exc:
                    st.warning(f'Otomatik okuma yapılamadı: {exc}')
            barcode = st.text_input(
                'Barkod numarası (gerekirse düzeltin veya elle girin)',
                value=detected or '',
                key=f'barcode_override_{method}_{detected or "none"}',
            )
        if st.button('Ürünü sorgula', type='primary', disabled=not barcode.strip()):
            try:
                with st.spinner('Ürün veri tabanında aranıyor...'):
                    p = lookup_barcode(barcode)
                st.session_state['barcode_result'] = {'barcode': barcode, 'product': p, 'analysis': None}
            except Exception as exc:
                st.error(f'Barkod sorgulanamadı: {exc}')

        saved = st.session_state.get('barcode_result')
        if saved:
            p = saved['product']
            if p:
                st.success('Ürün bulundu!')
                st.markdown('### ' + (p.get('product_name') or 'Ürün'))
                st.write('**Marka:**', p.get('brands') or 'Belirtilmemiş')
                st.write('**Miktar:**', p.get('quantity') or 'Belirtilmemiş')
                grade = (p.get('nutriscore_grade') or '').upper()
                if grade in ('A','B','C','D','E'):
                    st.markdown(f'**Nutri-Score: {grade}** (A–E beslenme profili derecesi; 0–100 puan değildir)')
                else:
                    st.caption('Nutri-Score verisi bulunamadı.')
                with st.expander('Veri tabanındaki orijinal bilgiler'):
                    st.write('**İçindekiler:**', p.get('ingredients_text_tr') or p.get('ingredients_text') or 'Veri yok')
                    st.write('**Alerjenler:**', p.get('allergens') or 'Veri yok')
                    nutrients = p.get('nutriments') or {}
                    for key, label in [('sugars_100g','Şeker'),('saturated-fat_100g','Doymuş yağ'),
                                       ('salt_100g','Tuz'),('proteins_100g','Protein'),('fiber_100g','Lif')]:
                        value = nutrients.get(key)
                        st.write(f'**{label} (100 g):** {value} g' if value is not None else f'**{label}:** Veri yok')
                if st.button('✨ Yapay zekâ ile detaylı analiz et', type='primary'):
                    try:
                        with st.spinner('İçerik, avantajlar, dezavantajlar ve tüketim tavsiyesi hazırlanıyor...'):
                            result = analyze_barcode_product(p)
                        st.session_state['barcode_result']['analysis'] = result
                    except Exception as exc:
                        st.error(f'Yapay zekâ analizi başarısız: {exc}')
                analysis = st.session_state['barcode_result'].get('analysis')
                if analysis:
                    show_result(analysis, 'Yiyecek')
                    st.caption('Kaynak: Open Food Facts topluluk veri tabanı. Sayısal puan deneysel/tahminidir; güvenilirlik notunu dikkate alın.')
            else:
                st.warning('Bu barkod için Open Food Facts veri tabanında ürün bulunamadı.')

else:
    st.subheader('Bu oturumdaki analizler')
    for category,result in reversed(st.session_state.get('history',[])):
        with st.expander(result.get('product_name') or category):
            show_result(result,category)
    if not st.session_state.get('history'):
        st.info('Henüz analiz yok. Geçmiş bu tarayıcı oturumu boyunca saklanır.')
st.divider()
st.caption('Puanlar deneysel veya tahminidir; resmî Nutri-Score, laboratuvar sonucu ya da sağlık teşhisi değildir. Güvenilirlik notunu okuyun.')
