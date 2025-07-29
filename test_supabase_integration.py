"""Test script for Supabase integration in Flora Backend."""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()

# Kullanıcının test kodunu kullanarak
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def create_supabase_client():
    """Supabase client oluştur"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client başarıyla oluşturuldu")
        return supabase
    except Exception as e:
        print(f"❌ Supabase client oluşturulamadı: {e}")
        return None

def test_connection(supabase: Client):
    """Bağlantı testi yap"""
    try:
        # image_generations tablosu ile bağlantıyı test et
        response = supabase.table('image_generations').select("*").limit(1).execute()
        print("✅ Supabase bağlantısı başarılı")
        return True
    except Exception as e:
        print(f"❌ Bağlantı testi başarısız: {e}")
        return False

def check_image_generations_table(supabase: Client):
    """image_generations tablosunun var olup olmadığını kontrol et"""
    try:
        response = supabase.table('image_generations').select("*").limit(1).execute()
        print("✅ image_generations tablosu mevcut")
        return True
    except Exception as e:
        print(f"❌ image_generations tablosu bulunamadı: {e}")
        return False

def insert_test_record(supabase: Client):
    """Test kaydı ekle - image_generations tablosuna"""
    try:
        test_data = {
            "original_image_filename": f"test_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
            "original_image_url": "https://example.com/test-image.jpg",
            "original_image_size": 1024000,
            "original_image_format": "JPEG",
            "prompt_used": "Test prompt for dog image generation",
            "dog_description": "A friendly golden retriever in a park",
            "status": "completed",
            "processing_time": 2.5,
            "logo_applied": False
        }
        
        response = supabase.table('image_generations').insert(test_data).execute()
        
        if response.data:
            print(f"✅ Kayıt başarıyla eklendi: ID {response.data[0]['id']}")
            return response.data[0]
        else:
            print("❌ Kayıt eklenemedi")
            return None
            
    except Exception as e:
        print(f"❌ Kayıt ekleme hatası: {e}")
        return None

def fetch_records(supabase: Client):
    """Kayıtları getir - image_generations tablosundan"""
    try:
        response = supabase.table('image_generations').select("id, original_image_filename, status, processing_time, created_at").order('created_at', desc=True).limit(5).execute()
        
        if response.data:
            print(f"✅ {len(response.data)} kayıt getirildi:")
            for record in response.data:
                print(f"  - ID: {record['id'][:8]}...")
                print(f"    Filename: {record['original_image_filename']}")
                print(f"    Status: {record['status']}")
                print(f"    Processing Time: {record.get('processing_time', 'N/A')}s")
                print(f"    Created: {record['created_at']}")
                print()
        else:
            print("📭 Hiç kayıt bulunamadı")
            
        return response.data
        
    except Exception as e:
        print(f"❌ Kayıt getirme hatası: {e}")
        return None

def get_statistics(supabase: Client):
    """İstatistikleri getir"""
    try:
        # Daily summary view'den veri çek
        response = supabase.table('daily_generation_summary').select("*").limit(5).execute()
        
        if response.data:
            print(f"✅ Son 5 günün istatistikleri:")
            for stat in response.data:
                print(f"  - Tarih: {stat['generation_date']}")
                print(f"    Toplam: {stat['total_requests']}")
                print(f"    Başarılı: {stat['successful_requests']}")
                print(f"    Başarı Oranı: {stat['success_rate_percent']}%")
                print(f"    Ort. İşlem Süresi: {stat['avg_processing_time']}s")
                print()
        else:
            print("📊 Henüz istatistik verisi yok")
            
        return response.data
        
    except Exception as e:
        print(f"⚠️  İstatistik verisi alınamadı (henüz veri olmayabilir): {e}")
        return None

def test_backend_integration():
    """Backend entegrasyonunu test et"""
    import requests
    
    try:
        print("\n🔧 Backend Supabase entegrasyonunu test ediliyor...")
        
        # Assuming the backend is running on localhost:3001
        response = requests.get("http://localhost:3001/api/v1/test-supabase")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend Supabase entegrasyonu başarılı!")
            print(f"   Test Record ID: {data['data']['test_record_id']}")
        else:
            print(f"❌ Backend test başarısız: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"⚠️  Backend test yapılamadı (backend çalışmıyor olabilir): {e}")

def main():
    print("🚀 Flora Backend Supabase Entegrasyonu Test Ediliyor...\n")
    
    # 1. Environment variables kontrolü
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL veya SUPABASE_KEY environment değişkenleri ayarlanmamış")
        print("   .env dosyasında şu değişkenleri ayarlayın:")
        print("   SUPABASE_URL=https://your-project.supabase.co")
        print("   SUPABASE_KEY=your-supabase-key")
        return
    
    print(f"📡 Supabase URL: {SUPABASE_URL}")
    print(f"🔑 Supabase Key: {SUPABASE_KEY[:20]}...{SUPABASE_KEY[-10:]}\n")
    
    # 2. Client oluştur
    supabase = create_supabase_client()
    if not supabase:
        return
    
    # 3. Bağlantı testi
    if not test_connection(supabase):
        return
    
    # 4. Tablo kontrolü
    if not check_image_generations_table(supabase):
        return
    
    # 5. Test kaydı ekle
    print("\n📝 Test kaydı ekleniyor...")
    new_record = insert_test_record(supabase)
    
    # 6. Kayıtları getir
    print("\n📋 Son kayıtlar getiriliyor...")
    records = fetch_records(supabase)
    
    # 7. İstatistikleri getir
    print("\n📊 İstatistikler getiriliyor...")
    stats = get_statistics(supabase)
    
    # 8. Backend entegrasyonunu test et
    test_backend_integration()
    
    print("\n✅ Test tamamlandı!")

if __name__ == "__main__":
    main() 