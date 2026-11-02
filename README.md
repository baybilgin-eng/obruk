# obruk.org — OBRUK Mağara Araştırma Grubu web sitesi

Statik site (HTML/CSS/JS). Sunucu, veritabanı veya eklenti gerektirmez; GitHub Pages üzerinde çalışır. Harita dahil hiçbir bileşen harici servis ya da API anahtarı gerektirmez.

## Klasör yapısı
- `index.html`, `hakkimizda/`, `arastirmalar/`, `raporlar/`, `yayinlar/`, `magara-envanteri/`, `saha-gunlugu/`, `iletisim/` … Türkçe sayfalar
- `en/` … İngilizce temel sayfalar
- Önceki sitedeki yazı adresleri korunur (`/kayseri-23-calisma-koramaz-vadisi/` gibi); taşınan sayfa adresleri yeni sayfalara yönlenir.
- `assets/` stil, betik, harita kütüphanesi (Leaflet) ve Türkiye sınırları · `img/` saha fotoğrafları, logo, PDF kapakları · `medya/` yazı görselleri (WebP) · `pdf/` raporlar ve yayınlar
- `sitemap.xml`, `robots.txt`, `404.html` arama motorları için hazır.
- `_kaynak/` siteyi yeniden üreten Python betikleri (`content.py` elle düzenlenebilir metinler ve listeler).

## Bilgisayarda önizleme
Klasördeki `index.html` dosyasına çift tıklayınca bazı bağlantılar klasör listesi olarak açılabilir. Doğru önizleme için klasörde bir komut satırı açıp `python -m http.server` çalıştırın ve tarayıcıda `http://localhost:8000` adresine gidin — ya da doğrudan GitHub Pages'te açın.

## GitHub Pages'te deneme yayını
1. GitHub'da yeni bir depo açın (ör. `obruk-site`), bu klasörün **içeriğini** depoya yükleyin (GitHub Desktop ile sürükle-bırak en kolayı).
2. Depo → Settings → Pages → Source: *Deploy from a branch*, Branch: `main` / `/ (root)` → Save.
3. Birkaç dakika sonra site `https://KULLANICI.github.io/obruk-site/` adresinde açılır. Tüm bağlantılar göreli olduğu için alt klasörde de çalışır.

## obruk.org'a bağlama (deneme bitince)
1. Settings → Pages → Custom domain: `obruk.org` yazıp kaydedin (depoya `CNAME` dosyası eklenir). *Enforce HTTPS* kutusunu işaretleyin.
2. Alan adı sağlayıcısının DNS panelinde:
   - `@` için 4 adet A kaydı: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - `www` için CNAME: `KULLANICI.github.io`
3. Google Search Console'da `obruk.org` mülkünü doğrulayıp `https://obruk.org/sitemap.xml` adresini gönderin.

## İçerik güncelleme
Yeni rapor / proje / üye eklemek için `_kaynak/content.py` dosyasındaki listeleri düzenleyip `python3 build.py` çalıştırmak yeterli (betik, `obruk_icerik` klasörünü okur; yolları dosyanın başındaki `SRC` / `OUT` değişkenlerinden ayarlayın).
İletişim formu e-postayı ziyaretçinin kendi e-posta programında ayamac@gmail.com adresine açar; sitede veri saklanmaz.
