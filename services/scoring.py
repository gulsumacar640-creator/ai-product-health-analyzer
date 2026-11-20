"""Transparent, experimental 0–100 indicative scores; NOT official Nutri-Score."""
def score_product(result, category):
    if category == 'Giysi':
        val = result.get('estimated_score')
        if isinstance(val,(int,float)) and 0 <= val <= 100:
            return round(val), 'Düşük güvenilirlik · Fotoğraf/etiket bilgisine dayalı tahmini kullanım puanı; laboratuvar kalite veya sağlık testi değildir.'
        return None, 'Giysi puanı için yeterli dayanak yok.'

    n = result.get('nutrition_per_100g') or {}
    keys = ('sugars_g','saturated_fat_g','salt_g','fiber_g','protein_g')
    def num(k):
        x=n.get(k)
        return float(x) if isinstance(x,(int,float)) and x>=0 else None
    vals={k:num(k) for k in keys}
    present=sum(v is not None for v in vals.values())
    # Heuristic, not a scientific or official score. Never infer a precise health verdict.
    if present>=3 and vals['sugars_g'] is not None:
        sugar=vals['sugars_g']; sat=vals['saturated_fat_g'] or 0; salt=vals['salt_g'] or 0
        fiber=vals['fiber_g'] or 0; protein=vals['protein_g'] or 0
        score=round(max(0,min(100,80-min(sugar,50)*1.1-min(sat,20)*1.3-min(salt,5)*8+min(fiber,10)*1.3+min(protein,20)*0.3)))
        confidence='Orta' if present==5 else 'Düşük'
        return score, f'{confidence} güvenilirlik · 100 g besin değerlerinden hesaplanan deneysel puan; resmî Nutri-Score değildir. Eksik veri: {5-present}/5.'
    val=result.get('estimated_score')
    if isinstance(val,(int,float)) and 0 <= val <= 100:
        return round(val), 'Çok düşük güvenilirlik · Eksik besin verileriyle yapay zekâ tahmini. Gerçek beslenme profilini temsil etmeyebilir.'
    return None, 'Skor üretilemedi; içerik ve besin değerleri için daha net etiket gerekli.'
