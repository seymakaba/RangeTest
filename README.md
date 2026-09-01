# Ürün Etiket Doğrulama Arayüzü

Excel dosyasındaki ürün görsellerini (URL üzerinden) gösterip, model tarafından
tahmin edilen **Yaka, Kol, Desen, Cep, Stil** gibi etiketleri görsele bakarak
kontrol etmenizi ve düzeltmenizi sağlayan basit bir Streamlit uygulaması.

## Özellikler

- Excel (.xlsx) dosyası yükleme
- Görsel URL kolonu ve etiket kolonlarını otomatik tahmin etme / elle seçme
- Ürün görselini **tıklayınca büyüyen (zoom)** şekilde gösterme
- Her etiket için mevcut değerleri dropdown'dan seçme veya yeni değer girme
- İleri / geri gezinme, kayda doğrudan gitme, arama (GorselAdi / MarkaKodu)
- Filtre: tümü / düşük güvenli tahminler / düzenlenenler / düzenlenmeyenler
- Tüm düzeltmeleri tek tuşla **yeni bir Excel dosyası** olarak indirme

## Beklenen Excel yapısı

Her satır bir ürün olmalı. Gerekli/kullanılan kolonlar:

| Kolon | Açıklama |
|---|---|
| Görsel URL kolonu | Ürün görselinin linki (siz ekleyeceksiniz, kolon adı serbest — uygulama içinde seçilir) |
| YakaTipi, KolBoyu, Desen, CepTuru, Stil | Model tahminleri (varsayılan sınıflar; farklıysa uygulamadan seçebilirsiniz) |
| `<Kolon>_Confidence` | (Opsiyonel) her etiket için güven skoru, örn. `YakaTipi_Confidence` |

Kolon adları farklıysa sorun değil: uygulama açıldığında sol menüden **"Kolon
eşleme"** bölümünden görsel URL kolonunu ve etiket kolonlarını elle seçebilirsiniz.

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tarayıcıda otomatik olarak `http://localhost:8501` açılır.

## GitHub'a yükleme

```bash
cd urun-etiket-dogrulama
git init
git add .
git commit -m "İlk sürüm: ürün etiket doğrulama arayüzü"
git branch -M main
git remote add origin https://github.com/<kullanici-adiniz>/<repo-adi>.git
git push -u origin main
```

## Streamlit Community Cloud ile paylaşma (ücretsiz)

1. [share.streamlit.io](https://share.streamlit.io) adresine GitHub hesabınızla giriş yapın.
2. **"New app"** butonuna tıklayın.
3. Az önce oluşturduğunuz GitHub reposunu, branch'i (`main`) ve ana dosyayı
   (`app.py`) seçin.
4. **Deploy** deyin — birkaç dakika içinde `https://<uygulama-adi>.streamlit.app`
   şeklinde herkesle paylaşabileceğiniz bir link elde edersiniz.

Uygulama içinde herhangi bir gizli anahtar / API key kullanılmadığı için ek bir
"Secrets" ayarına gerek yoktur.

## Notlar

- Uygulama, düzenlemelerinizi tarayıcı oturumu (session) boyunca hafızada tutar;
  sayfayı yenilerseniz veya oturum kapanırsa kaydetmediğiniz değişiklikler kaybolur.
  Bu yüzden çalışırken ara ara **"Son hali Excel olarak indir"** ile yedek almanız
  önerilir.
- Görseller doğrudan tarayıcıdan URL üzerinden yüklendiği için görsellerin
  herkese açık/erişilebilir bir URL'de olması gerekir.
- 14.000+ satırlık veri setinde performans sorunu yaşarsanız, filtre (örn.
  "Sadece düşük güvenli") kullanarak inceleyeceğiniz alt kümeyi daraltabilirsiniz.
