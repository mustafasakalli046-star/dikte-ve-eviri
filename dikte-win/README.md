# Dikte-Win (minimal, Windows-only yeniden yazim)

Bu, orijinal `dikte` projesinin (Linux/macOS/Windows, PyQt6, ~14.000 satir)
**sadece Windows'u hedefleyen, cok daha kucuk** bir yeniden yazimidir.
Cross-platform soyutlama katmanlari (paste.Desktop, audio.Sound, hotkey
backend tablosu, PyQt6 arayuzu) tamamen kaldirildi; yerine dogrudan Windows
API'lerini kullanan tek-yollu, ~1500 satirlik bir kod tabani geldi. Ozellik
kumesi ayni:

| Ozellik | Dosya |
| --- | --- |
| Kisayolla kayit + STT + yapistirma | `worker.py`, `audio.py`, `transcribe.py` |
| LLM ile temizlik (kekemelik/noktalama/ozel isim) | `cleanup.py` |
| Sessizlik filtresi (VAD) | `vad.py` |
| Toplanti kaydi + tutanak | `meeting.py` |
| Ajan modu (Claude Code / Codex / OpenRouter) | `agent.py` |
| Dosyadan transkripsiyon (.txt / .srt) | `filetranscribe.py` |
| **Yeni: Ingilizce ceviri** | `translate.py` |
| Ayarlar penceresi | `settings_ui.py` (Tkinter, PyQt6 yok) |
| Tepsi simgesi | `tray.py` (pystray) |
| CLI | `cli.py` |

## Neden farkli / neyi bilerek sadelestirdim

- **Tek platform → tek yol.** Orijinaldeki "her davranis bir tabloda, secici
  tek yerde" tasarimina artik gerek yok; her modul direkt Windows'a yazildi.
- **PyQt6 yerine Tkinter.** Ayarlar penceresi stdlib ile geliyor, ekstra
  agir bir GUI bagimliligi yok. Kose gostergesi (overlay) kaldirildi; durum
  tepsi simgesinin rengi ve Windows bildirimleriyle gosteriliyor.
- **Otomatik whisper.cpp/llama.cpp indirme yok.** Orijinal proje bunlari
  indirip sha256 dogrulayip arka planda sunucu olarak calistiriyordu
  (`ggml.py`, `hub.py`). Bu minimal surumde yerel mod, sunuculari **siz
  calistirdiginizda** `whisper_server_url` / `llama_server_url` ile onlara
  baglanir; istemiyorsaniz bulut saglayicilarini (OpenAI/Groq/OpenRouter)
  kullanabilirsiniz. Bu, kod tabanini once ~1000 satir kucultmenin en
  buyuk kalemiydi.
- **Ctrl+V ceviri kisayoluyla ilgili not.** Istediginiz gibi bir kisayolla
  panodaki metni Ingilizce'ye cevirip geri yapistiran bir ozellik eklendi
  (`translate.py`, `app.py::_on_translate_hotkey`). Varsayilani duz
  `Ctrl+V` degil `Ctrl+Alt+V` yaptim, cunku duz `Ctrl+V`'yi global olarak
  yakalamak sistemin normal yapistirma kisayolunu da ele gecirir (her
  yapistirmaniz cevrilmeye calisilir). Ayarlar → Genel → "Ceviri kisayolu"
  alanindan `ctrl+v` yazip degistirebilirsiniz; sadece bunun sonucunu
  bilerek yapin.
- **Toplanti/dosya transkripsiyonu basitlestirildi.** Orijinaldeki gercek
  zamanli, olay tabanli kanal ayirma yerine sabit uzunlukta parcalara
  bolup (20 sn toplanti, 60 sn dosya) her parcayi ayri transkribe eden,
  daha kolay anlasilir bir yaklasim kullanildi. Dogrulugu biraz daha
  dusuk ama kod cok daha az.

## Visual Studio'da acma

1. **Visual Studio Installer**'dan *Python geliştirme* iş yükünü kurun (kurulu
   degilse).
2. `File > Open > Folder...` ile bu klasoru (`dikte-win`) acin; Visual
   Studio klasoru otomatik bir Python projesi olarak tanir.
3. `Tools > Python > Python Environments` uzerinden bir sanal ortam
   olusturun (Python 3.11+) ve:
   ```
   pip install -r requirements.txt
   ```
   ya da Solution Explorer'da `requirements.txt`'ye sag tiklayip
   *Install from requirements.txt* secin.
4. `run.py` dosyasina sag tiklayip **Set as Startup File** secin, sonra
   F5 ile calistirin.
5. Ayrica gerekenler:
   - `winget install Gyan.FFmpeg` (dosya transkripsiyonu ve toplanti icin)
   - En az bir STT/LLM saglayicisi: `OPENAI_API_KEY` / `GROQ_API_KEY` /
     `OPENROUTER_API_KEY` ortam degiskeni, **veya** Ayarlar penceresinden
     dogrudan anahtar girin, **veya** yerel `whisper.cpp`/`llama.cpp`
     sunucularini kendiniz kurup calistirin ve URL'lerini ayarlardan verin.

## Kullanim

| Ne | Nasil |
| --- | --- |
| Kaydi baslat/durdur | `Ctrl+Space` ya da tepsi menusu |
| Kaydi iptal et | `Ctrl+Alt+Space` |
| Panodaki metni Ingilizce'ye cevir + yapistir | `Ctrl+Alt+V` (ayarlardan degistirilebilir) |
| Ajana sesli komut ver | Tepsi menusu → *Ajana sor* |
| Toplanti kaydi baslat/bitir | Tepsi menusu → *Toplanti kaydini baslat/bitir* |
| Ayarlar | Tepsi menusu → *Ayarlar* |
| Dosya transkripsiyonu | `python -m dikte transcribe dosya.mp4 --srt` |
| Belirli sure test kaydi | `python -m dikte record --seconds 8` |

Ayarlar `%APPDATA%\Dikte\config.json` (mod 600) dosyasinda tutulur, gecmis
ve toplanti kayitlari `%APPDATA%\Dikte\data\` altinda.

## Bilinen sinirlamalar (bilerek minimal tutulan yerler)

- Global kisayollar `keyboard` kutuphanesiyle kancalaniyor; bazi korumali
  pencereler (ör. yonetici olarak calisan uygulamalar) bunu gormeyebilir -
  boyle durumlarda Dikte-Win'i de yonetici olarak calistirin.
- Toplanti modunda hoparlor kaydi (`soundcard` + WASAPI loopback) bazi ses
  surucularinde calismayabilir; calismazsa toplanti sessizce sadece
  mikrofonla devam eder.
- Gecmis ve metin duzenleme arayuzu yok (dosyalar duz JSON/txt, elle
  incelenebilir).

## Lisans

Orijinal proje gibi GPL-3.0 varsayilmistir; kendi kullaniminiz icin
LICENSE dosyasini ekleyip guncelleyin.
