# Supabase Entegrasyonu - Flora Backend

Bu doküman, Flora Backend projesine eklenen Supabase direct client entegrasyonunu açıklar.

## 🚀 Özellikler

- ✅ Resim üretimi tamamlandığında otomatik Supabase kayıt ekleme
- ✅ Başarılı ve başarısız işlemler için ayrı kayıt tutma
- ✅ Logo overlay başarısızlıklarında bile kayıt ekleme
- ✅ Test endpoint'i ile bağlantı kontrolü
- ✅ Mevcut SQLAlchemy veritabanından bağımsız çalışma

## 📋 Kurulum

### 1. Environment Variables

`.env` dosyanızda şu değişkenleri ayarlayın:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
```

**Not:** `SUPABASE_KEY` olarak:
- Anon key (public key) kullanabilirsiniz
- Veya daha güvenli olmak için Service Role key kullanabilirsiniz

### 2. Gerekli Paketler

`supabase` paketi zaten `requirements.txt`'de mevcut:

```txt
supabase==2.3.0
```

Eğer eksikse yükleyin:
```bash
pip install supabase==2.3.0
```

## 🎯 Kullanım

### Otomatik Kayıt Ekleme

Artık resim üretimi yapıldığında sistem otomatik olarak Supabase'e kayıt ekler:

```python
# POST /api/v1/generate endpoint'i kullanıldığında
# Otomatik olarak şu bilgiler Supabase'e kaydedilir:

{
    "original_image_filename": "dog.jpg",
    "original_image_url": "https://storage.url/originals/...",
    "original_image_size": 1024000,
    "original_image_format": "JPEG",
    "generated_image_url": "https://storage.url/generations/...",
    "generated_image_size": 2048000,
    "prompt_used": "A friendly dog wearing GNB branded apparel...",
    "dog_description": "A friendly, well-groomed dog",
    "status": "completed",
    "processing_time": 3.5,
    "logo_applied": true,
    "created_at": "2025-01-29T10:30:00Z"
}
```

### Test Endpoint'i

Supabase bağlantısını test etmek için:

```bash
GET http://localhost:3001/api/v1/test-supabase
```

Başarılı response:
```json
{
    "success": true,
    "message": "✅ Supabase connection successful! Test record created.",
    "data": {
        "test_record_id": "12345678-1234-5678-9012-123456789012",
        "created_at": "2025-01-29T10:30:00Z"
    }
}
```

### Standalone Test Script

Bağımsız test için `test_supabase_integration.py` dosyasını çalıştırın:

```bash
python test_supabase_integration.py
```

Bu script:
- ✅ Bağlantı testini yapar
- ✅ Test kaydı ekler
- ✅ Kayıtları getirir
- ✅ İstatistikleri kontrol eder
- ✅ Backend entegrasyonunu test eder

## 📊 Kayıt Formatı

Supabase'e eklenen kayıtlar `image_generations` tablosunda şu formatta tutulur:

| Alan | Tip | Açıklama |
|------|-----|----------|
| `id` | UUID | Otomatik oluşturulan unique ID |
| `original_image_filename` | String | Yüklenen dosya adı |
| `original_image_url` | String | Storage'da original image URL'i |
| `original_image_size` | Integer | Original image boyutu (bytes) |
| `original_image_format` | String | Image formatı (JPEG, PNG, etc.) |
| `generated_image_url` | String | Storage'da üretilen image URL'i |
| `generated_image_size` | Integer | Üretilen image boyutu (bytes) |
| `prompt_used` | Text | AI'ya gönderilen prompt |
| `dog_description` | Text | Köpek açıklaması |
| `status` | String | İşlem durumu (completed, failed) |
| `processing_time` | Float | İşlem süresi (saniye) |
| `logo_applied` | Boolean | Logo eklendi mi? |
| `error_message` | Text | Hata mesajı (varsa) |
| `created_at` | DateTime | Kayıt oluşturulma zamanı |

## 🔧 Error Handling

Sistem farklı hata durumlarında da kayıt tutar:

### 1. Logo Overlay Hatası
- Status: `completed`
- Logo Applied: `false`
- Error Message: Logo hatası detayı
- İşlem başarılı sayılır, sadece logo eklenemez

### 2. AI Generation Hatası
- Status: `failed`
- Error Message: AI generation hatası
- İşlem başarısız sayılır

### 3. Genel Hatalar
- Status: `failed`
- Error Message: Genel hata detayı
- İşlem başarısız sayılır

## 🔄 Supabase Service Architecture

```
SupabaseClientService
├── _initialize_client()     # Client'ı başlat
├── _test_connection()       # Bağlantıyı test et
├── is_available()          # Client hazır mı?
├── insert_generation_record() # Kayıt ekle
├── update_generation_status() # Kayıt güncelle
└── get_generation_statistics() # İstatistik getir
```

## 📈 İstatistikler

Eğer `daily_generation_summary` view'ınız varsa, sistem istatistikleri de alabilir:

```python
# Supabase service'den istatistik alın
stats = await supabase_service.get_generation_statistics(limit=5)
```

## 🛠️ Troubleshooting

### Bağlantı Sorunları

1. **Environment variables kontrol edin:**
   ```bash
   echo $SUPABASE_URL
   echo $SUPABASE_KEY
   ```

2. **Test script'i çalıştırın:**
   ```bash
   python test_supabase_integration.py
   ```

3. **Backend test endpoint'ini kullanın:**
   ```bash
   curl http://localhost:3001/api/v1/test-supabase
   ```

### Yaygın Hatalar

- **Client not available:** Environment variables eksik/yanlış
- **Table not found:** `image_generations` tablosu oluşturulmamış
- **Permission denied:** API key yetkisiz

## 📝 Notlar

- Supabase client, mevcut SQLAlchemy veritabanından bağımsız çalışır
- Supabase bağlantısı başarısız olursa, sistem normal şekilde çalışmaya devam eder
- Kayıtlar hem mevcut database'e hem de Supabase'e parallel olarak eklenir
- Error durumlarında bile kayıt tutulmaya çalışılır

## 🎉 Başarılı Entegrasyon

Eğer her şey doğru ayarlandıysa:

1. ✅ Resim üretimi yapıldığında Supabase'e kayıt düşer
2. ✅ Test endpoint'i 200 OK döner
3. ✅ Log'larda "Supabase record created" mesajları görürsünüz
4. ✅ Supabase dashboard'da kayıtları görebilirsiniz 