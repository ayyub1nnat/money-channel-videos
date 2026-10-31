# MOTION_RULES.md — kodla animasyon kuralları (sahibin talimatı, 2026-10-31)

Bu projede kodla üretilen her animasyon/video işinde uygulanır.

## 1) Render sözleşmesi
- Tüm görsel durum zamanın saf fonksiyonu: `draw(t)`. Önceki kareye bağlı biriken durum yok.
- Rastgelelik sadece tohumlu üreteçle (ör. mulberry32). `Math.random` yasak (Python'da `random.Random(seed)`).
- Sayfada `window.__duration` ve `window.__setTime(t)` olsun; dışarıdan kare kare sürülebilsin.
- URL'de `?t=3.2` verilirse o anı çizip dursun (tek kare kontrolü).
- Sabit çözünürlük ve fps. `devicePixelRatio` ile net çizim.
- Tek dosya HTML. Kütüphane gerekirse CDN'den.
- MP4 gerekiyorsa: headless tarayıcıyla kare kare PNG al, FFmpeg ile birleştir.

## 2) Görünüm yasakları
- Ortalanmış başlık + mor/mavi gradyan şablonu yok.
- Anlamı olmayan parçacık, lens flare, neon parlama, RGB kayması, sürekli kamera sallantısı yok.
- Her şeyin zıpladığı elastik easing yok. Easing işe göre seçilir.
- En fazla 2 yazı tipi, tek vurgu rengi.
- Her sahnenin tek bir işi var. Metin okunacak kadar ekranda kalır (en az 1.2 sn).
- Geçişler önceki sahnede zaten görünen bir nesneden doğar.
- Büyük anlardan önce 300–600 ms durgunluk bırak.

## 3) Ses
- Ses verilmezse Web Audio ile sentezle. Her ses ekranda görünen bir olaya bağlı olsun.
- Müzik verilirse önce analiz et (BPM, vuruşlar, enerji), görüntüyü ona göre zamanla.
- NOT: YouTube kanal videoları için DAILY.md kuralı geçerli: müzik yok, geçiş sesi yok, sadece ses (am_michael).

## 4) Kontrol döngüsü
- Kod yazmadan önce sahne listesi ve süreleri göster.
- Final render'dan önce her sahneden kare alıp bir kontak sayfası yap, kendi gözünle incele
  (build_pov.py `--preview` → preview_grid.jpg).
- Taşan yazı, çakışma, okunmayan metin, güvenli alan dışı öğe varsa düzelt.
- "Kod çalışıyor" ile "görüntü doğru" aynı şey değil.
