# Vercel Deployment Guide - Flora Backend

Bu doküman Flora Backend projesini Vercel'e deploy etmek için kapsamlı bir rehberdir.

## 🚀 Hızlı Deployment

### 1. GitHub Repository Hazır
✅ Repository zaten oluşturuldu ve pushlandı: `https://github.com/gokhanustunyer/flora-backend`

### 2. Vercel'e Deploy Et

1. **Vercel'e git:** https://vercel.com
2. **GitHub ile giriş yap**
3. **"New Project" tıkla**
4. **Repository'yi seç:** `flora-backend`
5. **Deploy butonuna bas**

## 🔧 Environment Variables

Vercel dashboard'da **Settings > Environment Variables** bölümünden şu değişkenleri ekle:

### REQUIRED (Zorunlu)

```env
# Stability.ai API Key
STABILITY_AI_API_KEY=your-stability-ai-api-key-here

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
```

### OPTIONAL (İsteğe Bağlı)

```env
# Advanced Supabase
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# Database (Direct PostgreSQL)
DATABASE_URL=postgresql+psycopg://postgres:[password]@db.your-project.supabase.co:6543/postgres

# Storage Settings
USE_SUPABASE_STORAGE=true
SUPABASE_STORAGE_BUCKET=gnb-dog-images

# Application Settings
LOG_LEVEL=INFO
DEBUG_MODE=false
MAX_IMAGE_SIZE_MB=10
AI_GENERATION_TIMEOUT=30
MAX_IMAGE_DIMENSION=1024

# CORS (Frontend domain'ini ekle)
CORS_ORIGINS=["https://your-frontend.vercel.app","http://localhost:3000"]
```

## 📋 Deployment Checklist

### ✅ Pre-deployment (Tamamlandı)
- [x] Git repository oluşturuldu
- [x] `.gitignore` dosyası hazırlandı
- [x] `vercel.json` konfigürasyonu eklendi
- [x] Supabase entegrasyonu tamamlandı
- [x] Requirements.txt güncel
- [x] Main.py Vercel uyumlu hale getirildi

### 🔄 Deployment Sırasında
- [ ] Vercel project oluştur
- [ ] Environment variables ayarla
- [ ] Deploy et
- [ ] Test et

### ✅ Post-deployment
- [ ] API endpoints'lerini test et
- [ ] Supabase bağlantısını kontrol et
- [ ] Health check endpoint'ini test et

## 🌐 API Endpoints (Deploy sonrası)

Deploy edildikten sonra API şu endpoint'lerde mevcut olacak:

```
Base URL: https://your-project.vercel.app

Health Check:
GET /health

API Documentation:
GET /docs

Main Endpoints:
POST /api/v1/generate        # Resim üretimi
GET  /api/v1/test-supabase   # Supabase test
GET  /api/v1/generations     # Generation history
```

## 🧪 Test Etme

Deploy sonrası test etmek için:

### 1. Health Check
```bash
curl https://your-project.vercel.app/health
```

### 2. Supabase Test
```bash
curl https://your-project.vercel.app/api/v1/test-supabase
```

### 3. API Documentation
Tarayıcıda: `https://your-project.vercel.app/docs`

## ⚡ Performance Optimizations

Vercel konfigürasyonunda yapılan optimizasyonlar:

- **Memory:** 1024MB (AI generation için)
- **Timeout:** 60 saniye (AI processing için)
- **Region:** IAD1 (en hızlı bölge)
- **Python Version:** 3.11

## 🔥 Domain & SSL

Vercel otomatik olarak sağlar:
- ✅ HTTPS SSL sertifikası
- ✅ Global CDN
- ✅ Otomatik domain (`your-project.vercel.app`)
- ✅ Custom domain desteği

## 🐛 Troubleshooting

### Yaygın Sorunlar:

1. **Build Hatası:**
   - Environment variables eksik olabilir
   - Requirements.txt'de paket versiyonu sorunu

2. **Timeout Hatası:**
   - AI generation işlemi uzun sürüyor
   - Vercel function timeout'u 60 saniye

3. **Supabase Bağlantı Hatası:**
   - SUPABASE_URL ve SUPABASE_KEY kontrol et
   - Supabase project'in aktif olduğundan emin ol

### Log'ları Kontrol Et:
Vercel dashboard'da **Functions > View Function Logs**

## 🎉 Next Steps

Deploy başarılı olduktan sonra:

1. **Frontend Integration:** Frontend uygulamanızı bu API'ye bağlayın
2. **Custom Domain:** İsterseniz özel domain ekleyin
3. **Monitoring:** Vercel analytics'i aktifleştirin
4. **Scaling:** Gerekirse Pro plan'a geçin

## 📞 Support

Sorun yaşarsanız:
- Vercel documentation: https://vercel.com/docs
- Flora Backend repo: https://github.com/gokhanustunyer/flora-backend 